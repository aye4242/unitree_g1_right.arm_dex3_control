"""
free_arm_demo.py
────────────────
让 G1 机器人站立后，双臂电机卸力（kp=0, kd=极小阻尼），
你可以自由用手拖动双臂，其余关节保持锁定/平衡不受影响。

使用方法:
  1. 先让机器人进入站立模式
  2. 运行此脚本:
     cd teleop
     python free_arm_demo.py          # 默认与物理机器人通信
     python free_arm_demo.py --sim    # 仿真模式 (domain=1)
  3. Ctrl+C 退出后，双臂会缓慢回到站立姿态并还给底层站立控制器

注意: 默认使用 motion_mode=True (topic: rt/arm_sdk)，退出后腿部依旧受底层控制不倒。
"""

import time
import numpy as np
import argparse
import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sdk_dir = os.path.expanduser("~/unitree_sdk2_python")
if os.path.isdir(os.path.join(sdk_dir, "unitree_sdk2py")) and sdk_dir not in sys.path:
    sys.path.append(sdk_dir)

import logging_mp
logging_mp.basicConfig(level=logging_mp.INFO)
logger_mp = logging_mp.getLogger(__name__)

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from robot_control.robot_arm import (
    G1_29_ArmController, G1_29_JointArmIndex, G1_29_JointIndex,
    hg_LowCmd, hg_LowState,
    ChannelPublisher, ChannelSubscriber,
    unitree_hg_msg_dds__LowCmd_,
    DataBuffer, G1_29_LowState, G1_29_Num_Motors,
)
from unitree_sdk2py.utils.crc import CRC
import threading
from enum import IntEnum

# ─────────────────── 核心参数 ───────────────────
# 手臂卸力增益：kp=0 不做位置跟踪, kd 提供极小阻尼防止抖动
ARM_KP = 0.0
ARM_KD = 0.5          # 给一点点阻尼让手感更顺滑，设 0 完全无阻力
ARM_WRIST_KP = 0.0
ARM_WRIST_KD = 0.3

# 非手臂关节依旧按原来的高增益锁定（不要改这些！）
BODY_KP_HIGH = 300.0
BODY_KD_HIGH = 3.0
BODY_KP_LOW  = 80.0
BODY_KD_LOW  = 3.0

# 站立姿态下双臂关节角度 (rad)，退出时平滑回到这个姿态
# 顺序与 G1_29_JointArmIndex 一致:
#   L_ShoulderPitch, L_ShoulderRoll, L_ShoulderYaw, L_Elbow,
#   L_WristRoll, L_WristPitch, L_WristYaw,
#   R_ShoulderPitch, R_ShoulderRoll, R_ShoulderYaw, R_Elbow,
#   R_WristRoll, R_WristPitch, R_WristYaw
STANDING_ARM_Q = np.array([
    +0.2620, +0.2871, -0.0881, +0.8216, -0.0020, +0.0021, +0.0014,   # 左臂
    +0.2644, -0.2881, +0.0927, +0.7943, -0.0118, +0.0130, -0.0001,   # 右臂
])
# ────────────────────────────────────────────────

kTopicLowCommand_Motion = "rt/arm_sdk"
kTopicLowState = "rt/lowstate"


def is_weak_motor(motor_id_value):
    weak = {
        G1_29_JointIndex.kLeftAnklePitch.value,
        G1_29_JointIndex.kRightAnklePitch.value,
        G1_29_JointIndex.kLeftShoulderPitch.value,
        G1_29_JointIndex.kLeftShoulderRoll.value,
        G1_29_JointIndex.kLeftShoulderYaw.value,
        G1_29_JointIndex.kLeftElbow.value,
        G1_29_JointIndex.kRightShoulderPitch.value,
        G1_29_JointIndex.kRightShoulderRoll.value,
        G1_29_JointIndex.kRightShoulderYaw.value,
        G1_29_JointIndex.kRightElbow.value,
    }
    return motor_id_value in weak


def is_wrist_motor(motor_id_value):
    wrist = {
        G1_29_JointIndex.kLeftWristRoll.value,
        G1_29_JointIndex.kLeftWristPitch.value,
        G1_29_JointIndex.kLeftWristyaw.value,
        G1_29_JointIndex.kRightWristRoll.value,
        G1_29_JointIndex.kRightWristPitch.value,
        G1_29_JointIndex.kRightWristYaw.value,
    }
    return motor_id_value in wrist


def main():
    parser = argparse.ArgumentParser(description="G1 双臂自由拖拽模式")
    parser.add_argument("--sim", action="store_true", help="仿真模式 (domain=1)")
    args = parser.parse_args()

    domain_id = 1 if args.sim else 0
    ChannelFactoryInitialize(domain_id, networkInterface=None)
    logger_mp.info(f"Domain ID = {domain_id}  ({'SIM' if args.sim else 'REAL'})")

    # ---- DDS 通信初始化 ----
    lowcmd_pub = ChannelPublisher(kTopicLowCommand_Motion, hg_LowCmd)
    lowcmd_pub.Init()
    lowstate_sub = ChannelSubscriber(kTopicLowState, hg_LowState)
    lowstate_sub.Init()
    state_buf = DataBuffer()

    def subscribe_loop():
        while True:
            msg = lowstate_sub.Read()
            if msg is not None:
                ls = G1_29_LowState()
                for i in range(G1_29_Num_Motors):
                    ls.motor_state[i].q  = msg.motor_state[i].q
                    ls.motor_state[i].dq = msg.motor_state[i].dq
                state_buf.SetData(ls)
            time.sleep(0.002)

    t = threading.Thread(target=subscribe_loop, daemon=True)
    t.start()

    # 等待首次数据
    while state_buf.GetData() is None:
        logger_mp.warning("等待 DDS 数据...")
        time.sleep(0.1)
    logger_mp.info("DDS 订阅成功！")

    # ---- 构建命令消息 ----
    crc = CRC()
    msg = unitree_hg_msg_dds__LowCmd_()
    msg.mode_pr = 0
    msg.mode_machine = lowstate_sub.Read().mode_machine

    # 读取当前所有关节角度
    state = state_buf.GetData()
    all_q = np.array([state.motor_state[jid].q for jid in G1_29_JointIndex])

    arm_indices = set(member.value for member in G1_29_JointArmIndex)

    for jid in G1_29_JointIndex:
        msg.motor_cmd[jid].mode = 1

        if jid.value in arm_indices:
            # ★ 手臂关节：卸力 ★
            if is_wrist_motor(jid.value):
                msg.motor_cmd[jid].kp = ARM_WRIST_KP
                msg.motor_cmd[jid].kd = ARM_WRIST_KD
            else:
                msg.motor_cmd[jid].kp = ARM_KP
                msg.motor_cmd[jid].kd = ARM_KD
            # q 目标设为当前值（kp=0 时其实不影响）
            msg.motor_cmd[jid].q  = all_q[jid]
            msg.motor_cmd[jid].dq = 0
            msg.motor_cmd[jid].tau = 0
        else:
            # ★ 身体其余关节：高增益锁定 ★
            if is_weak_motor(jid.value):
                msg.motor_cmd[jid].kp = BODY_KP_LOW
                msg.motor_cmd[jid].kd = BODY_KD_LOW
            else:
                msg.motor_cmd[jid].kp = BODY_KP_HIGH
                msg.motor_cmd[jid].kd = BODY_KD_HIGH
            msg.motor_cmd[jid].q  = all_q[jid]

    # motion mode 权重 = 1 → 底层站立控制器仍在工作
    msg.motor_cmd[G1_29_JointIndex.kNotUsedJoint0].q = 1.0

    logger_mp.info("✅ 手臂已卸力，你可以自由拖动双臂了！")
    logger_mp.info(f"   手臂 kp={ARM_KP}, kd={ARM_KD}")
    logger_mp.info(f"   腕部 kp={ARM_WRIST_KP}, kd={ARM_WRIST_KD}")
    logger_mp.info("   按 Ctrl+C 退出（手臂将回零并释放）")

    ctrl_dt = 1.0 / 250.0

    try:
        while True:
            start = time.time()

            # 持续读取手臂当前角度并回写（kp=0 时实际没有位置控制力，
            # 但保持 q 命令跟随真实角度，方便退出时知道当前位置）
            cur_state = state_buf.GetData()
            if cur_state is not None:
                for jid in G1_29_JointArmIndex:
                    msg.motor_cmd[jid].q = cur_state.motor_state[jid].q

            msg.crc = crc.Crc(msg)
            lowcmd_pub.Write(msg)

            elapsed = time.time() - start
            time.sleep(max(0, ctrl_dt - elapsed))

    except KeyboardInterrupt:
        logger_mp.info("⚠️ 收到退出信号，手臂缓慢回到站立姿态中...")

        # 先读取当前手臂角度作为插值起点
        cur_state = state_buf.GetData()
        start_q = np.array([cur_state.motor_state[jid].q for jid in G1_29_JointArmIndex])
        target_q = STANDING_ARM_Q

        # 恢复 kp/kd（让电机有位置控制力）
        for jid in G1_29_JointArmIndex:
            if is_wrist_motor(jid.value):
                msg.motor_cmd[jid].kp = 40.0
                msg.motor_cmd[jid].kd = 1.5
            else:
                msg.motor_cmd[jid].kp = 80.0
                msg.motor_cmd[jid].kd = 3.0
            msg.motor_cmd[jid].tau = 0.0

        # 平滑插值：从当前位置 → 站立姿态 (约3秒, 750步@250Hz)
        num_interp_steps = 750
        for step in range(num_interp_steps + 1):
            alpha = step / num_interp_steps
            interp_q = start_q + alpha * (target_q - start_q)
            for idx, jid in enumerate(G1_29_JointArmIndex):
                msg.motor_cmd[jid].q = interp_q[idx]
            msg.crc = crc.Crc(msg)
            lowcmd_pub.Write(msg)
            time.sleep(ctrl_dt)

        # 到位后再保持一小段时间确保稳定
        for _ in range(250):  # ~1秒
            msg.crc = crc.Crc(msg)
            lowcmd_pub.Write(msg)
            time.sleep(ctrl_dt)

        # 逐步释放 motion mode 权重
        for w in np.linspace(1, 0, num=101):
            msg.motor_cmd[G1_29_JointIndex.kNotUsedJoint0].q = w
            msg.crc = crc.Crc(msg)
            lowcmd_pub.Write(msg)
            time.sleep(0.02)

        logger_mp.info("✅ 手臂已回到站立姿态，控制权已归还给底层站立控制器。")


if __name__ == "__main__":
    main()
