# unitree_g1_dex3_stack

Unitree G1 右臂安全抓取 ROS 2 全栈：YOLO 检测 → 3D 投影 → 键盘触发 → OMPL 规划 → 右臂执行。

## 环境准备

```bash
# ROS 2 Humble (已安装)
# 系统 Python 依赖
pip install ultralytics torch

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

启动后在终端中**按 K 键**触发一次抓取：节点自动选取最近目标，规划并执行右臂运动。

## 参数覆盖

```bash
ros2 launch unitree_g1_dex3_stack reach.launch.py \
  target_class:=cup \
  imshow:=false \
  planning_timeout:=2.0 \
  model_path:=/path/to/model.pt
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `target_class` | `bottle` | YOLO 检测目标类别 |
| `imshow` | `true` | 是否显示检测画面 |
| `planning_timeout` | `1.0` | OMPL 规划超时（秒） |
| `model_path` | `best.pt` | YOLO 模型路径 |

## 架构

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。
