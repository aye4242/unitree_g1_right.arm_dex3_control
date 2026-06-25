# 相机外参重标定流程

> **适用场景**：按压不同按键偏差方向不一致（参差不齐），说明相机外参旋转分量有误差，需重标定。

---

## 标定原理

采集 N 组「相机坐标系3D点 ↔ torso_link坐标系3D点」配对，用 SVD 求解刚体变换：

```
camera_color_optical_frame  →  [T_cam→torso]  →  torso_link
```

**与指甲盖标定方案的区别**：本方案将 AprilTag 固定在外部已知位置，通过手臂物理触碰 tag 中心精确获取 robot_point，无需指甲盖偏移补偿，也不依赖手臂姿态多样性。

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

> ⚠️ **关键**：必须覆盖上/中/下三个高度，否则 pitch 角分量无法约束，标定后仍然会出现上下偏差参差不齐的问题。

---

## 步骤一：启动基础环境

> ⚠️ **注意**：标定时**不要启动 RealSense ROS 节点**，v4l2_apriltag_trigger 会直接开相机（v4l2），两者同时运行会独占冲突导致采集失败。

**终端1**（容器）：机器人节点
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch unitree_g1_dex3_stack robot.launch.py \
  tf_topic:=/unitree_g1_dex3/tf tf_static_topic:=/unitree_g1_dex3/tf_static
```

**终端2**（容器）：发布当前相机静态 TF（采集期间保持运行）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run tf2_ros static_transform_publisher \
  0.057624 0.017529 0.429869 \
  -0.659252 0.659252 -0.255707 0.255707 \
  torso_link camera_color_optical_frame \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static
```

**终端3**（容器）：重力补偿自由拖动（**同一终端**切换 free/lock，不能开两个进程）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
python3 /workspaces/unitree_dex3/right_arm_mode.py \
  --mode interactive --network-interface enP8p1s0
```
> 输入 `free` 进入重力补偿模式手动拖动手臂；输入 `lock` 锁定当前姿态。

**终端4**（容器）：AprilTag 检测节点（保持运行，每组数据都在此按 `g`）
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

**终端5**（容器）：读取 TCP 坐标（每组 lock 后在此读）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run tf2_ros tf2_echo \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static \
  -- torso_link right_tcp_link
```

预览相机画面(本机):

```
sshpass -p 123 ssh unitree@192.168.100.30 "ffmpeg -f v4l2 -i /dev/video4 -frames:v 1 /tmp/live.jpg -y 2>/dev/null" \
  && sshpass -p 123 scp unitree@192.168.100.30:/tmp/live.jpg /tmp/ \
  && xdg-open /tmp/live.jpg
```

---

## 步骤二：逐点采集数据

每组采集流程如下，重复 6~10 次（每次换 AprilTag 位置）：

### 2.1 固定 AprilTag，获取相机坐标（camera_point）

1. 将 AprilTag 贴在面板目标位置（硬卡纸平整，tag 朝向相机）
2. 在**终端4**按 `g` 触发采集

检测成功后日志输出：
```
detect_only accepted=4/4 tag=(x, y, z) @ camera_color_optical_frame
```
**记录 `tag=(x, y, z)` → 这就是 camera_point**

> 若 accepted < 4/4，该组数据**不采用**，调整 tag 位置或光线后重试。

### 2.2 拖动手臂触碰 tag 中心，获取机器人坐标（robot_point）

1. **终端3**输入 `free`
2. 手动将中指指尖拖到 AprilTag **中心**，指尖垂直轻触 tag 平面中心
3. **终端3**输入 `lock`，等手臂静止（1~2秒）
4. 在**终端5**读取：
   ```
   Translation: [x, y, z]
   ```
   **记录 `Translation: [x, y, z]` → 这就是 robot_point**

> ⚠️ 手臂必须**静止**且手指**实际接触** tag 中心时读取，误差控制在5mm以内。

### 2.3 记录到 JSON

**第一次采集前清空旧数据**：
```bash
echo '{"camera_points": [], "robot_points": []}' > \
  /workspaces/unitree_dex3/elevator_vision/scripts/calibration/calibration_data.json
```

将每组点对追加到文件，最终格式：
```json
{
  "camera_points": [[x1, y1, z1], [x2, y2, z2]],
  "robot_points":  [[x1, y1, z1], [x2, y2, z2]]
}
```

---

## 步骤三：计算新变换矩阵

```bash
cd /workspaces/unitree_dex3/elevator_vision/scripts/calibration
python3 compute_transform.py
```

输出矩阵后**检查第一行第四列**（相机 X 位置）：

```
[[ ...   ...   ...   0.057 ]   ← 此值必须 > 0.04，否则数据分布有问题
 [ ...   ...   ...   0.017 ]
 [ ...   ...   ...   0.430 ]
 [  0.    0.    0.    1.   ]]
```

---

## 步骤四：更新外参参数

运行以下脚本一次性提取所有需要更新的参数：

```bash
python3 - << 'EOF'
import numpy as np
from scipy.spatial.transform import Rotation as R

T = np.load('/workspaces/unitree_dex3/elevator_vision/transforms/camera_to_robot.npy')
t = T[:3, 3]
q = R.from_matrix(T[:3, :3]).as_quat()  # [qx, qy, qz, qw]

# URDF d435_joint: 去掉 optical_frame 旋转分量（chain: d435→camera_link→color_frame→optical）
q_d435 = R.from_quat(q) * R.from_quat([-0.5, 0.5, -0.5, 0.5]).inv()
rpy = q_d435.as_euler('xyz')

print("=== 1. elevator_button_press.launch.py ===")
print(f"  '{t[0]:.6f}', '{t[1]:.6f}', '{t[2]:.6f}',")
print(f"  '{q[0]:.6f}', '{q[1]:.6f}', '{q[2]:.6f}', '{q[3]:.6f}',")
print(f"  'torso_link', 'camera_color_optical_frame',")
print()
print("=== 2. URDF d435_joint ===")
print(f'<origin xyz="{t[0]:.7f} {t[1]:.7f} {t[2]:.7f}"')
print(f'        rpy="{rpy[0]:.10f} {rpy[1]:.10f} {rpy[2]:.10f}"/>')
print()
print("=== 3. static_transform_publisher 备用参数 ===")
print(f"  {t[0]:.6f} {t[1]:.6f} {t[2]:.6f} {q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}")
print(f"  torso_link camera_color_optical_frame")
EOF
```

**4.1** 将输出的 `launcher` 参数替换到 `elevator_button_press.launch.py` 的 `camera_to_robot_tf` 节点中。

**4.2** 将输出的 URDF 参数替换到：
```
unitree_dex3/src/unitree_g1_dex3_stack-main/robots/g1_description/g1_29dof_with_hand_rev_1_0.urdf
```
找到 `d435_joint` 的 `<origin>` 行并替换。

**4.3** 重新编译（容器内）：
```bash
cd /workspaces/unitree_dex3
colcon build --packages-select unitree_g1_dex3_stack
```

**4.4** 同时更新步骤二终端2中的 static_transform_publisher 参数，方便下次重标定时使用正确的当前值。

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
| **覆盖范围** | 必须有上/中/下三个高度，否则 pitch 角约束不足 |
| **数据质量** | 只用 `accepted=4/4` 的检测结果 |
| **标定结果验证** | 矩阵 `T[0,3]`（相机X）必须 > 0.04m，否则数据分布有问题 |
| **机器人姿态** | 采集时机器人站立姿态与实际按压时保持一致 |
| **AprilTag平整** | tag 必须贴在平整硬板上，翘曲会导致 PnP 检测误差 |
| **TCP触碰精度** | 手指中心对准 tag 中心，误差控制在5mm以内 |
| **旧数据清空** | 新标定前清空旧的 `calibration_data.json` |
| **重标定后需重部署** | 更新 launch 文件后记得同步到 `install_container`（见 README-elevator-vision.md 部署章节）|

---

## 当前外参参考值（标定前）

```
torso_link → camera_color_optical_frame
平移：0.057624, 0.017529, 0.429869
四元数(x,y,z,w)：-0.659252, 0.659252, -0.255707, 0.255707
```

如果标定后新值与上述值差异超过 **5cm / 5°**，建议检查采集过程是否有错误。
