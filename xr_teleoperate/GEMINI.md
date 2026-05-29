# XR Teleoperate Project Context

This project implements teleoperation control of Unitree humanoid robots (G1, H1 series) using XR (Extended Reality) devices like Apple Vision Pro, PICO 4 Ultra, and Meta Quest 3.

## Project Overview

- **Core Goal**: Drive robot arms and dexterous hands in real-time using XR hand/controller tracking.
- **Main Technologies**:
  - **Python**: Core implementation language.
  - **unitree_sdk2py**: Official Python library for DDS communication with Unitree hardware.
  - **Pinocchio**: Rigid-body dynamics library used for Inverse Kinematics (IK).
  - **Vuer / TeleVuer**: Web-based XR interface for receiving poses and sending images.
  - **TeleImager**: Image streaming service using WebRTC or ZMQ.
  - **dex-retargeting**: Library for mapping human hand poses to robot dexterous hands.

## Key Directories

- `teleop/`: Main source code directory.
  - `teleop_hand_and_arm.py`: Entry point for teleoperation.
  - `robot_control/`: Core control logic (IK, retargeting, DDS commands).
  - `televuer/`: Submodule for XR device interaction.
  - `teleimager/`: Submodule for camera streaming.
  - `utils/`: Helpers for recording, IPC, and visualization.
- `assets/`: URDF models, meshes, and retargeting configurations for robots and hands.

## Building and Running

### Environment Setup
1. Create a Conda environment:
   ```bash
   conda create -n tv python=3.10 pinocchio=3.1.0 numpy=1.26.4 -c conda-forge
   conda activate tv
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e teleop/teleimager
   pip install -e teleop/televuer
   # Also requires unitree_sdk2_python installed from its own repo
   ```

### Simulation
1. Start the simulation (Isaac Lab recommended).
2. Run teleop script:
   ```bash
   cd teleop
   python teleop_hand_and_arm.py --sim --arm G1_29 --ee dex3
   ```

### Physical Deployment
1. Start `teleimager-server` on the robot's computing unit (PC2).
2. Run teleop script on your host machine:
   ```bash
   cd teleop
   python teleop_hand_and_arm.py --arm G1_29 --ee dex3 --img-server-ip <PC2_IP>
   ```

## Development Conventions

- **DDS Communication**: Uses `unitree_sdk2py`. Domain ID 0 for real robots, ID 1 for simulation.
- **Multiprocessing/Threading**: Heavy use of `threading` and `multiprocessing` for concurrent data capture, control, and streaming.
- **IK Integration**: Inverse Kinematics is handled in `teleop/robot_control/robot_arm_ik.py` using Pinocchio models defined in `assets/`.
- **Hand Mapping**: Retargeting configurations are stored as YAML files in `assets/<hand_type>/<hand_type>.yml`.

## Important Note
Always ensure the robot is in a safe position (initial pose) before starting or stopping teleoperation to avoid sudden movements.
