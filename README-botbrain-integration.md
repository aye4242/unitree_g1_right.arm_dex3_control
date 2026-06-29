# unitree_g1_dex3_stack — BotBrain 集成文档

原项目（`unitree-dex3:humble` + `run.sh`）已并入 BotBrain 框架，由 `docker-compose.yaml` 统一编排管理。

- **机器人主机**：`192.168.100.30`
- **BotBrain 项目路径**：`/home/unitree/botbrain_ws/botbrain_project-main/`
- **代码位置**：`botbrain_ws/src/g1_right_dex3/`

---

## 1. 代码文件结构

```
botbrain_ws/src/
├── fcl/                          # FCL 碰撞库（从原项目修复完整版）
├── g1_right_dex3/
│   ├── unitree_g1_dex3_stack/    # 主包：ROS2 C++ 规划器 + Python 节点
│   ├── trac_ik/                  # TRAC-IK 求解器（含 trac_ik_lib 等子包）
│   ├── unitree_dex3_cpp/         # Dex-3 灵巧手 Python 绑定（pybind11）
│   ├── elevator_vision/          # 电梯视觉检测脚本
│   ├── yolonas_ocr/              # YOLO-NAS OCR 推理模型
│   ├── data/                     # 标定数据
│   └── right_arm_mode.py         # 右臂卸力/锁定工具
└── ...（其他 BotBrain 包）
```

---

## 2. Docker 服务说明

`docker-compose.yaml` 新增两个服务，均使用 `unitree-dex3:humble` 镜像：

| 服务名 | 用途 |
|--------|------|
| `builder_dex3` | 编译 C++ 包 + 构建 Python 绑定（手动执行一次） |
| `dex3_stack` | 运行时服务，随 BotBrain 自动启动 |

---

## 3. 编译

### 启动开发容器

```bash
cd /home/unitree/botbrain_ws/botbrain_project-main
docker compose up -d dev_dex3
```

```bash
docker exec -it g1_robot_dev_dex3 bash
```

### 容器内 source 环境

```bash
source /opt/ros/humble/setup.bash
source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
```

### 全量编译（首次或需要重新编译所有包）

```bash
cd /botbrain_ws
colcon build --packages-select fcl trac_ik_lib unitree_g1_dex3_stack \
  --cmake-args -DBUILD_IK_FCL_OMPL_PLANNER=ON -DPython3_EXECUTABLE=/usr/bin/python3
pip3 install --no-build-isolation --no-deps -e src/g1_right_dex3/unitree_dex3_cpp
```

### 增量编译（只改了 `unitree_g1_dex3_stack` 代码后）

```bash
cd /botbrain_ws
colcon build --packages-select unitree_g1_dex3_stack \
  --cmake-args -DBUILD_IK_FCL_OMPL_PLANNER=ON -DPython3_EXECUTABLE=/usr/bin/python3
```

### 编译后重启运行时服务

```bash
# 宿主机执行
docker compose restart dex3_stack
```

编译成功标志：
```
Summary: 3 packages finished
Successfully installed unitree_cpp-1.0.3
```

> ⚠️ stderr 中出现 `warning` 是正常的，只要没有 `failed` 就成功。

---

## 4. 启动 / 停止服务

```bash
cd /home/unitree/botbrain_ws/botbrain_project-main

# 启动
docker compose up -d dex3_stack

# 查看状态
docker compose ps dex3_stack

# 查看日志
docker compose logs -f dex3_stack

# 停止
docker compose stop dex3_stack

# 重启（更新代码后）
docker compose restart dex3_stack
```

> `restart: always` 已配置，机器重启后自动恢复。

---

## 5. 进入容器

启动持久开发容器（常驻后台，可反复进入）：

```bash
# 宿主机
cd /home/unitree/botbrain_ws/botbrain_project-main
docker compose up -d dev_dex3
```

```bash
# 进入容器
docker exec -it g1_robot_dev_dex3 bash
```

```bash
# 容器内 source 环境（每次进入后执行）
source /opt/ros/humble/setup.bash
source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
source /botbrain_ws/install/setup.bash
```

> `dev_dex3` 与 `dex3_stack` 使用同一镜像和 volume，区别是 `dev_dex3` 常驻供开发调试，`dex3_stack` 跑实际节点。

---

## 6. Launch 入口

| Launch 文件 | 用途 |
|---|---|
| `apriltag_button_press.launch.py` | **全流程**：AprilTag 检测 → OMPL 规划 → 手臂执行 → 灵巧手按压 |
| `elevator_button_press.launch.py` | **电梯视觉**：yolonas_ocr 检测楼层按钮 → 手臂按压 |
| `apriltag_reach.launch.py` | 端到端到达（不含灵巧手） |
| `apriltag.launch.py` | 仅相机 + AprilTag 调试 |
| `reach.launch.py` | 仅 planner 手动测试 |

---

## 7. 常用命令

> 以下命令均在**容器内**执行，先进入容器：
> ```bash
> docker exec -it g1_robot_dex3_stack bash
> ```

### 验证节点是否正常运行

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
ros2 node list
```

预期节点（至少包含）：
```
/ik_fcl_ompl_planner
/joint_state_publisher
/joint_trajectory_executor
/robot_state_publisher
/v4l2_apriltag_trigger
```

### 只启动相机识别（安全测试，不动手臂）

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py camera_only:=true
```

### AprilTag 按钮按压（dry-run，不控制灵巧手）

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py dry_run:=true
```

启动后按 **G 键** 触发按压序列。

### AprilTag 按钮按压（真机执行）

> 使用 **V4L2 直接访问相机**，不需要启动 RealSense ROS 驱动。
> 每个按钮位置对应不同的 `v4l2_config_file`（yaml 里的 `offset_xyz` 不同）。

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash

# 按压（指定 yaml 偏移量文件）
ros2 launch unitree_g1_dex3_stack apriltag_button_press.launch.py \
  dry_run:=false \
  v4l2_config_file:=/botbrain_ws/src/g1_right_dex3/unitree_g1_dex3_stack/config/apriltag_button_press.yaml
```

各按钮位置对应的 yaml：

| 位置 | yaml 文件 |
|------|-----------|
| 按下（press） | `config/apriltag_button_press.yaml` |
| 向上（up） | `config/apriltag_button_up.yaml` |
| 向下（down） | `config/apriltag_button_down.yaml` |
| 打开（open） | `config/apriltag_button_open.yaml` |
| 关闭（close） | `config/apriltag_button_close.yaml` |
| 数字1-6 | `config/apriltag_button_number1.yaml` 等 |

启动后按 **G 键** 触发按压序列。

### 电梯视觉按压

> 使用 **RealSense ROS 驱动**获取 RGB + 深度图像，需先在独立终端启动相机。

**终端 1：启动 RealSense 深度相机**

```bash
docker exec -it g1_robot_dev_dex3 bash
```

```bash
# 容器内
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py \
  enable_depth:=true \
  align_depth.enable:=true \
  rgb_camera.color_profile:=640x480x30 \
  depth_module.depth_profile:=640x480x30
```

**终端 2：启动电梯视觉按压**

```bash
docker exec -it g1_robot_dev_dex3 bash
```

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
ros2 launch unitree_g1_dex3_stack elevator_button_press.launch.py \
  target_floor:=5 det_threshold:=0.3
```

> ⚠️ `button_detector_node` 需约 **12 秒**加载 TensorFlow 模型，出现以下日志后再按 G：
> ```
> [button_detector_node] button_detector_node ready  backend=ros ...
> ```
> 系统最长等待 **60 秒**获取检测结果，出现 Ready 后可直接按 G。

### 手臂回站立姿态（紧急恢复）

```bash
# 容器内
source /opt/ros/humble/setup.bash
ros2 topic pub /executor/return_to_standing std_msgs/msg/Empty '{}' --once
```

### 手动触发相机拍照

```bash
# 容器内
source /opt/ros/humble/setup.bash
ros2 topic pub /apriltag/capture_trigger std_msgs/msg/Empty '{}' --once
```

### 手动发布目标位姿

```bash
# 容器内
source /opt/ros/humble/setup.bash
ros2 topic pub /goal_pose geometry_msgs/msg/PoseStamped \
  '{header: {frame_id: "torso_link"}, pose: {position: {x: 0.4, y: -0.2, z: 0.18}, orientation: {w: 1.0}}}' --once
```

### 灵巧手控制

```bash
# 容器内
# 伸出中指
python3 /botbrain_ws/src/g1_right_dex3/unitree_dex3_cpp/example/control_dex3_right_setpoint.py \
  enP8p1s0 0 -1.05 -1.7 1.7 1.8 0 0

# 合拢
python3 /botbrain_ws/src/g1_right_dex3/unitree_dex3_cpp/example/control_dex3_right_setpoint.py \
  enP8p1s0 0 -1.05 -1.7 1.7 1.8 1.7 1.8
```

### 右臂卸力 / 锁定模式

```bash
# 容器内
source /opt/ros/humble/setup.bash
source /botbrain_ws/install/setup.bash
python3 /botbrain_ws/src/g1_right_dex3/right_arm_mode.py
```

| 命令 | 功能 |
|------|------|
| `free` | 卸力，可自由拖动右臂 |
| `lock` | 锁定，保持当前姿态 |
| `status` | 查看当前 7 个关节角度 |

---

## 8. 路径对照（原项目 → BotBrain）

| 原路径（`/workspaces/`） | 新路径（`/botbrain_ws/`） |
|---|---|
| `/workspaces/unitree_dex3/detect_img` | `/botbrain_ws/detect_img` |
| `/workspaces/unitree_dex3_cpp/example/control_dex3_right_setpoint.py` | `/botbrain_ws/src/g1_right_dex3/unitree_dex3_cpp/example/control_dex3_right_setpoint.py` |
| `/workspaces/yolonas_ocr/frozen_model` | `/botbrain_ws/src/g1_right_dex3/yolonas_ocr/frozen_model` |
| `/workspaces/unitree_dex3/elevator_vision/scripts/button_detector_node.py` | `/botbrain_ws/src/g1_right_dex3/elevator_vision/scripts/button_detector_node.py` |
| `install_container/setup.bash` | `/botbrain_ws/install/setup.bash` |

---

## 9. 注意事项

### 旧容器冲突

原来的 `unitree-dex3-dev` 容器（通过 `run.sh` 启动）**不能与 `dex3_stack` 同时运行**，会产生 DDS 话题冲突：

```bash
docker stop unitree-dex3-dev
```

### 话题冲突风险

| 话题 / 资源 | 状态 |
|------|------|
| `/tf` / `/tf_static` | ✅ 已用 `/unitree_g1_dex3/tf` 命名空间隔离 |
| `/lf/lowstate` | ✅ 只读订阅，无冲突 |
| `/joint_states` | ⚠️ 与 BotBrain 可能重复发布，需监控 |
| `/arm_sdk` | ⚠️ `g1_manipulation_pkg` 与 `dex3_stack` 不能同时控制右臂 |
| `/dev/video4`（V4L2）| ⚠️ 独占设备，BotBrain 相机节点需先停止 |

---

## 10. 问题排查

### 节点没起来

```bash
# 宿主机
docker compose logs dex3_stack | tail -50
```

### 手臂没有正常回到站立 / Dex-3 超时

> ⚠️ 不要直接关掉报错终端，否则下次启动手臂会瞬间冲击回原点。

```bash
# 容器内
source /opt/ros/humble/setup.bash
ros2 topic pub /executor/return_to_standing std_msgs/msg/Empty '{}' --once
```

### V4L2 设备被占用

```bash
# 宿主机
fuser -v /dev/video4
kill <PID>
```

### TRAC-IK 无解循环

planner 日志出现反复 `No solution found`，目标超出可达范围，检查 `reach_max_distance` 参数或手动发布可达目标位姿。
