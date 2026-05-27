# Task 006: Implement UAV Control Bridge

## Task goal

- Add a reusable ROS 2 UAV control bridge node in `px4_offboard_hover`.
- The bridge must subscribe to `/uav/target_position` and publish PX4 offboard setpoints through the existing `OffboardPositionControl` base class.
- Keep Demo 01-04 behavior stable. Do not delete or overwrite existing logs or visualization results.

## Required behavior

- Add a console entry point named `uav_control_bridge`.
- Subscribe:
  - `/uav/target_position`: `geometry_msgs/msg/Point`, local PX4 NED frame.
- Publish to PX4 only through the existing base class:
  - `/fmu/in/offboard_control_mode`
  - `/fmu/in/trajectory_setpoint`
  - `/fmu/in/vehicle_command`
- Parameters and defaults:
  - `initial_x=0.0`
  - `initial_y=0.0`
  - `initial_z=-2.0`
  - `yaw=0.0`
  - `target_timeout=1.0`
  - `max_altitude=5.0`
  - `min_altitude=0.5`
  - `max_horizontal_range=5.0`
  - `target_jump_limit=1.5`
- Safety semantics:
  - Treat all `/uav/target_position` values as local NED.
  - Positive altitude is not accepted on this topic; callers must publish NED `z=-altitude`.
  - Reject non-finite targets.
  - Reject targets where altitude `-z` is above `max_altitude` or below `min_altitude`.
  - Reject targets outside `max_horizontal_range` from local origin.
  - Reject target jumps larger than `target_jump_limit` from the current safe target.
  - On `target_timeout`, keep holding the last safe target and log a warning no more than once per timeout interval.
  - Rejected targets must not update the safe target.

## Allowed changes

- `src/px4_offboard_hover/px4_offboard_hover/*.py`
- `src/px4_offboard_hover/setup.py`
- `src/px4_offboard_hover/package.xml` only if needed for dependencies
- `docs/UAV_CONTROL_API.md` if implementation notes need updating
- `codex-logs/006-implement-uav-control-bridge.log`

Do not modify PX4-Autopilot, `src/px4_msgs`, existing experiment data, or Demo 01-03 scripts.

## Required commands

Save command output to `codex-logs/006-implement-uav-control-bridge.log`:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -m compileall src scripts
colcon build --packages-select px4_offboard_hover
```

If the build fails because ROS dependencies are unavailable, try to fix local package issues first. If still blocked, report the exact failure.

## Deliverables

- A working `uav_control_bridge` ROS 2 entry point.
- Updated API documentation if behavior differs from the prior design doc.
- `codex-logs/006-implement-uav-control-bridge.log`

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

