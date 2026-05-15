#!/usr/bin/env python3
"""ROS 2 node: press K to trigger YOLO detection, then select nearest
detection and publish goal_pose."""

import os
import select
import termios
import tty
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty
from vision_msgs.msg import Detection3DArray
from geometry_msgs.msg import PoseStamped


class KeyboardTriggerNode(Node):
    def __init__(self):
        super().__init__('keyboard_trigger_node')
        self.waiting_for_result = False
        self.create_subscription(Detection3DArray, '/detections_3d', self.det_cb, 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)
        self.trigger_pub = self.create_publisher(Empty, '/yolo/trigger', 10)
        self.fd = os.open('/dev/tty', os.O_RDONLY | os.O_NONBLOCK)
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        self.create_timer(0.1, self.timer_callback)
        self.get_logger().info('[KeyboardTrigger] Ready — press K to trigger')

    def det_cb(self, msg):
        if not self.waiting_for_result:
            return
        self.waiting_for_result = False
        self.process_detections(msg)

    def timer_callback(self):
        if select.select([self.fd], [], [], 0.0)[0]:
            ch = os.read(self.fd, 1).decode('utf-8', errors='ignore')
            if ch in ('k', 'K'):
                self.trigger()

    def trigger(self):
        if self.waiting_for_result:
            self.get_logger().warn('[KeyboardTrigger] Already waiting for detection result')
            return
        self.get_logger().info('[KeyboardTrigger] K pressed — triggering YOLO inference')
        self.waiting_for_result = True
        self.trigger_pub.publish(Empty())

    def process_detections(self, msg):
        if len(msg.detections) == 0:
            self.get_logger().warn('[KeyboardTrigger] Detection returned 0 results')
            return
        best = None
        best_dist = float('inf')
        for det in msg.detections:
            p = det.bbox.center.position
            d = math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
            if d < best_dist:
                best_dist = d
                best = det
        cx = best.bbox.center.position.x
        cy = best.bbox.center.position.y
        cz = best.bbox.center.position.z
        sy = best.bbox.size.y
        y_bottom = cy + sy / 2.0
        y_target = y_bottom - sy * 0.1
        goal = PoseStamped()
        goal.header.frame_id = msg.header.frame_id
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.pose.position.x = cx
        goal.pose.position.y = y_target
        goal.pose.position.z = cz
        goal.pose.orientation.x = -0.68194788
        goal.pose.orientation.y =  0.06844694
        goal.pose.orientation.z = -0.07816853
        goal.pose.orientation.w =  0.72398328
        self.goal_pub.publish(goal)
        self.get_logger().info(
            f'[KeyboardTrigger] Targeting nearest object at '
            f'({cx:.3f}, {y_target:.3f}, {cz:.3f}), publishing /goal_pose')

    def destroy_node(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
        os.close(self.fd)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTriggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
