# Pitfalls Research: Safe Right-Arm Reaching

## Critical Pitfalls

### 1. Interfering with Running Mode
**Risk**: Writing to non-right-arm joints in `LowCmd` could fight with the official running mode, causing instability or falls.
**Warning signs**: Robot wobbles, loses balance, or jerks when arm moves.
**Prevention**: Only populate `motor_cmd` entries for right arm joint indices (kRightShoulderPitch through kRightWristYaw). Leave all other entries untouched. Test with very slow movements first.
**Phase**: Executor modification

### 2. Self-Collision Logic Bug
**Risk**: Current `isInCollision()` has an incorrect filtering condition. It skips pairs where at least one link is NOT in `planning_links` (uses `||`). This means it only checks pairs where BOTH links are in the planning chain — it never checks right arm vs torso/legs.
**Warning signs**: Planner produces paths that collide with the body.
**Prevention**: Fix the condition to check pairs where at least ONE link is in `planning_links` — right arm vs any other body link.
**Phase**: Planner modification

### 3. Trajectory Time Step Too Small
**Risk**: Current `time_step_ = 0.05` (50ms per waypoint). Combined with many interpolated waypoints, this can produce very fast motions that the robot can't track.
**Warning signs**: Jerky motion, motors lagging behind commanded positions, overshoot.
**Prevention**: Add velocity-based time parameterization instead of fixed time steps. Limit joint velocity to a safe fraction of URDF max velocity.
**Phase**: Executor modification

### 4. IK Solution Near Singularity
**Risk**: TRAC-IK may return solutions near kinematic singularities, leading to large joint velocities during execution.
**Warning signs**: One joint suddenly moves very fast between waypoints.
**Prevention**: Check maximum joint velocity between consecutive waypoints before execution. Reject or re-time if too fast.
**Phase**: Executor modification

### 5. Missing Environment Collisions
**Risk**: Without a table collision object, the planner may produce paths that go through the table surface.
**Warning signs**: Arm collides with table during execution.
**Prevention**: Add static table collision object (box primitive) at known height. Make table dimensions configurable via ROS parameters.
**Phase**: Planner modification

### 6. Start State Already in Collision
**Risk**: If the robot's current configuration is already in self-collision (according to FCL), the planner will reject the start state and fail immediately.
**Warning signs**: Planner always fails with "Start state invalid".
**Prevention**: Add a configurable collision padding/margin. Allow slightly-in-collision start states. Log clearly when this happens.
**Phase**: Planner modification

### 7. URDF Collision Primitives vs Meshes
**Risk**: The default URDF uses meshes for collision. Meshes are slower for FCL and may have issues (normals, water-tightness). The repo includes a `_collision_primitives.urdf` variant.
**Warning signs**: Slow collision checking, false positives/negatives.
**Prevention**: Use the `_collision_primitives.urdf` for planning. Simpler geometries = faster and more reliable FCL checks.
**Phase**: Configuration

## Medium Pitfalls

### 8. TF Timing Issues
**Risk**: TF transform from camera to robot frame may have timing mismatches if frames are published at different rates.
**Prevention**: Use `tf_buffer_.transform()` with adequate timeout (already 0.5s). Log transform age.

### 9. YOLO False Positives
**Risk**: YOLO detects a non-existent object, arm reaches to empty space.
**Prevention**: Not in scope for this milestone (perception reused as-is). Consider confidence threshold tuning if needed.

### 10. Stale Joint State
**Risk**: Planner uses old joint state if `joint_states` topic stops publishing.
**Prevention**: Check joint state age before planning. Reject if older than a threshold (e.g., 500ms).
