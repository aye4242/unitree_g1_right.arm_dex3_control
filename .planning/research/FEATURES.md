# Features Research: Safe Right-Arm Reaching

## Table Stakes (Must Have)

### Self-Collision Avoidance
- Right arm links must not collide with torso, legs, left arm
- FCL collision checking at every OMPL state evaluation
- Current code already checks self-collision but has a logic issue: `isInCollision()` skips pairs where BOTH links are outside planning_links — should check pairs where at least ONE is a planning link and the OTHER is any body part
- **Complexity**: Medium — existing code needs refinement, not rewrite

### Joint Limit Enforcement
- URDF joint limits already parsed and applied as OMPL bounds
- Trajectory executor already clamps commands to URDF limits
- Need to also enforce velocity limits during execution
- **Complexity**: Low — mostly already implemented

### Coordinate Transform Pipeline
- Camera frame → robot base frame transform via TF2
- Already implemented in `goalPoseCallback()` with `tf_buffer_.transform()`
- Need to verify the full chain: YOLO detection → 3D projection → TF transform → planner goal
- **Complexity**: Low — integration testing

### Right-Arm-Only Control
- Planner already selects right arm based on `pose.position.y < 0.0` — should be forced to always use right arm
- Trajectory executor sends commands for ALL joints — needs to only send right arm joint commands
- Other joints must remain under official running mode control
- **Complexity**: Medium — executor needs careful modification

## Table Stakes (Safety)

### Environment Collision Avoidance
- Add table/surface as collision object in FCL
- Could be static (known table height) or dynamic (from point cloud)
- Static is simpler and sufficient for initial version
- **Complexity**: Medium — new feature but straightforward FCL API

### Trajectory Smoothness
- Current output: raw OMPL waypoints at fixed time intervals
- No velocity or acceleration limits applied
- Need time parameterization: compute proper velocities and time stamps
- Options: cubic spline interpolation, trapezoidal velocity profile
- **Complexity**: Medium — new code needed

### Safe Startup
- Nodes wait for dependencies (robot_state_publisher, joint_states)
- Planner should not accept goals until it has a valid joint state
- Executor should validate trajectory before sending commands
- **Complexity**: Low — defensive checks

## Differentiators (Nice to Have, Defer)

### Path Simplification
- OMPL `PathSimplifier` to shorten paths after planning
- Reduces unnecessary waypoints
- **Complexity**: Low — one API call

### Velocity Scaling
- Runtime parameter to slow down execution speed
- Useful for initial testing (run at 50% speed)
- **Complexity**: Low

### Planning Timeout Adaptation
- Retry with longer timeout if first attempt fails
- **Complexity**: Low

## Anti-Features (Do NOT Build)

- **Dual-arm planning**: Out of scope, only right arm
- **Grasping logic**: No hand control needed
- **Dynamic obstacle tracking**: Static environment sufficient for v1
- **Path recording/playback**: Not needed for reaching task
