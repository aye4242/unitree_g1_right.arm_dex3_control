# Stack Research: Safe Right-Arm Reaching for Unitree G1

## Current Stack (Already In Place)

| Component | Library | Version/Status | Notes |
|-----------|---------|----------------|-------|
| Motion Planning | OMPL (RRTConnect) | Compiled, working | Sampling-based planner |
| Collision Checking | FCL | Vendored, compiled | Supports box, cylinder, sphere, mesh geometries |
| Inverse Kinematics | TRAC-IK | Vendored, compiled | Distance solve mode, 1.0s timeout |
| Forward Kinematics | KDL | Via kdl_parser | Chain from URDF |
| Perception | Ultralytics YOLO + PCL | Working | 2D→3D projection via depth images |
| TF | tf2_ros | Working | Camera-to-robot transform calibrated |
| Robot Interface | unitree_hg | Working | LowCmd/LowState messages |

## Recommendations

### Keep As-Is
- **OMPL + FCL + TRAC-IK**: This is the standard stack for ROS 2 arm planning without MoveIt. The existing implementation already handles the core pipeline. No need to switch.
- **RRTConnect planner**: Good default for 7-DOF arm planning. Fast and bidirectional.

### Add/Improve
- **OMPL path simplification**: Current code calls `path.interpolate()` but does NOT call `path.simplify()` or use `PathSimplifier`. Adding simplification removes unnecessary waypoints and shortens paths.
- **Trajectory smoothing**: Current output is raw OMPL waypoints with fixed time steps. No velocity/acceleration profiling. Should add time parameterization for smooth execution.
- **Collision checking resolution**: `setStateValidityCheckingResolution()` is commented out. Should be enabled (0.01-0.05) to catch collisions between waypoints.
- **Environment collision objects**: Current `buildCollisionObjects()` only loads URDF collision geometries (self-collision). No mechanism to add table or other environment obstacles.

### Do NOT Use
- **MoveIt 2**: Overkill for this use case. The existing direct OMPL+FCL integration is simpler and already working. MoveIt would require significant setup (SRDF, move_group, etc.) with no clear benefit.
- **VAMP**: Requires specific setup and is not yet mainstream for ROS 2 Foxy-era stacks.

## Confidence

- **High**: Keep OMPL+FCL+TRAC-IK stack — proven and already compiled
- **High**: Add path simplification — standard OMPL feature, minimal code change
- **Medium**: Trajectory smoothing approach — several options (cubic spline, trapezoidal velocity profile, TOPP-RA), needs evaluation
- **High**: Add environment obstacles — straightforward FCL addition
