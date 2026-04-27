# Research Summary: Safe Right-Arm Reaching

## Stack
Keep existing OMPL + FCL + TRAC-IK stack. No library changes needed. Add OMPL path simplification (already available in API) and trajectory time parameterization (new code). Use collision primitives URDF for faster FCL checks.

## Table Stakes
1. **Self-collision avoidance** — Fix existing `isInCollision()` logic bug (checks wrong link pairs)
2. **Joint limit enforcement** — Already implemented in planner bounds; add velocity limits in executor
3. **Environment collision** — Add static table as FCL box primitive
4. **Right-arm-only control** — Force planner to right arm; modify executor to only send right arm commands
5. **Coordinate transform** — Already working, needs integration verification
6. **Trajectory smoothness** — Add velocity-based time parameterization
7. **Safe startup** — Check joint state freshness, validate trajectories before execution

## Watch Out For
1. **Running mode interference** — MUST only write right arm joints in LowCmd, leave rest untouched
2. **Self-collision logic bug** — Current code only checks arm-vs-arm pairs, not arm-vs-body
3. **Fixed time steps** — Current 50ms/waypoint can produce unsafe velocities; needs proper time parameterization
4. **Start state in collision** — May need collision padding for FCL
5. **Use collision primitives URDF** — Faster and more reliable than mesh-based collision

## Key Decisions
- No MoveIt — direct OMPL integration is simpler and already working
- Static table only — no dynamic obstacle tracking for v1
- Right arm forced — no left arm support needed
- Collision primitives URDF recommended over mesh URDF for planning
