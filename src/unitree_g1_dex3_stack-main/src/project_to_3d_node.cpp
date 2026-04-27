#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <cv_bridge/cv_bridge.h>
#include <image_transport/image_transport.hpp>
#include <sensor_msgs/image_encodings.hpp>
#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/synchronizer.h>

#include <opencv2/opencv.hpp>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>
#include <pcl/filters/statistical_outlier_removal.h>
#include <pcl/common/centroid.h>
#include <pcl/common/common.h>
#include <pcl/common/transforms.h>

#include <vision_msgs/msg/detection3_d_array.hpp>
#include <vision_msgs/msg/detection3_d.hpp>
#include <vision_msgs/msg/object_hypothesis_with_pose.hpp>
#include <vision_msgs/msg/bounding_box3_d.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <geometry_msgs/msg/pose_with_covariance.hpp>
#include <geometry_msgs/msg/vector3.hpp>

#include "bboxes_ex_msgs/msg/bounding_box.hpp"
#include "bboxes_ex_msgs/msg/bounding_boxes.hpp"

#include <Eigen/Geometry>

#include <algorithm>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include <tf2/time.h>
#include <tf2_ros/buffer.h>
#include <tf2_ros/create_timer_ros.h>
#include <tf2_ros/transform_listener.h>

struct Detection {
  std::string class_name;
  float confidence;
  int x_min, y_min, x_max, y_max;
};

class ProjectTo3DNode : public rclcpp::Node {
public:
  ProjectTo3DNode()
  : Node("project_to_3d_node"),
    tf_buffer_(this->get_clock()),
    tf_listener_(tf_buffer_) {
    this->declare_parameter<std::string>("rgb_topic", "/camera/color/image_raw");
    this->declare_parameter<std::string>("depth_topic", "/camera/aligned_depth_to_color/image_raw");
    this->declare_parameter<std::string>("camera_info_topic", "/camera/color/camera_info");
    this->declare_parameter<std::string>("detections_topic", "/yolo/bounding_boxes");
    this->declare_parameter<std::string>("pointcloud_topic", "/objects_3d");
    this->declare_parameter<std::string>("detection3d_topic", "/detections_3d");
    this->declare_parameter<std::string>("output_frame", "camera_color_optical_frame");
    this->declare_parameter<double>("center_depth_region_scale", 0.4);
    this->declare_parameter<std::vector<std::string>>(
      "allowed_classes", {"cup", "bottle", "book", "bowl"});

    std::string rgb_topic;
    std::string depth_topic;
    std::string camera_info_topic;
    std::string detections_topic;
    std::string pointcloud_topic;
    std::string detection3d_topic;
    std::string output_frame;
    double center_depth_region_scale;
    std::vector<std::string> allowed_classes;

    this->get_parameter("rgb_topic", rgb_topic);
    this->get_parameter("depth_topic", depth_topic);
    this->get_parameter("camera_info_topic", camera_info_topic);
    this->get_parameter("detections_topic", detections_topic);
    this->get_parameter("pointcloud_topic", pointcloud_topic);
    this->get_parameter("detection3d_topic", detection3d_topic);
    this->get_parameter("output_frame", output_frame);
    this->get_parameter("center_depth_region_scale", center_depth_region_scale);
    this->get_parameter("allowed_classes", allowed_classes);

    RCLCPP_INFO(this->get_logger(), "Project To 3D Object Node Initialized");

    rgb_sub_.subscribe(this, rgb_topic);
    depth_sub_.subscribe(this, depth_topic);
    info_sub_.subscribe(this, camera_info_topic);
    detections_sub_.subscribe(this, detections_topic);

    tf_buffer_.setCreateTimerInterface(
      std::make_shared<tf2_ros::CreateTimerROS>(
        this->get_node_base_interface(),
        this->get_node_timers_interface()));

    sync_.reset(new Sync(SyncPolicy(10), rgb_sub_, depth_sub_, info_sub_, detections_sub_));
    sync_->registerCallback(std::bind(
      &ProjectTo3DNode::imageCallback,
      this,
      std::placeholders::_1,
      std::placeholders::_2,
      std::placeholders::_3,
      std::placeholders::_4));

    pointcloud_pub_ = this->create_publisher<sensor_msgs::msg::PointCloud2>(pointcloud_topic, 10);
    detection_pub_ = this->create_publisher<vision_msgs::msg::Detection3DArray>(detection3d_topic, 10);

    allowed_classes_ = std::move(allowed_classes);
    output_frame_ = std::move(output_frame);
    center_depth_region_scale_ = static_cast<float>(std::clamp(center_depth_region_scale, 0.1, 1.0));
  }

private:
  typedef message_filters::sync_policies::ApproximateTime<
    sensor_msgs::msg::Image,
    sensor_msgs::msg::Image,
    sensor_msgs::msg::CameraInfo,
    bboxes_ex_msgs::msg::BoundingBoxes> SyncPolicy;
  typedef message_filters::Synchronizer<SyncPolicy> Sync;

  message_filters::Subscriber<sensor_msgs::msg::Image> rgb_sub_;
  message_filters::Subscriber<sensor_msgs::msg::Image> depth_sub_;
  message_filters::Subscriber<sensor_msgs::msg::CameraInfo> info_sub_;
  message_filters::Subscriber<bboxes_ex_msgs::msg::BoundingBoxes> detections_sub_;
  std::shared_ptr<Sync> sync_;

  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr pointcloud_pub_;
  rclcpp::Publisher<vision_msgs::msg::Detection3DArray>::SharedPtr detection_pub_;

  std::vector<std::string> allowed_classes_;
  std::string output_frame_;
  float center_depth_region_scale_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;

  static Eigen::Affine3f transformToEigen(const geometry_msgs::msg::Transform & transform) {
    const Eigen::Translation3f translation(
      static_cast<float>(transform.translation.x),
      static_cast<float>(transform.translation.y),
      static_cast<float>(transform.translation.z));
    const Eigen::Quaternionf rotation(
      static_cast<float>(transform.rotation.w),
      static_cast<float>(transform.rotation.x),
      static_cast<float>(transform.rotation.y),
      static_cast<float>(transform.rotation.z));
    return translation * rotation.normalized();
  }

  static sensor_msgs::msg::PointCloud2 toRosCloudMsg(
    const pcl::PointCloud<pcl::PointXYZRGB> & cloud,
    const std_msgs::msg::Header & header,
    const std::string & frame_id) {
    sensor_msgs::msg::PointCloud2 cloud_msg;
    pcl::toROSMsg(cloud, cloud_msg);
    cloud_msg.header = header;
    cloud_msg.header.frame_id = frame_id;
    return cloud_msg;
  }

  static float computeMedianDepth(std::vector<float> & depths) {
    const std::size_t mid = depths.size() / 2;
    std::nth_element(depths.begin(), depths.begin() + mid, depths.end());
    const float upper = depths[mid];
    if ((depths.size() % 2U) != 0U) {
      return upper;
    }

    std::nth_element(depths.begin(), depths.begin() + mid - 1, depths.begin() + mid);
    const float lower = depths[mid - 1];
    return 0.5f * (lower + upper);
  }

  void imageCallback(
    const sensor_msgs::msg::Image::ConstSharedPtr & rgb_msg,
    const sensor_msgs::msg::Image::ConstSharedPtr & depth_msg,
    const sensor_msgs::msg::CameraInfo::ConstSharedPtr & info_msg,
    const bboxes_ex_msgs::msg::BoundingBoxes::ConstSharedPtr & detections_msg) {
    if (!rgb_msg || !depth_msg || !info_msg || !detections_msg) {
      RCLCPP_ERROR(this->get_logger(), "Received null message(s).");
      return;
    }
    if ((rgb_msg->height != depth_msg->height) || (rgb_msg->width != depth_msg->width)) {
      RCLCPP_ERROR(this->get_logger(), "Image sizes are different.");
      return;
    }

    try {
      const cv::Mat rgb = cv_bridge::toCvShare(rgb_msg, "bgr8")->image;
      const cv::Mat depth = cv_bridge::toCvShare(depth_msg)->image;

      const float fx = info_msg->k[0];
      const float fy = info_msg->k[4];
      const float cx = info_msg->k[2];
      const float cy = info_msg->k[5];

      if (fx == 0.0f || fy == 0.0f) {
        RCLCPP_ERROR(this->get_logger(), "Camera intrinsics fx or fy is zero.");
        return;
      }

      const std::string source_frame = rgb_msg->header.frame_id;
      const std::string published_frame = output_frame_.empty() ? source_frame : output_frame_;
      const bool needs_transform = !published_frame.empty() && published_frame != source_frame;

      Eigen::Affine3f output_from_source = Eigen::Affine3f::Identity();
      if (needs_transform) {
        try {
          const auto transform = tf_buffer_.lookupTransform(
            published_frame, source_frame, rgb_msg->header.stamp, tf2::durationFromSec(0.2));
          output_from_source = transformToEigen(transform.transform);
        } catch (const tf2::TransformException & ex) {
          RCLCPP_WARN(
            this->get_logger(),
            "Skipping detection projection because transform '%s' <- '%s' at %.9f is unavailable: %s",
            published_frame.c_str(),
            source_frame.c_str(),
            rclcpp::Time(rgb_msg->header.stamp).seconds(),
            ex.what());
          return;
        }
      }

      pcl::PointCloud<pcl::PointXYZRGB> total_cloud;
      vision_msgs::msg::Detection3DArray detection_array;
      detection_array.header = rgb_msg->header;
      detection_array.header.frame_id = published_frame;

      for (const auto & bbox : detections_msg->bounding_boxes) {
        const Detection det{
          bbox.class_id,
          bbox.probability,
          bbox.xmin,
          bbox.ymin,
          bbox.xmax,
          bbox.ymax
        };

        if (
          !allowed_classes_.empty() &&
          std::find(allowed_classes_.begin(), allowed_classes_.end(), det.class_name) ==
            allowed_classes_.end()) {
          RCLCPP_DEBUG(this->get_logger(), "Skipping detection: %s", det.class_name.c_str());
          continue;
        }
        if (det.confidence < 0.3f) {
          RCLCPP_DEBUG(
            this->get_logger(),
            "Skipping detection with low confidence: %s (%.2f)",
            det.class_name.c_str(),
            det.confidence);
          continue;
        }
        if (det.x_min < 0 || det.y_min < 0 || det.x_max > rgb.cols || det.y_max > rgb.rows) {
          RCLCPP_DEBUG(
            this->get_logger(),
            "Skipping detection with out-of-bounds coordinates: %s",
            det.class_name.c_str());
          continue;
        }
        if (det.x_min >= det.x_max || det.y_min >= det.y_max) {
          RCLCPP_DEBUG(
            this->get_logger(),
            "Skipping detection with invalid bounding box: %s",
            det.class_name.c_str());
          continue;
        }

        try {
          const int bbox_width = det.x_max - det.x_min;
          const int bbox_height = det.y_max - det.y_min;
          const int center_width = std::max(
            1,
            static_cast<int>(std::round(static_cast<float>(bbox_width) * center_depth_region_scale_)));
          const int center_height = std::max(
            1,
            static_cast<int>(std::round(static_cast<float>(bbox_height) * center_depth_region_scale_)));
          const int center_x_min = det.x_min + std::max(0, (bbox_width - center_width) / 2);
          const int center_y_min = det.y_min + std::max(0, (bbox_height - center_height) / 2);
          const int center_x_max = std::min(det.x_max, center_x_min + center_width);
          const int center_y_max = std::min(det.y_max, center_y_min + center_height);
          const int bbox_center_x = det.x_min + bbox_width / 2;
          const int bbox_center_y = det.y_min + bbox_height / 2;

          std::vector<float> center_depth_samples;
          center_depth_samples.reserve(
            static_cast<std::size_t>(std::max(1, (center_x_max - center_x_min) * (center_y_max - center_y_min))));
          for (int img_y = center_y_min; img_y < center_y_max; ++img_y) {
            for (int img_x = center_x_min; img_x < center_x_max; ++img_x) {
              const uint16_t z_raw = depth.at<uint16_t>(img_y, img_x);
              const float z = static_cast<float>(z_raw) * 0.001f;
              if (!std::isfinite(z) || z <= 0.0f || z > 3.0f) {
                continue;
              }
              center_depth_samples.push_back(z);
            }
          }
          if (center_depth_samples.empty()) {
            RCLCPP_DEBUG(
              this->get_logger(),
              "Skipping detection with no valid depth in bbox center region: %s",
              det.class_name.c_str());
            continue;
          }
          const float center_depth = computeMedianDepth(center_depth_samples);

          const cv::Mat roi =
            depth(cv::Rect(det.x_min, det.y_min, det.x_max - det.x_min, det.y_max - det.y_min));
          pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud(new pcl::PointCloud<pcl::PointXYZRGB>());

          for (int v = 0; v < roi.rows; ++v) {
            for (int u = 0; u < roi.cols; ++u) {
              const uint16_t z_raw = roi.at<uint16_t>(v, u);
              const float z = static_cast<float>(z_raw) * 0.001f;
              if (!std::isfinite(z) || z <= 0.0f || z > 3.0f) {
                continue;
              }

              const int img_x = u + det.x_min;
              const int img_y = v + det.y_min;
              if (img_x < 0 || img_x >= rgb.cols || img_y < 0 || img_y >= rgb.rows) {
                continue;
              }

              const float x = (static_cast<float>(img_x) - cx) * z / fx;
              const float y = (static_cast<float>(img_y) - cy) * z / fy;
              if (!std::isfinite(x) || !std::isfinite(y)) {
                continue;
              }

              pcl::PointXYZRGB point;
              point.x = x;
              point.y = y;
              point.z = z;
              const cv::Vec3b color = rgb.at<cv::Vec3b>(img_y, img_x);
              point.r = color[2];
              point.g = color[1];
              point.b = color[0];
              cloud->points.push_back(point);
            }
          }

          const float coverage = static_cast<float>(cloud->size()) / (roi.rows * roi.cols);
          if (coverage < 0.1f) {
            RCLCPP_DEBUG(
              this->get_logger(),
              "Skipping detection with low coverage: %s (coverage: %.2f)",
              det.class_name.c_str(),
              coverage);
            continue;
          }

          pcl::StatisticalOutlierRemoval<pcl::PointXYZRGB> sor;
          sor.setInputCloud(cloud);
          sor.setMeanK(20);
          sor.setStddevMulThresh(1.0);
          sor.filter(*cloud);

          std::vector<int> indices;
          pcl::removeNaNFromPointCloud(*cloud, *cloud, indices);
          if (cloud->empty()) {
            RCLCPP_DEBUG(
              this->get_logger(),
              "Cloud is empty after removing NaNs for detection: %s",
              det.class_name.c_str());
            continue;
          }

          if (needs_transform) {
            pcl::PointCloud<pcl::PointXYZRGB>::Ptr transformed_cloud(
              new pcl::PointCloud<pcl::PointXYZRGB>());
            pcl::transformPointCloud(*cloud, *transformed_cloud, output_from_source);
            cloud = transformed_cloud;
          }

          total_cloud += *cloud;

          Eigen::Vector3f target_position(
            (static_cast<float>(bbox_center_x) - cx) * center_depth / fx,
            (static_cast<float>(bbox_center_y) - cy) * center_depth / fy,
            center_depth);
          if (needs_transform) {
            target_position = output_from_source * target_position;
          }

          pcl::PointXYZRGB min_pt;
          pcl::PointXYZRGB max_pt;
          pcl::getMinMax3D(*cloud, min_pt, max_pt);

          vision_msgs::msg::Detection3D detection;
          detection.header = rgb_msg->header;
          detection.header.frame_id = published_frame;

          vision_msgs::msg::ObjectHypothesisWithPose hypo;
          hypo.id = det.class_name;
          hypo.score = det.confidence;
          hypo.pose.pose.position.x = target_position.x();
          hypo.pose.pose.position.y = target_position.y();
          hypo.pose.pose.position.z = target_position.z();
          hypo.pose.pose.orientation.w = 1.0;

          detection.results.push_back(hypo);
          detection.bbox.center = hypo.pose.pose;
          detection.bbox.size.x = max_pt.x - min_pt.x;
          detection.bbox.size.y = max_pt.y - min_pt.y;
          detection.bbox.size.z = max_pt.z - min_pt.z;

          detection_array.detections.push_back(detection);
        } catch (const cv::Exception & e) {
          RCLCPP_ERROR(this->get_logger(), "OpenCV exception in detection loop: %s", e.what());
          continue;
        } catch (const std::exception & e) {
          RCLCPP_ERROR(this->get_logger(), "Standard exception in detection loop: %s", e.what());
          continue;
        } catch (...) {
          RCLCPP_ERROR(this->get_logger(), "Unknown exception in detection loop");
          continue;
        }
      }

      pointcloud_pub_->publish(toRosCloudMsg(total_cloud, rgb_msg->header, published_frame));
      detection_pub_->publish(detection_array);
    } catch (const cv::Exception & e) {
      RCLCPP_ERROR(this->get_logger(), "OpenCV exception in imageCallback: %s", e.what());
    } catch (const std::exception & e) {
      RCLCPP_ERROR(this->get_logger(), "Standard exception in imageCallback: %s", e.what());
    } catch (...) {
      RCLCPP_ERROR(this->get_logger(), "Unknown exception in imageCallback");
    }
  }
};

int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ProjectTo3DNode>());
  rclcpp::shutdown();
  return 0;
}
