# 指尖AprilTag 相机外参标定

将小AprilTag 贴在中指指甲盖，通过多个姿态采集相机坐标和机器人TCP坐标，计算 camera → torso_link 外参。

**两种方案可选，推荐方案A（更简单）。**

---

## 方案A：容器工具（推荐）

**全部在容器内运行。**

进入容器：
```bash
bash /home/unitree/Desktop/unitree_container/run.sh
```

### 启动环境

**终端1**（容器）：机器人节点
```bash
ros2 launch unitree_g1_dex3_stack robot.launch.py \
  tf_topic:=/unitree_g1_dex3/tf tf_static_topic:=/unitree_g1_dex3/tf_static
```

**终端2**（容器）：静态相机TF
```bash
ros2 run tf2_ros static_transform_publisher \
  0.057624 0.017529 0.429869 \
  -0.659252 0.659252 -0.255707 0.255707 \
  torso_link camera_color_optical_frame \
  --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static
```

**终端3**（容器）：重力补偿自由拖动（同一终端切换，不能开两个进程）
```bash
python3 /workspaces/unitree_dex3/right_arm_mode.py \
  --mode interactive --network-interface enP8p1s0
```
输入 `free` 手动摆臂，`lock` 锁定。

**终端4**（容器）：apriltag 检测（将0.030替换为实际tag边长）
```bash
ros2 run unitree_g1_dex3_stack v4l2_apriltag_trigger.py \
  --ros-args \
  -p tag_family:=tag36h11 \
  -p tag_size:=0.030 \
  -p target_tag_id:=0 \
  -p detect_only:=true \
  -p camera_frame:=camera_color_optical_frame \
  -p output_frame:=camera_color_optical_frame \
  -p warmup_frames:=30 \
  -p warmup_min_s:=5.0 \
  -r /tf:=/unitree_g1_dex3/tf \
  -r /tf_static:=/unitree_g1_dex3/tf_static
```

> `warmup_frames:=30 warmup_min_s:=5.0`：D435i 自动曝光稳定需3-5秒，默认12帧/2秒不够，图像会偏暗发绿。

> ⚠️ **不要同时启动 RealSense ROS 节点**（v4l2冲突）

### 预览相机画面（实时，无需检测到 tag）

在**本机终端**执行，直接抓取当前相机画面：

```bash
sshpass -p 123 ssh unitree@192.168.100.30 "ffmpeg -f v4l2 -i /dev/video4 -frames:v 1 /tmp/live.jpg -y 2>/dev/null" \
  && sshpass -p 123 scp unitree@192.168.100.30:/tmp/live.jpg /tmp/ \
  && xdg-open /tmp/live.jpg
```

> 不依赖 tag 检测，随时可用。图像可能偏暗，确认 tag 在画面内即可。

### 每组数据采集流程（重复15-25次）

1. 终端3输入 `free`，手动摆好位置（指甲朝向相机，腕关节不挡tag）
2. 终端3输入 `lock`，等手臂静止
3. **终端4按 `g`**，等日志出现：
   ```
   detect_only accepted=4/4 tag=(cx, cy, cz) @ camera_color_optical_frame
   ```
   记录 `tag=(cx, cy, cz)` → **camera_point**

4. **终端5**（容器）读TCP坐标：
   ```bash
   ros2 run tf2_ros tf2_echo \
     --ros-args -r /tf:=/unitree_g1_dex3/tf -r /tf_static:=/unitree_g1_dex3/tf_static \
     -- torso_link right_tcp_link
   ```
   记录 `Translation: [rx, ry, rz]` → **robot_point**

5. 填入 `calibration_data.md`

### 计算结果

填完20组后整理成JSON，路径：
```
/workspaces/unitree_dex3/elevator_vision/scripts/calibration/calibration_data.json
```
格式：
```json
{"camera_points": [[cx,cy,cz],...], "robot_points": [[rx,ry,rz],...]}
```

运行：
```bash
python3 /workspaces/unitree_dex3/elevator_vision/scripts/calibration/compute_transform.py
```

---

## 方案B：宿主机 Handeye 项目

> **前提**：需要先在宿主机解决 cyclonedds 环境问题。  
> 项目路径：`/home/unitree/Desktop/Handeye_calibration_unitreeG1`

### 激活环境

宿主机执行：
```bash
conda activate hand_eye_calib  # 需提前创建此环境
cd /home/unitree/Desktop/Handeye_calibration_unitreeG1
```

### 流程

**步骤1**：重力补偿自由拖动
```bash
PYTHONPATH=/home/unitree/unitree_sdk2_python \
  python3 right_arm_mode.py --mode interactive
```
输入 `free` 摆臂，`lock` 锁定。

**步骤2**：数据采集（另开终端，lock后再运行）
```bash
PYTHONPATH=/home/unitree/unitree_sdk2_python \
  python3 collect_data.py --tag-size 0.030 --tag-id 0
```
检测到tag后按 `s` 保存，重复15-25次，`q` 退出。

**步骤3**：计算标定结果
```bash
PYTHONPATH=/home/unitree/unitree_sdk2_python \
  python3 compute_to_hand.py
```

---

## 更新外参

计算完成后将新TF参数更新到 `elevator_button_press.launch.py`。  
详见 `README-camera-calibration.md` 步骤四。

---

## 注意事项

| 项目 | 要求 |
|------|------|
| tag尺寸参数 | 必须与实际打印尺寸一致 |
| 只用一个终端切换free/lock | 两个进程争夺电机控制权会颤抖 |
| 点分布 | 上/中/下各至少5组 |
| RealSense不能同时运行（方案A）| v4l2与ROS节点冲突 |
| lock后再按g/s | 手臂静止1-2秒后再采集 |
