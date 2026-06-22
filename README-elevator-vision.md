# 电梯按键视觉按压方案 (yolonas_ocr)

新方案用 **yolonas_ocr** 视觉检测替代旧方案（AprilTag），通过 RealSense D435i 的 RGB+深度图像检测电梯按键坐标，驱动右臂灵巧手按压。

- **部署机器**：`192.168.100.30`

```bash
# 进入容器（会自动 source ROS2 和工作区环境）
bash /home/unitree/Desktop/unitree_container/run.sh

# 先在另一个终端启动 RealSense（也需要进入容器）
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch realsense2_camera rs_launch.py

# 启动完整方案（启动后按 G 触发按压）
ros2 launch unitree_g1_dex3_stack elevator_button_press.launch.py \
  target_floor:=5 det_threshold:=0.3
```

> ⚠️ **WARNING**：如果手臂没有正常回到初始姿态，新开一个终端发布：
> ```bash
> bash /home/unitree/Desktop/unitree_container/run.sh
> ros2 topic pub /executor/return_to_standing std_msgs/msg/Empty '{}' --once
> ```

**运行环境**：所有 ROS 2 节点均在 Docker 容器内运行（`unitree-dex3-dev`），宿主机通过 `run.sh` 启动进入。

---

## 控制链路

```
G键触发
  → apriltag_button_press_node（发布 /apriltag/capture_trigger）
  → button_detector_node（yolonas_ocr 检测 + RealSense 深度 + TF变换）
  → ik_fcl_ompl_planner（OMPL 运动规划）
  → joint_trajectory_executor（关节控制执行）
  → 手指按压按键 ✅
```

---

## Docker 环境

```bash
# 启动容器（交互式 shell，自动 source ROS 和 install）
bash /home/unitree/Desktop/unitree_container/run.sh

# 容器内 shell 已自动 source：
#   /opt/ros/humble/setup.bash
#   /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
#   /workspaces/unitree_dex3/install/setup.bash
```

> **注意**：不要用 `docker exec -it unitree-dex3-dev bash`，那样进入后 `ros2` 命令找不到。始终用 `run.sh` 进入容器。

---

## 启动步骤

### 终端 1：启动 RealSense
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  align_depth.enable:=true \
  rgb_camera.color_profile:=640x480x30 \
  depth_module.depth_profile:=640x480x30
```

> 使用 640×480@30fps 而非默认 1280×720，避免 USB 2.0 带宽不足（83MB/s）导致 RGB 实际只有 ~3fps。  
> 可加 alias 简化：`echo "alias start_rs='ros2 launch realsense2_camera rs_launch.py enable_depth:=true align_depth.enable:=true rgb_camera.color_profile:=640x480x30 depth_module.depth_profile:=640x480x30'" >> ~/.bashrc && source ~/.bashrc`

### 终端 2：启动完整方案
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
ros2 launch unitree_g1_dex3_stack elevator_button_press.launch.py \
  target_floor:=5 det_threshold:=0.3
```

等出现以下提示后按 G：
```
[apriltag_button_press_node] Ready — press G to run pre→extend→press→pre→close→return
```

> ⚠️ **注意：两个节点的启动时序不同**
> - `apriltag_button_press_node`：约 **3 秒**内显示 Ready 提示
> - `button_detector_node`：需约 **12 秒**加载 TensorFlow 模型，之后才打印：
>   ```
>   [button_detector_node] button_detector_node ready  backend=ros ...
>   ```
>
> **出现 Ready 提示后可以直接按 G**，无需等待检测日志，系统最长等待 **60 秒**获取检测结果。  
> - 若检测结果已缓存（30秒内），按G立即响应  
> - 若刚启动/相机刚对准，等待新检测结果（最长60秒）

> ⚠️ **注意**：第二次按 G 需等手臂完全缩回原位，否则手臂遮挡相机导致检测失败。

---

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_floor` | `0` | 目标楼层（0=取置信度最高的按键） |
| `det_threshold` | `0.5` | 检测置信度阈值（建议 `0.3`） |
| `dry_run` | `false` | 干跑模式，不执行实际按压 |
| `press_y_offset` | `0.0` | 按压点 torso_link Y轴偏移（正=向左，负=向右），单位 m |
| `press_z_offset` | `0.0` | 按压点 torso_link Z轴偏移（正=向上，负=向下），单位 m |

---

## 按压精度调试

### 坐标系说明

按压目标点在 `torso_link` 坐标系下：

```
       Z↑
       |
       |___→ Y（向左）
      /
     X（向前，朝向按键面板）
```

| 参数 | 正方向 | 负方向 |
|---|---|---|
| `press_y_offset` | 向左 | 向右 |
| `press_z_offset` | 向上 | 向下 |
| `pre_contact_offset_x` | — | 越大越往后（接近距离）|

> **与旧方案的区别**：旧方案 `offset_xyz` 在 **AprilTag 局部坐标系**内，每个按键都有独立值（tag 贴固定位置，各按键几何距离不同）。新方案 YOLO 直接检测各按键，偏移在 **torso_link 坐标系**内，对所有按键统一生效，只补偿系统性标定误差。

---

### 调试流程

**第一步：确认检测坐标是否合理**

启动后观察日志（无需按 G）：
```
[button_detector_node]: floor='3' conf=0.99 depth=0.471m  torso(0.435,-0.117,0.136)
```
`torso(x, y, z)` 中 x≈0.4~0.6，y≈-0.2~0.1，z≈0.1~0.3 为合理范围。

**第二步：干跑确认手臂轨迹**

```bash
ros2 launch unitree_g1_dex3_stack elevator_button_press.launch.py \
  target_floor:=3 dry_run:=true
```
按 G，手臂运动到按压位置前方但不实际按压，目视检查对准。

**第三步：实际按压，测量偏差方向**

| 现象 | 调整 |
|---|---|
| 手指偏右 | `press_y_offset` 增大（如 `0.02`） |
| 手指偏左 | `press_y_offset` 减小（如 `-0.02`） |
| 手指偏高 | `press_z_offset` 减小（如 `-0.02`） |
| 手指偏低 | `press_z_offset` 增大（如 `0.02`） |
| 没触到面板或戳太深 | 调 `pre_contact_offset_x`（默认 `0.05`）|

**第四步：带偏移参数启动测试**

```bash
ros2 launch unitree_g1_dex3_stack elevator_button_press.launch.py \
  target_floor:=3 press_y_offset:=0.02 press_z_offset:=-0.01
```

每次调整步长建议 **1~2 cm**（0.01~0.02），逐步逼近。

> **判断是否需要重新标定**：若不同按键（3/4/5/6）偏差方向**一致** → 用上述参数可修正；若偏差方向**因按键而异（参差不齐）** → 相机外参旋转误差，需重新标定。

---

### 当前调试进度

| 项目 | 状态 | 说明 |
|---|---|---|
| 深度采样优化 | ✅ 已完成 | 改为全 bbox 区域 25th 百分位，减少发光按键中心 depth 无效的影响 |
| 按压偏移参数 | ✅ 已完成 | 新增 `press_y_offset` / `press_z_offset` |
| 启动时序修复 | ✅ 已完成 | TimerAction 从 3s 改为 20s，避免 TF 初始化前就触发 |
| 旧版二进制更新 | ⏳ 待部署 | 需重新 build + 同步到 `install_container`（见部署章节） |
| 按压精度实测调参 | ⏳ 待测试 | 部署后实测，用 `press_y_offset` / `press_z_offset` 调整 |
| 相机外参重标定 | 🔲 备用方案 | 若不同按键偏差参差不齐，需重新采集标定数据 |

---

## 本地 → 机器人部署

> 容器内有两套安装目录：`install/`（符号链接）和 `install_container/`（真实文件副本，ROS2 实际加载这个）。

### 修改了 `button_detector_node.py`

节点通过绝对路径直接运行，**只需 SCP，无需 colcon**：

```bash
scp unitree_dex3/elevator_vision/scripts/button_detector_node.py \
    unitree@192.168.100.30:~/Desktop/unitree_dex3/elevator_vision/scripts/
```

### 修改了 `elevator_button_press.launch.py`

Launch 文件从 `install_container` 加载，**必须先 SCP，再同步**：

```bash
# 1. 先上传源文件到机器人（必须在 colcon build 之前）
scp unitree_dex3/src/unitree_g1_dex3_stack-main/launch/elevator_button_press.launch.py \
    unitree@192.168.100.30:~/Desktop/unitree_dex3/src/unitree_g1_dex3_stack-main/launch/

# 2. 同步到 install_container（推荐用 cp，比 colcon build 更可靠）
sshpass -p "123" ssh unitree@192.168.100.30 \
  "docker exec unitree-dex3-dev cp \
    /workspaces/unitree_dex3/src/unitree_g1_dex3_stack-main/launch/elevator_button_press.launch.py \
    /workspaces/unitree_dex3/install_container/unitree_g1_dex3_stack/share/unitree_g1_dex3_stack/launch/"
```

> ⚠️ **坑**：不要先跑 colcon build 再 SCP。colcon build 读取的是机器人上 `src/` 里的文件，如果 SCP 还没做，build 的还是旧文件。

---

## 关键文件（容器内路径）

| 文件 | 路径 |
|------|------|
| 检测节点 | `/workspaces/unitree_dex3/elevator_vision/scripts/button_detector_node.py` |
| launch 文件 | `/workspaces/unitree_dex3/install/unitree_g1_dex3_stack/share/unitree_g1_dex3_stack/launch/elevator_button_press.launch.py` |
| 标定矩阵 | `/workspaces/unitree_dex3/elevator_vision/scripts/transforms/camera_to_robot.npy` |
| yolonas 模型 | `/workspaces/yolonas_ocr/frozen_model/` |

---

## 静态 TF（相机 → 机器人）

基于 AprilTag 一次性标定，写死在 launch 文件中：

```
camera_color_optical_frame → torso_link
translation: (0.017530, 0.332415, 0.278584)
rotation (x,y,z,w): (0.659252, -0.659252, 0.255707, 0.255707)
```

---

## 故障排查

### 1. RealSense 找不到设备：`Cannot open '/dev/videoX'`

**症状**：RealSense 节点报 `No such file or directory`，相机无法启动。

**原因**：USB 设备掉线，内核未识别到相机。

**排查与修复**：
```bash
# 1. 检查设备是否存在
ls /dev/video*

# 2. 重新触发设备检测（不需要重插）
sudo udevadm trigger && sleep 2 && ls /dev/video*

# 3. 查看 USB 错误日志
dmesg | grep -i "usb\|video\|disconnect" | tail -20
```

如果 `udevadm trigger` 后设备回来了，重新启动 RealSense 节点即可。  
如果还是没有，**物理重插USB线**后再试。

---

### 2. RGB 只有 ~3fps（USB 带宽不足）

**症状**：
```bash
ros2 topic hz /camera/camera/color/image_raw --window 10
# 显示：average rate: 2.93 Hz  （应为30Hz）
```

**原因**：1280×720 RGB8 未压缩格式带宽约 83MB/s，超过 USB 2.0 上限（~60MB/s），相机被迫降帧。

**修复**：启动 RealSense 时指定 640×480 分辨率：
```bash
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  align_depth.enable:=true \
  rgb_camera.color_profile:=640x480x30 \
  depth_module.depth_profile:=640x480x30
```

**设置默认 alias（推荐）**：
```bash
echo "alias start_rs='ros2 launch realsense2_camera rs_launch.py enable_depth:=true align_depth.enable:=true rgb_camera.color_profile:=640x480x30 depth_module.depth_profile:=640x480x30'" >> ~/.bashrc
source ~/.bashrc
# 之后直接运行
start_rs
```

---

### 3. 警告：`capture trigger received but no image in Xs`

**症状**：按 G 后出现此警告，手臂不动作。

**含义**：`button_detector_node` 在 X 秒内没收到 RGB 图像帧（相机停流）。

**诊断步骤**：
```bash
# 检查 RGB 是否在推流
ros2 topic hz /camera/camera/color/image_raw --window 10

# 检查深度是否在推流
ros2 topic hz /camera/camera/depth/image_rect_raw --window 10

# 确认深度话题存在
ros2 topic echo /camera/camera/depth/image_rect_raw --field header.stamp --once
```

**常见原因**：
| 现象 | 原因 | 修复 |
|------|------|------|
| RGB = 0Hz，Depth = 30Hz | 相机 USB 掉线 | 重插 USB 或 `udevadm trigger` |
| RGB = ~3Hz，Depth = 30Hz | USB 带宽不足 | 改用 640×480×30 |
| RGB = 30Hz 但有 0.3s 尖峰 | USB 接触不良 | 换 USB3.0 口或换线 |

---

### 4. 检测卡住：`waiting for YOLO detection (up to 60s)`

**症状**：按 G 后打印此消息，长时间无法按压。

**原因链**：RealSense 停止推流 → `button_detector_node` 推理线程收不到新帧 → 等待超时。

**排查**：先确认相机话题正常（见上一节），然后检查检测日志：
```
[button_detector_node]: floor='3' conf=0.99 depth=0.47m torso(0.43,-0.12,0.13)
```
- 如果有此日志且**频率正常（每3-5秒一次）**：重新按G，会立即响应（系统使用30秒内缓存）
- 如果日志停止：相机停流，需重启 RealSense

---

### 5. 按压完成后再次按G无响应

**原因**：手臂按压期间 USB 振动可能导致相机短暂停流，30秒内的缓存坐标可复用。

**操作**：
- 按压完成后 **30 秒内**再按 G：直接使用缓存坐标，立即响应
- 超过 30 秒：系统等待新检测（相机若恢复正常则很快响应）

---

### 6. launch 启动后长时间无响应

**正常现象**：启动后约 **12-15 秒**内看起来"卡住"，实际上是 YOLO（TensorFlow）模型在加载，属正常行为。

等到以下日志出现才代表就绪：
```
[button_detector_node]: inference thread started
[button_detector_node]: button_detector_node ready  backend=ros ...
[apriltag_button_press_node]: Ready — press G to run pre→extend→press→...
```
