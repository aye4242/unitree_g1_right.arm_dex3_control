#!/bin/bash

# 激活conda环境
source ~/miniforge3/etc/profile.d/conda.sh
conda activate grab

# Source ROS2环境
cd /home/unitree/Desktop/unitree_dex3
source install/setup.bash

# 运行perception
ros2 launch src/unitree_g1_dex3_stack-main/launch/perception.launch.py
