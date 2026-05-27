# uav-air-reach-ros2

PX4 + ROS2 workspace for UAV offboard control, a lightweight UAV-arm simulation stack, high-level arm/UAV bridges, target-pose perception baselines, LeRobot-style data export, and Demo 10 air-reach regression.

## Repository Layout

- `px4_ros2_ws/`: primary ROS2 workspace with custom packages, scripts, docs, Codex tasks, and deliverables.
- `px4_ros2_ws/src/aerial_manip_*`: stage-2 UAV-arm messages, control, Gazebo, vision, evaluation, and policy packages.
- `px4_ros2_ws/src/px4_offboard_hover`: PX4 offboard demos and UAV high-level control bridge.
- `px4_ws/PX4-Autopilot`: PX4 upstream dependency tracked as a Git submodule.
- `px4_ros2_ws/src/px4_msgs`: PX4 ROS2 messages tracked as a Git submodule.
- `deliverables/`: generated project status reports, including `status.html`.

## Current Status

The Codex queue has completed tasks `001` through `022`. The latest dashboard is:

```text
deliverables/status.html
```

The latest Demo 10 dry-run regression passed with:

```text
max_flight_error_m=0.067
final_endpoint_error_m=0.051
target_visible_ratio=0.775
```

Live PX4/Gazebo validation for Demo 10 is still a follow-up item.

## Restore Submodules

After cloning this repository, initialize external dependencies with:

```bash
git submodule update --init --recursive
```

## Common Checks

```bash
cd px4_ros2_ws
python3 -m compileall src scripts
colcon build --packages-select aerial_manip_msgs aerial_manip_control aerial_manip_gazebo aerial_manip_vision aerial_manip_eval aerial_manip_policy
python3 scripts/check_demo_10.py logs/demo10_air_reach/20260527_191707
```
