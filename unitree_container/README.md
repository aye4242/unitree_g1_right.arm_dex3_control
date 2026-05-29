# Unitree Dex3 Container

This directory contains a Docker environment for developing, building, and running:

- `/home/unitree/Desktop/unitree_dex3`
- `/home/unitree/Desktop/unitree_dex3_cpp`

All download/install actions are manual: the assistant does not run them automatically. `build.sh` prints a warning and asks for confirmation before `docker build` starts.

## What the image provides

- ROS 2 Humble base environment
- CycloneDDS RMW for ROS 2
- Unitree SDK2 C++ headers/libraries installed under `/usr/local`
- Unitree ROS2 message packages: `unitree_api`, `unitree_go`, `unitree_hg`
- RealSense ROS wrapper package from apt
- OpenCV, cv_bridge, TF, KDL, URDF, OMPL, geometric_shapes, FCL-related system libraries
- Python packages for AprilTag and Python/C++ binding builds
- Optional Python packages for Pinocchio and Unitree SDK2 Python

## Build the image

Run this yourself when you are ready to download dependencies:

```bash
bash /home/unitree/Desktop/unitree_container/build.sh
```

The default image name is:

```text
unitree-dex3:humble
```

`build.sh` uses Docker build network mode `host` by default to avoid Docker bridge failures on this G1 NX kernel, such as missing iptables `raw` table errors. Override only if needed:

```bash
BUILD_NETWORK=default bash /home/unitree/Desktop/unitree_container/build.sh
```

`build.sh` does not pass shell proxy variables by default. This avoids failures when a stale proxy such as `192.168.100.20:7890` is set but not reachable. If you need a proxy, enable it explicitly:

```bash
USE_PROXY=1 PROXY_URL=http://192.168.100.20:7890 bash /home/unitree/Desktop/unitree_container/build.sh
```

If that proxy returns `Connection refused`, fix or disable the proxy first, then rerun the build.

If `pin` or `unitree_sdk2_python` causes build problems, retry with optional parts disabled:

```bash
INSTALL_PINOCCHIO_PIP=0 bash /home/unitree/Desktop/unitree_container/build.sh
```

```bash
INSTALL_UNITREE_SDK2_PYTHON=0 bash /home/unitree/Desktop/unitree_container/build.sh
```

The Dockerfile installs `cyclonedds==0.10.2` for `unitree_sdk2py` with `CYCLONEDDS_HOME=/usr/local` so the Python wheel build can find the CycloneDDS headers and libraries installed by Unitree SDK2.

## Start the container

```bash
bash /home/unitree/Desktop/unitree_container/run.sh
```

The default runtime assumptions are:

- Unitree network interface: `enP8p1s0`
- Host networking: enabled
- Device access: privileged with `/dev` mounted
- Project mounts:
  - `/workspaces/unitree_dex3`
  - `/workspaces/unitree_dex3_cpp`
- Optional local mounts if present:
  - `/workspaces/xr_teleoperate`
  - `/workspaces/unitree_sdk2_python`
- Shells opened through `run.sh` automatically source `/opt/ros/humble/setup.bash`, `/opt/unitree_ros2/cyclonedds_ws/install/setup.bash`, and `/workspaces/unitree_dex3/install_container/setup.bash` when it exists.
- `PYTHONPATH` includes `/workspaces/unitree_dex3_cpp/build`, so an already-built `unitree_cpp.cpython-310-*.so` remains importable after restarting the `--rm` container.

Override the network interface if needed:

```bash
UNITREE_NET_IF=eth0 bash /home/unitree/Desktop/unitree_container/run.sh
```

Run a one-shot command in the container:

```bash
bash /home/unitree/Desktop/unitree_container/run.sh bash -lc 'ros2 pkg list | grep unitree_hg'
```

After building `/workspaces/unitree_dex3` inside the container, source it manually in the shell that needs it:

```bash
source /workspaces/unitree_dex3/install/setup.bash
```

## Build `unitree_dex3_cpp` inside the container

Inside the container:

```bash
cd /workspaces/unitree_dex3_cpp
python3 -m pip install -e . --no-build-isolation --no-deps
python3 -c 'import unitree_cpp; print("unitree_cpp import OK")'
```

Because `run.sh` uses `docker run --rm`, editable pip install metadata inside the container is not persistent after exit. The compiled extension under `/workspaces/unitree_dex3_cpp/build` is on the mounted host directory and is included in `PYTHONPATH`, so restarting the container can still import `unitree_cpp` as long as that build output exists.

If you disabled `INSTALL_UNITREE_SDK2_PYTHON` but later need `right_arm_mode.py`, install the mounted local SDK2 Python package yourself:

```bash
python3 -m pip install --no-deps -e /workspaces/unitree_sdk2_python
```

## Build `unitree_dex3` inside the container

Inside the container:

```bash
cd /workspaces/unitree_dex3
source /opt/ros/humble/setup.bash
source /opt/unitree_ros2/cyclonedds_ws/install/setup.bash
colcon --log-base log_container build \
  --build-base build_container \
  --install-base install_container \
  --cmake-args -DBUILD_IK_FCL_OMPL_PLANNER=ON
source install_container/setup.bash
ros2 pkg prefix unitree_g1_dex3_stack
```

Use the `*_container` directories to avoid reusing `build/`, `install/`, and `log/` created on the host path `/home/unitree/Desktop/unitree_dex3`. Reusing those directories inside the container can trigger CMakeCache path mismatch errors.

## Run safe verification first

Prefer camera/detection-only tests before any robot motion:

```bash
cd /workspaces/unitree_dex3
source install_container/setup.bash
ros2 launch unitree_g1_dex3_stack apriltag_reach.launch.py camera_backend:=v4l2_trigger detect_only:=true imshow:=false
```

If V4L2 cannot open the D435i RGB device, check for another process using it on the host:

```bash
fuser -v /dev/video4
```

## Robot communication checks

After the robot is connected and powered, check DDS/ROS traffic before running motion:

```bash
ros2 topic echo /lf/lowstate --once
```

For `unitree_dex3_cpp` Dex-3 tactile/debug paths, use the container with host networking and the correct `UNITREE_NET_IF`.

## Notes about Python dependencies

The image pins `numpy<2` to avoid ROS Humble `cv_bridge` ABI issues. Avoid installing pip `opencv-python` unless you intentionally need it, because apt OpenCV is already used by ROS.

`right_arm_mode.py` currently imports modules from the local project and from `xr_teleoperate/teleop`; `run.sh` sets `PYTHONPATH` for those mounted paths. It also imports `utils.pinocchio_compat`, which was not found in the searched local trees; that missing module is separate from the container build issue and must be restored or the import changed before relying on that script.
