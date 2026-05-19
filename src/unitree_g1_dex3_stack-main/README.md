# unitree_g1_dex3_stack

Unitree G1 右臂安全到达 ROS 2 全栈：AprilTag 检测 → G 键触发 → OMPL 规划 → 右臂执行。

## 环境准备

```bash
# ROS 2 Humble (已安装)
# ROS 依赖
sudo apt install ros-humble-realsense2-camera ros-humble-vision-msgs

# 编译（启用 C++ 规划器）
cd ~/Desktop/unitree_dex3
colcon build --cmake-args -DBUILD_IK_FCL_OMPL_PLANNER=ON
source install/setup.bash
```

## 快速启动

```bash
ros2 launch unitree_g1_dex3_stack reach.launch.py
```

启动后在终端中**按 G 键**触发一次规划执行：bridge 取最新 AprilTag 目标位姿发给 planner，规划并执行右臂运动。

## 参数覆盖

```bash
ros2 launch unitree_g1_dex3_stack reach.launch.py \
  planning_timeout:=2.0
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `planning_timeout` | `1.0` | OMPL 规划超时（秒） |
| `adaptive_orientation_enabled` | `true` | 自适应末端位姿 |
| `imshow` | `true` | 是否显示 AprilTag 检测画面 |

## 架构

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。


## Phase 7: AprilTag 检测节点

AprilTag 检测节点依赖 `pupil-apriltags`（pip 包，不在 rosdep 中）。每台部署机器只需安装一次：

```bash
pip install pupil-apriltags
```

独立启动（单条命令即可，无需先启动其他 launch）：

```bash
ros2 launch unitree_g1_dex3_stack apriltag.launch.py
ros2 launch unitree_g1_dex3_stack apriltag.launch.py imshow:=false   # 无显示器 / SSH 部署
```

节点发布两个话题：

- `/apriltag/tag_pose` — `geometry_msgs/PoseStamped`，tag 中心原始位姿（坐标系：`torso_link`）
- `/apriltag/target_pose` — `geometry_msgs/PoseStamped`，tag 位姿在 tag 局部系上叠加 XYZ 偏移后的目标位姿（坐标系：`torso_link`）

检测参数集中在 `config/apriltag.yaml`（`tag_size`、`target_tag_id`、`offset_xyz`、`decision_margin_min` 等）。

## Phase 9: 三条启动入口

Phase 9 (AprilTag 端到端) 后，共有三条 launch 入口，用途不同：

| Launch | 用途 |
|--------|------|
| `apriltag_reach.launch.py` | **端到端流水线**：AprilTag 检测 → bridge 缓存 → G 键触发 → planner (自适应位姿) → executor。最常用入口。 |
| `reach.launch.py` | **Planner 手动测试**：仅启动 robot + planner + executor，不启动检测。通过 `ros2 topic pub /goal_pose` 手动发布目标位姿。 |
| `apriltag.launch.py` | **检测独立调试**：仅启动 robot + RealSense + AprilTag 检测节点 (含 OpenCV 可视化)，不启动 planner/executor。用于调试 tag 识别、摆位、decision_margin 参数。 |

### 使用方法

1. **端到端**：`ros2 launch unitree_g1_dex3_stack apriltag_reach.launch.py`
   - 启动后等待约 3 秒让各节点就绪
   - 将 AprilTag 摆在目标位置，观察 OpenCV 窗口确认检测
   - 在终端按 **G** 键触发（不是 Enter，直接按 G）
   - Bridge 日志显示 `|target-shoulder|` 距离和 `publishing /goal_pose`

2. **Planner 手动测试**：`ros2 launch unitree_g1_dex3_stack reach.launch.py`
   - 然后另开终端：`ros2 topic pub /goal_pose geometry_msgs/PoseStamped "{header: {frame_id: 'torso_link'}, pose: {position: {x: 0.4, y: -0.2, z: 0.0}, orientation: {w: 1.0}}}"`

3. **检测独立调试**：`ros2 launch unitree_g1_dex3_stack apriltag.launch.py imshow:=true`
   - 带可视化窗口调试 tag 识别；按 q 关闭窗口或退出

### 端到端 UAT

```bash
ros2 run unitree_g1_dex3_stack apriltag_reach_uat.py
```

UAT harness 逐一测试 4 个 tabletop 目标点，通过 KDL FK 测量 TCP 实际位置与目标位置的误差，输出每个点的 PASS/FAIL 及总 PASS_COUNT。要求 4/4 全部通过（误差 ≤ 3 cm）。

操作步骤：
1. 启动 `apriltag_reach.launch.py`
2. 另开终端运行 `apriltag_reach_uat.py`
3. UAT 提示 "Place tag at point N" → 摆放 AprilTag 到指定位置 → 按 G → 等待测量
4. 重复 4 次，确认全部 PASS

### 前提条件

- **pupil-apriltags**（Phase 7）：`pip install pupil-apriltags`
- **Realsense SDK**：`sudo apt install ros-humble-realsense2-camera`
- **colcon build**：`colcon build --cmake-args -DBUILD_IK_FCL_OMPL_PLANNER=ON`
- **conda environment**：启动前 `conda activate grab`（Perception 节点在 conda 环境下运行）
