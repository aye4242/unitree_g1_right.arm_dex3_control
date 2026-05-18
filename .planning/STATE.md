---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: AprilTag 定位 + TCP 修正
status: executing
last_updated: "2026-05-18T03:52:18.714Z"
last_activity: 2026-05-18 -- Phase 07 planning complete
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 6
  completed_plans: 3
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-15)

**Core value:** The right arm TCP moves safely to the target position without colliding with the robot's own body or the environment, and without exceeding joint limits.
**Current focus:** Phase 7 — AprilTag 检测节点 (plans ready, awaiting execute)

## Current Position

Phase: 7
Plan: Not started
Status: Ready to execute (3 plans across 3 waves)
Last activity: 2026-05-18 -- Phase 07 planning complete

## Current Milestone

**v1.1 — AprilTag 定位 + TCP 修正**

| Phase | Name | Status | Requirements |
|-------|------|--------|--------------|
| 6 | YOLO 清理 + TCP Offset 集成 | ✓ Complete (2026-05-18) | CLEAN-01 ✓, TCP-01 ✓, TCP-02 ✓ |
| 7 | AprilTag 检测节点 | ⏳ Plans ready (3 plans, 3 waves) | TAG-01~04 |
| 8 | 自适应末端位姿 | ○ Pending | ORI-01 |
| 9 | 端到端集成 | ○ Pending | INTG-01~02 |

Progress: ████░░░░░░ 25% (1/4 phases) — Phase 7 plans drafted

## Active Context

- v1.0 milestone complete — full right-arm reaching pipeline working
- Phase 6 complete: YOLO 已彻底移除；TCP offset 通过 URDF `right_tcp_link` 集成到 planner IK 链
- Phase 7 context gathered: 双 topic（`/apriltag/tag_pose` + `/apriltag/target_pose`，frame_id=`torso_link`）、tag_size=0.08m、target_tag_id=0、tag 局部系 offset、Python rclpy + pupil-apriltags、OpenCV imshow 可视化（绿/红框 + 三轴 + HUD）
- Phase 7 plans drafted: 07-01 (build config + YAML, Wave 1) → 07-02 (detector node, Wave 2) → 07-03 (launch + README, Wave 3); RESEARCH.md + PATTERNS.md + 3 PLAN.md committed
- D435i 全局分辨率确定为 640×480 @ 15fps，align_depth 关闭
- Phase 9 才整合到端到端 launch 并桥接到 `/goal_pose`

## Decisions Log

| Decision | Phase | Rationale |
|----------|-------|-----------|
| 移除 YOLO，改用 AprilTag 36h11 | Init | YOLO 检测经测试不可行；AprilTag 轻量可靠 |
| TCP offset 集成到 planner | Init | 当前 IK 目标不含 TCP offset |
| 自适应末端位姿 | Init | 固定位姿导致 IK/OMPL 失败率高 |

---
Last activity: 2026-05-18
