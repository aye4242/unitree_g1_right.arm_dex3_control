"""
读取 G1_29 双臂 14 个关节角度 (度) 并计算左右手 TCP 位姿。

用法:
    python read_dual_arm_joints.py          # 真机
    python read_dual_arm_joints.py --sim    # 仿真
    python read_dual_arm_joints.py --loop   # 持续打印 (默认 5 Hz)
"""
import argparse
import numpy as np
import os, sys, time

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import logging_mp
logging_mp.basicConfig(level=logging_mp.INFO)
logger_mp = logging_mp.getLogger(__name__)

import pinocchio as pin
from scipy.spatial.transform import Rotation as R

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from teleop.robot_control.robot_arm import G1_29_ArmController, G1_29_JointArmIndex
from teleop.robot_control.robot_arm_ik import G1_29_ArmIK

# 左臂关节名称（G1_29_JointArmIndex 枚举前 7 个）
LEFT_ARM_JOINT_NAMES = [
    "LeftShoulderPitch",    # index 15
    "LeftShoulderRoll",     # index 16
    "LeftShoulderYaw",      # index 17
    "LeftElbow",            # index 18
    "LeftWristRoll",        # index 19
    "LeftWristPitch",       # index 20
    "LeftWristYaw",         # index 21
]

# 右臂关节名称（G1_29_JointArmIndex 枚举后 7 个）
RIGHT_ARM_JOINT_NAMES = [
    "RightShoulderPitch",   # index 22
    "RightShoulderRoll",    # index 23
    "RightShoulderYaw",     # index 24
    "RightElbow",           # index 25
    "RightWristRoll",       # index 26
    "RightWristPitch",      # index 27
    "RightWristYaw",        # index 28
]


def print_arm_info(arm_name, joint_names, q_rad, tcp_pose):
    """打印单臂关节角度和 TCP 位姿"""
    q_deg = np.degrees(q_rad)

    print(f"\n  {arm_name} 关节角度")
    print("─" * 60)
    for name, deg, rad in zip(joint_names, q_deg, q_rad):
        print(f"  {name:>22s}:  {deg:+8.2f}°  ({rad:+7.4f} rad)")

    pos = tcp_pose.translation
    rpy_deg = np.degrees(R.from_matrix(tcp_pose.rotation).as_euler('xyz'))

    print(f"\n  {arm_name} TCP 位姿 (相对于 pelvis)")
    print("─" * 60)
    print(f"  位置 X: {pos[0]:+.5f} m")
    print(f"  位置 Y: {pos[1]:+.5f} m")
    print(f"  位置 Z: {pos[2]:+.5f} m")
    print(f"  Roll  : {rpy_deg[0]:+.2f}°")
    print(f"  Pitch : {rpy_deg[1]:+.2f}°")
    print(f"  Yaw   : {rpy_deg[2]:+.2f}°")
    print(f"\n  4x4 齐次变换矩阵:")
    print(tcp_pose.homogeneous)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="读取 G1_29 双臂关节角度及 TCP 位姿")
    parser.add_argument('--sim', action='store_true', help='启用仿真模式')
    parser.add_argument('--loop', action='store_true', help='持续循环打印')
    parser.add_argument('--hz', type=float, default=5.0, help='打印频率 (默认 5 Hz)')
    parser.add_argument('--network-interface', type=str, default=None)
    args = parser.parse_args()

    domain_id = 1 if args.sim else 0
    ChannelFactoryInitialize(domain_id, networkInterface=args.network_interface)

    # motion_mode=False: 只订阅状态，不接管机器人运动
    arm_ctrl = G1_29_ArmController(motion_mode=False, simulation_mode=args.sim)

    # 加载 IK 模型（含 Pinocchio 运动学模型，用于正解 FK）
    arm_ik = G1_29_ArmIK()
    model = arm_ik.reduced_robot.model
    data  = arm_ik.reduced_robot.data

    l_ee_id = model.getFrameId("L_ee")
    r_ee_id = model.getFrameId("R_ee")

    dt = 1.0 / args.hz

    while True:
        # 1. 读取 14 维关节角度: 前 7 左臂, 后 7 右臂
        dual_arm_q_rad = arm_ctrl.get_current_dual_arm_q()
        left_arm_q_rad  = dual_arm_q_rad[:7]
        right_arm_q_rad = dual_arm_q_rad[7:]

        # 2. 正运动学 FK
        pin.framesForwardKinematics(model, data, dual_arm_q_rad)
        l_pose = data.oMf[l_ee_id]
        r_pose = data.oMf[r_ee_id]

        # 3. 打印
        print("\n" + "═" * 60)
        print_arm_info("左臂", LEFT_ARM_JOINT_NAMES, left_arm_q_rad, l_pose)
        print("\n" + "─" * 60)
        print_arm_info("右臂", RIGHT_ARM_JOINT_NAMES, right_arm_q_rad, r_pose)
        print("═" * 60)

        if not args.loop:
            break

        time.sleep(dt)
