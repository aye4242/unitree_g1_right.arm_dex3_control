# 相机外参重标定流程

> **适用场景**：按压不同按键偏差方向不一致（参差不齐），说明相机外参旋转分量有误差，需重标定。

---

## 标定原理

采集 N 组「相机坐标系3D点 ↔ torso_link坐标系3D点」配对，用 SVD 求解刚体变换：

```
camera_color_optical_frame  →  [T_cam→torso]  →  torso_link
```

结果写入：
1. `elevator_vision/scripts/transforms/camera_to_robot.npy`（YOLO方案使用）
2. `elevator_button_press.launch.py` 中 static_transform_publisher 参数（TF2使用）

---

## 准备工作

- 打印 **AprilTag tag36h11 ID=0**，边长精确为 **8cm**，贴在硬卡纸上
- 至少需要采集 **6 组**点对，分布要求：

```
面板区域分布（最少6点）：

[TL] ← 左上角    [TR] ← 右上角
[ML] ← 左中      [MR] ← 右中
[BL] ← 左下      [BR] ← 右下
```

> ⚠️ **关键**：必须覆盖上/中/下三个高度，否则pitch角分量无法约束，标定后仍然会出现上下偏差参差不齐的问题。

---

## 步骤一：启动基础环境

> ⚠️ **注意**：标定时**不要启动 RealSense ROS 节点**，v4l2_apriltag_trigger 会直接开相机（v4l2），两者同时运行会独占冲突导致采集失败。

**终端1**：进容器，启动机器人节点
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch unitree_g1_dex3_stack robot.launch.py \
  tf_topic:=/unitree_g1_dex3/tf tf_static_topic:=/unitree_g1_dex3/tf_static
```

**终端2**：进同一容器，发布当前相机静态TF
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run tf2_ros static_transform_publisher \
  0.057624 0.017529 0.429869 \
  -0.659252 0.659252 -0.255707 0.255707 \
  torso_link camera_color_optical_frame \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static
```

**终端5**：进容器，启动运动规划器
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch unitree_g1_dex3_stack planner.launch.py \
  tf_topic:=/unitree_g1_dex3/tf tf_static_topic:=/unitree_g1_dex3/tf_static
```

**终端6**：进容器，启动关节控制器（`hold_indefinitely=true` 会导致新轨迹被丢弃，不要加）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch unitree_g1_dex3_stack control.launch.py \
  auto_return_to_standing:=false
```
> 手臂到位后保持约5秒，期间读TF记录坐标；5秒后才接受下一条 goal_pose。

---

## 步骤二：逐点采集数据

每组数据采集流程如下，重复6次（每次把 AprilTag 换到不同位置）：

### 2.1 获取相机坐标（camera_point）

将 AprilTag 固定到面板目标位置，运行 AprilTag 检测获取 tag 在相机系下的位置：

**终端3**：进容器，启动 AprilTag 检测节点（它会直接开相机，无需 RealSense 节点）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run unitree_g1_dex3_stack v4l2_apriltag_trigger.py \
  --ros-args \
  -p tag_family:=tag36h11 \
  -p tag_size:=0.08 \
  -p target_tag_id:=0 \
  -p offset_xyz:=[0.0,0.0,0.0] \
  -p detect_only:=true \
  -p camera_frame:=camera_color_optical_frame \
  -p output_frame:=camera_color_optical_frame \
  -r /tf:=/unitree_g1_dex3/tf \
  -r /tf_static:=/unitree_g1_dex3/tf_static
```

等出现 `Ready — trigger_key=g` 后，把 AprilTag 摆好，**在终端3里按 `g` 键**触发一次采集。

检测成功后日志会输出：
```
detect_only accepted=4/4 tag=(x, y, z) target=(...) @ camera_color_optical_frame
```
**直接从这行日志记录 `tag=(x, y, z)` → 这就是 camera_point**，不需要 echo topic。

**终端4**：进容器，读取 tag 坐标
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 topic echo /apriltag/tag_pose --once
# 记录 pose.position.x/y/z → 这是 camera_point
```

### 2.2 获取机器人坐标（robot_point）

手臂移动需要终端5/6的 planner + controller 正在运行。

**第一步**：按G后读取 `/apriltag/target_pose` 的近似 torso 坐标：
```bash
ros2 topic echo /apriltag/target_pose --once
# 假设输出: pose.position x=0.45 y=-0.10 z=0.15
```

**第二步（先伸手指）**：在宿主机终端运行（注意用 `/usr/bin/python3`，不是 conda 的 python3）：
```bash
/usr/bin/python3 /home/unitree/Desktop/unitree_dex3_cpp/example/control_dex3_right_setpoint.py \
  enP8p1s0 0.0 -1.05 -1.7 1.7 1.8 0.0 0.0
```
或在容器内运行：
```bash
/usr/bin/python3 /workspaces/unitree_dex3_cpp/example/control_dex3_right_setpoint.py \
  enP8p1s0 0.0 -1.05 -1.7 1.7 1.8 0.0 0.0
```

**第三步**：手臂先移到 tag 前方5cm（x减0.05，避免直接撞上）：

```bash
# 将上一步的 y/z 原值代入，x减0.05
  ros2 topic pub /goal_pose geometry_msgs/msg/PoseStamped '{
    header: {frame_id: "torso_link"},
    pose: {
      position: {x: 0.30, y: 0.0, z: 0.16},
      orientation: {x: 0.0, y: -0.7071, z: 0.0, w: 0.7071}
    }
  }' --once
```

**第三步**：等手臂停稳，每次x加0.02向前推，直到手指轻触 tag 中心：
```bash
# 逐步增大 x: 0.40 → 0.42 → 0.44 → 0.46，直到触碰
ros2 topic pub /goal_pose geometry_msgs/msg/PoseStamped '{
  header: {frame_id: "torso_link"},
  pose: {
    position: {x: 0.42, y: -0.10, z: 0.15},
    orientation: {x: 0.0, y: -0.7071, z: 0.0, w: 0.7071}
  }
}' --once
# 若左右/上下偏移，同样方式微调 y（正=向左）和 z（正=向上）
```

**第四步**：手臂静止后读取 TCP 坐标：
```bash
ros2 run tf2_ros tf2_echo \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static \
  -- torso_link right_tcp_link
# 记录 Translation: x/y/z → 这是 robot_point
```

> ⚠️ robot_point 必须在手臂**静止**且手指**实际接触** tag 中心时读取，误差控制在5mm以内。
> ℹ️ 手腕姿态看起来弯曲属于正常现象 — IK 只保证指尖位置正确，不影响标定精度。

**采完一组后让手臂回原位**（hold_indefinitely=true 时 return_to_standing topic 被忽略，用 goal_pose 代替）：
```bash
ros2 topic pub /goal_pose geometry_msgs/msg/PoseStamped '{
  header: {frame_id: "torso_link"},
  pose: {
    position: {x: 0.16, y: -0.25, z: -0.25},
    orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}
  }
}' --once
```

### 2.3 记录到 JSON

将每组点对追加到文件：

```
/workspaces/unitree_dex3/elevator_vision/scripts/calibration/calibration_data.json
```

格式：
```json
{
  "camera_points": [
    [x1_cam, y1_cam, z1_cam],
    [x2_cam, y2_cam, z2_cam],
    ...
  ],
  "robot_points": [
    [x1_torso, y1_torso, z1_torso],
    [x2_torso, y2_torso, z2_torso],
    ...
  ]
}
```

---

## 步骤三：计算新变换矩阵

```bash
cd /workspaces/unitree_dex3/elevator_vision/scripts/calibration
python3 compute_transform.py
# 输出新的 camera_to_robot.npy 到 ../transforms/camera_to_robot.npy
```

---

## 步骤四：更新 launch 文件中的 TF 参数

`camera_to_robot.npy` 是 T_cam→torso，launch 文件里的 static_transform_publisher 需要的是 T_torso→cam（逆变换）的平移和四元数。运行以下脚本自动提取：

```bash
python3 - << 'EOF'
import numpy as np
from scipy.spatial.transform import Rotation

T_cam_to_robot = np.load(
    '/workspaces/unitree_dex3/elevator_vision/scripts/transforms/camera_to_robot.npy')

# 求逆（T_torso→cam）
T_inv = np.linalg.inv(T_cam_to_robot)
t = T_inv[:3, 3]
q = Rotation.from_matrix(T_inv[:3, :3]).as_quat()  # x,y,z,w

print(f"\n=== 更新 launch 文件中 static_transform_publisher 的参数 ===")
print(f"平移 (x y z):       {t[0]:.6f} {t[1]:.6f} {t[2]:.6f}")
print(f"四元数 (x y z w):   {q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}")
print(f"\n替换 elevator_button_press.launch.py 中 arguments 字段为：")
print(f"  '{t[0]:.6f}', '{t[1]:.6f}', '{t[2]:.6f}',")
print(f"  '{q[0]:.6f}', '{q[1]:.6f}', '{q[2]:.6f}', '{q[3]:.6f}',")
print(f"  'torso_link', 'camera_color_optical_frame',")
EOF
```

将输出的值替换到 `elevator_button_press.launch.py` 的 `camera_to_robot_tf` 节点中：

```python
camera_to_robot_tf = Node(
    ...
    arguments=[
        '<新的x>', '<新的y>', '<新的z>',
        '<新的qx>', '<新的qy>', '<新的qz>', '<新的qw>',
        'torso_link', 'camera_color_optical_frame',
    ],
)
```

---

## 步骤五：验证标定结果

重新启动完整方案，观察 YOLO 检测日志：

```
[button_detector_node]: floor='5' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.136)
[button_detector_node]: floor='3' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.086)
[button_detector_node]: floor='1' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.036)
```

验证标准：
- 同列按键（如1、3、5）的 `y` 值应该接近（横向对齐）
- `z` 值按行递减，差值约等于实际按键间距
- dry_run 模式下，手臂轨迹目标点与按键视觉位置吻合

---

## ⚠️ 注意事项

| 注意点 | 说明 |
|---|---|
| **点对数量** | 至少6组，建议8~10组 |
| **覆盖范围** | 必须有上/中/下三个高度，否则pitch角约束不足 |
| **机器人姿态** | 采集时机器人站立姿态与实际按压时保持一致 |
| **AprilTag平整** | tag 必须贴在平整硬板上，翘曲会导致PnP检测误差 |
| **TCP触碰精度** | 手指中心对准tag中心，误差控制在5mm以内 |
| **深度对齐** | RealSense 必须开启 `align_depth.enable:=true`，否则深度和RGB不对齐 |
| **不要混用坐标系** | camera_point 必须是 `camera_color_optical_frame` 下的值，robot_point 必须是 `torso_link` 下的值 |
| **旧数据清空** | 新标定前删除或清空旧的 `calibration_data.json` |
| **重标定后需重部署** | 更新 launch 文件后记得同步到 `install_container`（见 README-elevator-vision.md 部署章节）|

---

## 当前外参参考值（标定前）

```
torso_link → camera_color_optical_frame
平移：0.057624, 0.017529, 0.429869
四元数(x,y,z,w)：-0.659252, 0.659252, -0.255707, 0.255707
```

如果标定后新值与上述值差异超过 **5cm / 5°**，建议检查采集过程是否有错误。
