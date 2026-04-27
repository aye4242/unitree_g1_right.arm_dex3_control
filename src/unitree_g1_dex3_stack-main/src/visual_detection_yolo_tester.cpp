#include <cerrno>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstring>
#include <limits>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/header.hpp>
#include <tf2/exceptions.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>
#include <tf2_ros/buffer.h>
#include <tf2_ros/create_timer_ros.h>
#include <tf2_ros/transform_listener.h>
#include <vision_msgs/msg/detection3_d.hpp>
#include <vision_msgs/msg/detection3_d_array.hpp>

class VisualDetectionYoloTester : public rclcpp::Node {
public:
  VisualDetectionYoloTester()
  : Node("visual_detection_yolo_tester"),
    tf_buffer_(this->get_clock()),
    tf_listener_(tf_buffer_),
    running_(true) {
    this->declare_parameter<std::string>("detections_topic", "/detections_3d");
    this->declare_parameter<std::string>("target_class", "cup");
    this->declare_parameter<std::string>("robot_frame", "pelvis");

    this->get_parameter("detections_topic", detections_topic_);
    this->get_parameter("target_class", target_class_);
    this->get_parameter("robot_frame", robot_frame_);

    tf_buffer_.setCreateTimerInterface(
      std::make_shared<tf2_ros::CreateTimerROS>(
        this->get_node_base_interface(),
        this->get_node_timers_interface()));

    detections_sub_ = this->create_subscription<vision_msgs::msg::Detection3DArray>(
      detections_topic_, 10,
      std::bind(&VisualDetectionYoloTester::detectionsCallback, this, std::placeholders::_1));

    RCLCPP_INFO(
      this->get_logger(),
      "Visual YOLO tester ready. target_class='%s', robot_frame='%s', detections_topic='%s'",
      target_class_.c_str(), robot_frame_.c_str(), detections_topic_.c_str());
    RCLCPP_INFO(
      this->get_logger(),
      "Press 's' to print the latest '%s' position in frame '%s'. Press 'q' to quit this node.",
      target_class_.c_str(), robot_frame_.c_str());

    keyboard_thread_ = std::thread(&VisualDetectionYoloTester::keyboardLoop, this);
  }

  ~VisualDetectionYoloTester() override {
    running_.store(false);
    closeKeyboard();
    if (keyboard_thread_.joinable()) {
      keyboard_thread_.join();
    }
  }

private:
  void detectionsCallback(const vision_msgs::msg::Detection3DArray::SharedPtr msg) {
    std::lock_guard<std::mutex> lock(detections_mutex_);
    latest_header_ = msg->header;
    latest_detections_ = msg->detections;
  }

  void keyboardLoop() {
    if (!openKeyboard()) {
      return;
    }

    while (running_.load() && rclcpp::ok()) {
      char ch = 0;
      const ssize_t bytes_read = ::read(keyboard_fd_, &ch, 1);
      if (bytes_read == 1) {
        if (ch == 's' || ch == 'S') {
          printSelectedDetection();
        } else if (ch == 'q' || ch == 'Q') {
          RCLCPP_INFO(this->get_logger(), "Received 'q', shutting down visual_detection_yolo_tester.");
          running_.store(false);
          rclcpp::shutdown();
          break;
        }
      } else if (bytes_read < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
        RCLCPP_ERROR(this->get_logger(), "Keyboard read failed: %s", std::strerror(errno));
        break;
      }

      std::this_thread::sleep_for(std::chrono::milliseconds(30));
    }

    closeKeyboard();
  }

  bool openKeyboard() {
    keyboard_fd_ = ::open("/dev/tty", O_RDONLY | O_NONBLOCK);
    if (keyboard_fd_ < 0) {
      RCLCPP_ERROR(
        this->get_logger(),
        "Failed to open /dev/tty for keyboard input: %s",
        std::strerror(errno));
      return false;
    }

    if (::tcgetattr(keyboard_fd_, &old_termios_) != 0) {
      RCLCPP_ERROR(
        this->get_logger(),
        "Failed to read terminal attributes: %s",
        std::strerror(errno));
      ::close(keyboard_fd_);
      keyboard_fd_ = -1;
      return false;
    }

    struct termios raw = old_termios_;
    raw.c_lflag &= static_cast<unsigned int>(~(ICANON | ECHO));
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;

    if (::tcsetattr(keyboard_fd_, TCSANOW, &raw) != 0) {
      RCLCPP_ERROR(
        this->get_logger(),
        "Failed to switch terminal to raw mode: %s",
        std::strerror(errno));
      ::close(keyboard_fd_);
      keyboard_fd_ = -1;
      return false;
    }

    keyboard_ready_ = true;
    return true;
  }

  void closeKeyboard() {
    if (keyboard_fd_ >= 0) {
      if (keyboard_ready_) {
        (void)::tcsetattr(keyboard_fd_, TCSANOW, &old_termios_);
        keyboard_ready_ = false;
      }
      ::close(keyboard_fd_);
      keyboard_fd_ = -1;
    }
  }

  void printSelectedDetection() {
    vision_msgs::msg::Detection3D selected_detection;
    std_msgs::msg::Header selected_header;
    std::size_t match_count = 0;

    {
      std::lock_guard<std::mutex> lock(detections_mutex_);
      if (latest_detections_.empty()) {
        RCLCPP_WARN(this->get_logger(), "No Detection3D data received yet.");
        return;
      }

      double best_score = -std::numeric_limits<double>::infinity();
      bool found = false;

      for (const auto & detection : latest_detections_) {
        if (detection.results.empty()) {
          continue;
        }
        if (detection.results.front().id != target_class_) {
          continue;
        }

        ++match_count;
        const double score = detection.results.front().score;
        if (!found || score > best_score) {
          best_score = score;
          selected_detection = detection;
          found = true;
        }
      }

      if (!found) {
        RCLCPP_WARN(
          this->get_logger(),
          "No detection matched target_class='%s' in the latest message.",
          target_class_.c_str());
        return;
      }

      selected_header = latest_header_;
    }

    geometry_msgs::msg::PoseStamped pose_in;
    pose_in.header = selected_detection.header;
    if (pose_in.header.frame_id.empty()) {
      pose_in.header = selected_header;
    }
    if (pose_in.header.stamp.sec == 0 && pose_in.header.stamp.nanosec == 0) {
      pose_in.header.stamp = selected_header.stamp;
    }
    pose_in.pose = selected_detection.bbox.center;

    if (pose_in.header.frame_id.empty()) {
      RCLCPP_ERROR(this->get_logger(), "Selected detection has an empty frame_id; cannot transform.");
      return;
    }

    try {
      const geometry_msgs::msg::PoseStamped pose_out =
        tf_buffer_.transform(pose_in, robot_frame_, tf2::durationFromSec(0.2));

      RCLCPP_INFO(
        this->get_logger(),
        "[s] class='%s' matches=%zu chosen_score=%.3f source_frame='%s' -> robot_frame='%s' position=(%.4f, %.4f, %.4f)",
        target_class_.c_str(),
        match_count,
        selected_detection.results.front().score,
        pose_in.header.frame_id.c_str(),
        robot_frame_.c_str(),
        pose_out.pose.position.x,
        pose_out.pose.position.y,
        pose_out.pose.position.z);
    } catch (const tf2::TransformException & ex) {
      RCLCPP_ERROR(
        this->get_logger(),
        "Failed to transform detection from '%s' to '%s': %s",
        pose_in.header.frame_id.c_str(),
        robot_frame_.c_str(),
        ex.what());
    }
  }

  rclcpp::Subscription<vision_msgs::msg::Detection3DArray>::SharedPtr detections_sub_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;

  std::string detections_topic_;
  std::string target_class_;
  std::string robot_frame_;

  std::mutex detections_mutex_;
  std::vector<vision_msgs::msg::Detection3D> latest_detections_;
  std_msgs::msg::Header latest_header_;

  std::thread keyboard_thread_;
  std::atomic<bool> running_;

  int keyboard_fd_ = -1;
  bool keyboard_ready_ = false;
  struct termios old_termios_ {};
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<VisualDetectionYoloTester>());
  rclcpp::shutdown();
  return 0;
}
