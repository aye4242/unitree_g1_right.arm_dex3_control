#!/usr/bin/env python3
"""ROS 2 node that runs Ultralytics YOLO inference on demand.
Caches the latest frame and only runs inference when triggered via
/yolo/trigger (std_msgs/Empty)."""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from sensor_msgs.msg import Image
from std_msgs.msg import Empty
from bboxes_ex_msgs.msg import BoundingBox, BoundingBoxes
from cv_bridge import CvBridge
import cv2

from ultralytics import YOLO


class UltralyticsDetectorNode(Node):
    def __init__(self):
        super().__init__('ultralytics_detector')

        # ---------- parameters ----------
        self.declare_parameter('model_path', '')
        self.declare_parameter('conf', 0.3)
        self.declare_parameter('nms', 0.45)
        self.declare_parameter('imshow_isshow', True)
        self.declare_parameter('device', '')
        self.declare_parameter('src_image_topic_name', '/camera/color/image_raw')
        self.declare_parameter('publish_boundingbox_topic_name',
                               '/yolo/bounding_boxes')
        self.declare_parameter('publish_image_topic_name',
                               '/yolo/image_raw')

        model_path = self.get_parameter('model_path').value
        self.conf = self.get_parameter('conf').value
        self.iou = self.get_parameter('nms').value
        self.imshow = self.get_parameter('imshow_isshow').value
        device = self.get_parameter('device').value
        src_topic = self.get_parameter('src_image_topic_name').value
        bbox_topic = self.get_parameter('publish_boundingbox_topic_name').value

        # ---------- model ----------
        self.model = YOLO(model_path)
        if device:
            self.model.to(device)
        self.get_logger().info(f'Loaded model: {model_path}')
        self.get_logger().info(f'Classes: {self.model.names}')

        # ---------- ROS I/O ----------
        self.bridge = CvBridge()
        self.latest_msg = None
        self.pub_bboxes = self.create_publisher(BoundingBoxes, bbox_topic, 10)
        self.sub_image = self.create_subscription(
            Image, src_topic, self.image_callback, QoSProfile(depth=1))
        self.sub_trigger = self.create_subscription(
            Empty, '/yolo/trigger', self.trigger_callback, 10)

    # ------------------------------------------------------------------
    def image_callback(self, msg: Image):
        self.latest_msg = msg

    def trigger_callback(self, _msg: Empty):
        if self.latest_msg is None:
            self.get_logger().warn('Trigger received but no frame cached yet')
            return
        msg = self.latest_msg
        img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        results = self.model(img, conf=self.conf, iou=self.iou, verbose=False)

        bboxes_msg = BoundingBoxes()
        bboxes_msg.header = msg.header

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    bbox = BoundingBox()
                    bbox.probability = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    bbox.xmin = int(x1)
                    bbox.ymin = int(y1)
                    bbox.xmax = int(x2)
                    bbox.ymax = int(y2)
                    cls_id = int(box.cls[0])
                    bbox.class_id = self.model.names[cls_id]
                    bboxes_msg.bounding_boxes.append(bbox)

        self.pub_bboxes.publish(bboxes_msg)
        self.get_logger().info(f'Inference done: {len(bboxes_msg.bounding_boxes)} detections')

        # Save annotated image for inspection
        annotated = results[0].plot()
        save_path = '/home/unitree/Desktop/unitree_dex3/yolo_last_detection.jpg'
        cv2.imwrite(save_path, annotated)
        self.get_logger().info(f'Saved annotated image to {save_path}')

        if self.imshow:
            annotated = results[0].plot()
            cv2.imshow('YOLO Detection', annotated)
            cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = UltralyticsDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
