# Task 007: Add UAV State Feedback

## Task goal

- Extend the UAV control bridge with high-level state feedback topics from `docs/UAV_CONTROL_API.md`.
- Keep the interface simple and compatible with standard ROS 2 message types.

## Required behavior

- Subscribe:
  - `/fmu/out/vehicle_local_position_v1`: `px4_msgs/msg/VehicleLocalPosition`
- Publish:
  - `/uav/current_position`: `geometry_msgs/msg/PointStamped`
  - `/uav/current_target`: `geometry_msgs/msg/PointStamped`
  - `/uav/reached_target`: `std_msgs/msg/Bool`
  - `/uav/control_state`: `std_msgs/msg/String`
- Use `header.frame_id="uav_local_ned"` for point stamped topics.
- Publish current position only when PX4 reports both `xy_valid` and `z_valid`.
- Add parameters:
  - `reach_xy_tolerance=0.30`
  - `reach_z_tolerance=0.20`
  - `reach_hold_time=1.0`
- Control state values for this task:
  - `TRACKING` when a safe target is active and being sent to PX4.
  - `REACHED` after the vehicle remains within reach tolerances for `reach_hold_time`.
  - `HOLDING` when input timed out and the bridge is holding the last safe target.
  - `INVALID_TARGET` immediately after rejecting an input target.
- `/uav/current_target` must publish the current safe target, not the raw rejected command.

## Allowed changes

- `src/px4_offboard_hover/px4_offboard_hover/*.py`
- `src/px4_offboard_hover/setup.py`
- `src/px4_offboard_hover/package.xml`
- `docs/UAV_CONTROL_API.md`
- `codex-logs/007-add-uav-state-feedback.log`

Do not modify PX4-Autopilot, `src/px4_msgs`, existing experiment data, or Demo 01-03 scripts.

## Required commands

Save command output to `codex-logs/007-add-uav-state-feedback.log`:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -m compileall src scripts
colcon build --packages-select px4_offboard_hover
```

## Deliverables

- UAV bridge feedback topics.
- Updated docs describing implemented topic status.
- `codex-logs/007-add-uav-state-feedback.log`

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

