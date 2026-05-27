# Task 018: Add Tag Target Pose Estimation

## Task goal

- Add a first verifiable target-pose pipeline using AprilTag or ArUco.

## Allowed changes

- `src/aerial_manip_gazebo/**`
- `src/aerial_manip_vision/**`
- `docs/STAGE2_TARGET_POSE.md`
- `codex-logs/018-add-tag-target-pose-estimation.log`

## Implementation requirements

- Place a simple fiducial target in the simulation world.
- Publish `/vision/target_pose` and `/vision/target_pose_in_uav_frame`.
- Prefer an installed ROS 2 tag detector if available; otherwise provide a documented placeholder node and environment warning.

## Required commands

```bash
python3 -m compileall src/aerial_manip_vision
colcon build --packages-select aerial_manip_vision aerial_manip_gazebo
ros2 topic echo /vision/target_pose --once || true
```

## Deliverables

- Target model/world assets.
- Target pose node or detector launch.
- Metrics or warning log.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
