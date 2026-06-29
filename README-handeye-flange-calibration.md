# 手眼标定：手背贴码规范化流程（推荐）

> **适用场景**：为 apriltag / elevator 视觉方案重新标定相机外参（`torso_link → camera_color_optical_frame`）。
>
> **方法**：眼在手外（Eye-to-Hand）—— 相机固定在躯干，AprilTag 板安装在灵巧手手背刚性底座，机械臂带着码运动，使用 `calibrateHandEye`（AX=XB）求解。全程在容器内运行。

---

## 为什么这个方法比"触碰点对法"更可靠

| 对比项 | 触碰点对法（旧） | 本方案（手背贴码） |
|---|---|---|
| 数据类型 | 仅位置 xyz | **完整位姿**（旋转 + 平移）|
| 求解算法 | SVD 点云匹配 | `calibrateHandEye`（AX=XB）|
| TCP 定义依赖 | 依赖 `right_tcp_link` 精确在指尖 | **不依赖 TCP 位置，EE 偏移由算法自动消除** |
| 典型精度 | ~28 mm | < 5 mm |

---

## 准备工作

### 打印标定板

- Tag 规格：**tag36h11 ID=0**，边长精确为 **3 cm**（用尺量确认打印尺寸）
- 打印在硬卡纸或铝塑板上，保证板面平整

### 安装到灵巧手手背

1. 找到灵巧手与手腕法兰连接的**固定底座**（手背靠近手腕一侧的金属/硬质塑料平面）
2. 用 **3M 双面胶**或结构胶将 AprilTag 板贴牢、贴平
3. 贴好后轻拨所有手指，确认：板子与任何手指无干涉，手指运动不会碰到或带歪板子
4. ⚠️ 整个标定采集过程中**板子不能移位**，否则必须重新采集全部数据

### 清空旧标定数据

```bash
echo '{"camera_points":[],"camera_quats":[],"robot_points":[],"robot_quats":[]}' > \
  /workspaces/unitree_dex3/elevator_vision/scripts/calibration/calibration_data_handeye.json
```

---

## 步骤一：启动基础环境

> ⚠️ **不要启动 RealSense ROS 节点**，v4l2 会直接开相机，两者会独占冲突。

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
  0.030168 0.053707 0.496973 \
  -0.656780 0.663322 -0.255468 0.251755 \
  torso_link camera_color_optical_frame \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static
```

**终端3**（容器）：重力补偿自由拖动（同一终端切换 free/lock，不能开两个进程）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
python3 /workspaces/unitree_dex3/right_arm_mode.py \
  --mode interactive --network-interface enP8p1s0
```
> 输入 `free` 进入重力补偿模式；输入 `lock` 锁定姿态。

**终端4**（容器）：AprilTag 检测节点（保持运行，每组数据在此按 `g`）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run unitree_g1_dex3_stack v4l2_apriltag_trigger.py \
    --ros-args \
    -p tag_family:=tag36h11 \
    -p tag_size:=0.030 \
    -p target_tag_id:=0 \
    -p detect_only:=true \
    -p camera_frame:=camera_color_optical_frame \
    -p output_frame:=camera_color_optical_frame \
    -p target_tag_id:=0 \
    -p detect_only:=true \
    -p camera_frame:=camera_color_optical_frame \
    -p output_frame:=camera_color_optical_frame \
    -p warmup_frames:=30 \
    -p warmup_min_s:=5.0 \
    -p quad_decimate:=1.0 \
    -p decision_margin_min:=15.0 \
    -r /tf:=/unitree_g1_dex3/tf \
    -r /tf_static:=/unitree_g1_dex3/tf_static
```

**终端5**（容器）：读取手掌 TF 坐标（每组 lock 后在此读）
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 run tf2_ros tf2_echo \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static \
  -- torso_link right_hand_palm_link
```

### 预览相机画面（本机）

```bash
sshpass -p 123 ssh unitree@192.168.100.30 \
  "ffmpeg -f v4l2 -i /dev/video4 -frames:v 1 /tmp/live.jpg -y 2>/dev/null" \
  && sshpass -p 123 scp unitree@192.168.100.30:/tmp/live.jpg /tmp/ \
  && xdg-open /tmp/live.jpg
```

---

## 步骤二：逐点采集数据（重复 15～25 次）

每组采集流程：

### 2.1 摆好手臂姿态

1. **终端2** 输入 `free`，手动将机械臂摆到新位置（手背上的 AprilTag 朝向相机，无遮挡）
2. **终端2** 输入 `lock`，等手臂完全静止（1～2 秒）

### 2.2 获取相机坐标（camera_point + camera_quat）

在**终端4**按 `g`，等日志出现：

```
detect_only accepted=4/4 tag=(cx, cy, cz) tag_quat=(cqx,cqy,cqz,cqw) @ camera_color_optical_frame
```

- 记录 `tag=(cx, cy, cz)` → **camera_point**
- 记录 `tag_quat=(cqx,cqy,cqz,cqw)` → **camera_quat**

> 若 accepted < 4/4，该组数据**不采用**，调整姿态或光线后重试。

### 2.3 获取机器人坐标（robot_point + robot_quat）

在**终端5**读取：
```
Translation: [rx, ry, rz]
Rotation in Quaternion (xyzw): [rqx, rqy, rqz, rqw]
```

- 记录 `Translation` → **robot_point**
- 记录 `Rotation` → **robot_quat**

### 2.4 追加到 JSON

将每组数据追加到 `calibration_data_handeye.json`，最终格式：

```json
{
  "camera_points": [[cx1,cy1,cz1], [cx2,cy2,cz2]],
  "camera_quats":  [[cqx1,cqy1,cqz1,cqw1], [cqx2,cqy2,cqz2,cqw2]],
  "robot_points":  [[rx1,ry1,rz1], [rx2,ry2,rz2]],
  "robot_quats":   [[rqx1,rqy1,rqz1,rqw1], [rqx2,rqy2,rqz2,rqw2]]
}
```

### 姿态分布要求

```
上方（手举高） × ≥5 组
中间（正常高度）× ≥5 组
下方（手放低） × ≥5 组
+ 不同横向偏转 × ≥5 组
```

> ⚠️ **关键**：必须覆盖上/中/下三个高度，否则 pitch 角分量无法约束。

---

## 步骤三：计算变换矩阵

```bash
python3 /workspaces/unitree_dex3/elevator_vision/scripts/calibration/compute_handeye.py
```

输出矩阵后**检查第一行第四列**（相机 X 位置）：

```
[[ ...   ...   ...   0.057 ]   ← 此值必须 > 0.04，否则姿态分布有问题
 [ ...   ...   ...   0.017 ]
 [ ...   ...   ...   0.430 ]
 [  0.    0.    0.    1.   ]]
```

若 T[0,3] < 0.04，检查：板子是否移位 / 是否只用了 `accepted=4/4` 的组 / 姿态是否覆盖上中下。

---

## 步骤四：提取并更新外参参数

运行以下脚本提取所有需要更新的参数：

```bash
python3 - << 'EOF'
import numpy as np
from scipy.spatial.transform import Rotation as R

T = np.load('/workspaces/unitree_dex3/elevator_vision/transforms/camera_to_robot.npy')
t = T[:3, 3]
q = R.from_matrix(T[:3, :3]).as_quat()  # [qx, qy, qz, qw]

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

### 4.1 备份并更新 elevator_button_press.launch.py

文件：`unitree_dex3/src/unitree_g1_dex3_stack-main/launch/elevator_button_press.launch.py`

找到 `camera_to_robot_tf` 节点，注释旧参数后填入新值：

```python
arguments=[
    # 旧参数备份 YYYY-MM-DD: '旧值...',
    '新tx', '新ty', '新tz',
    '新qx', '新qy', '新qz', '新qw',
    'torso_link', 'camera_color_optical_frame',
],
```

### 4.2 备份并更新 URDF d435_joint

文件：`unitree_dex3/src/unitree_g1_dex3_stack-main/robots/g1_description/g1_29dof_with_hand_rev_1_0.urdf`

找到 `d435_joint`，注释旧参数后替换 `<origin>` 行：

```xml
<!-- 旧标定 YYYY-MM-DD: <origin xyz="..." rpy="..."/> -->
<origin xyz="新x 新y 新z"
        rpy="新roll 新pitch 新yaw"/>
```

### 4.3 重新编译（容器内）

```bash
cd /workspaces/unitree_dex3
colcon build --packages-select unitree_g1_dex3_stack
```

---

## 步骤五：验证标定结果

重新启动完整方案，观察检测日志：

```
[button_detector_node]: floor='5' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.136)
[button_detector_node]: floor='3' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.086)
[button_detector_node]: floor='1' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.036)
```

验证标准：
- 同列按键（如 1、3、5）的 `y` 值接近（横向对齐）
- `z` 值按行递减，差值约等于实际按键间距
- `dry_run` 模式下手臂目标点与按键视觉位置吻合

---

## 注意事项

| 注意点 | 说明 |
|---|---|
| **板子固定** | 整个采集过程不能移位，采集前后各检查一次 |
| **姿态多样性** | 必须覆盖上/中/下三个高度，否则 pitch 约束不足 |
| **只用 accepted=4/4** | 检测不完整的组直接丢弃，重新摆姿态 |
| **lock 后再采集** | 手臂静止 1~2 秒后再按 g |
| **验证 T[0,3] > 0.04** | 低于此值说明姿态分布有问题，重新采集 |
| **重部署** | 更新 launch 文件后需同步到 install_container（见 README-elevator-vision.md）|

---

## 当前外参参考值（标定前）

```
torso_link → camera_color_optical_frame
平移：0.030168, 0.053707, 0.496973
四元数(x,y,z,w)：-0.656780, 0.663322, -0.255468, 0.251755
```
> 上一版备份（2024）：平移 0.057624, 0.017529, 0.429869  四元数 -0.659252, 0.659252, -0.255707, 0.255707

> 标定后将新值更新于此，供下次重标定时参考。若标定后新值与上述值差异超过 **5 cm / 5°**，建议检查采集过程是否有误。
