# Architecture Research: Safe Right-Arm Reaching

## Current Architecture Assessment

The existing system follows a clean perception → planning → control pipeline via ROS 2 topics. The core architecture is sound. Changes are modifications to existing nodes, not architectural redesign.

## Component Changes Needed

### 1. Planner Node (`ik_fcl_ompl_planner`)
**Current**: Supports both arms, selects by goal position y-coordinate.
**Target**: Always plans for right arm only.

Changes:
- Remove left arm chain, IK solver, FK solver (or just ignore them)
- Force `use_right = true` always
- Fix self-collision checking logic: check right arm links against ALL other body links
- Add environment collision objects (table) to FCL
- Add OMPL path simplification after planning
- Enable state validity checking resolution

### 2. Trajectory Executor (`joint_trajectory_executor`)
**Current**: Sends `LowCmd` with commands for ALL joints, controls both hands.
**Target**: Only sends commands for right arm joints (7 DOF), leaves everything else to running mode.

Changes:
- Only write right arm joint positions into `LowCmd`
- Do NOT send hand open/close commands
- Add trajectory smoothing (time parameterization with velocity limits)
- Add pre-execution validation (check trajectory is within limits)

### 3. No Changes Needed
- `ultralytics_detector.py` — works as-is
- `project_to_3d_node` — works as-is
- `detection_to_goal_node` — works as-is (publishes goal_pose)
- `joint_state_publisher` — works as-is
- `robot.launch.py` — works as-is

## Data Flow (Target)

```
Camera (RealSense D435)
    ↓ RGB + Depth images
ultralytics_detector (YOLO)
    ↓ 2D bounding boxes
project_to_3d_node
    ↓ 3D detections (Detection3DArray) in camera frame
detection_to_goal_node
    ↓ PoseStamped (selected target) in camera frame
ik_fcl_ompl_planner
    │ 1. TF transform: camera → torso_link
    │ 2. TRAC-IK: target pose → joint angles
    │ 3. OMPL: plan collision-free path
    │ 4. Simplify path
    ↓ JointTrajectory (right arm only, smoothed)
joint_trajectory_executor
    │ 1. Validate trajectory
    │ 2. Time-parameterize with velocity limits
    │ 3. Send ONLY right arm joint commands
    ↓ LowCmd (right arm joints only) → /arm_sdk
```

## Build Order

1. **Planner modifications** — right-arm-only, improved collision, path simplification
2. **Executor modifications** — right-arm-only, trajectory smoothing, validation
3. **Integration testing** — end-to-end pipeline verification
4. **Safety hardening** — error handling, graceful degradation

## Key Constraint: Coexistence with Running Mode

The official Unitree running mode controls balance via the same `/arm_sdk` topic. The trajectory executor must:
- Only populate motor commands for right arm joint indices
- Leave other joint commands at zero or untouched
- Not interfere with the running mode's leg/waist control
