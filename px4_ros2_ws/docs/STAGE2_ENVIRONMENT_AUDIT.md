# Stage 2 Environment Audit

Task: `011-audit-stage2-environment`

Audit date: 2026-05-27

Workspace:

```text
/home/clcwork/UAV_capture/px4_ros2_ws
```

Raw command log:

```text
codex-logs/011-audit-stage2-environment.log
```

## Summary

Stage 2 can rely on the existing PX4 model assets, ROS 2 command-line tools,
Gazebo Sim, and the dedicated LeRobot conda environment. The active ROS 2 Jazzy
environment does not currently expose the ROS/Gazebo bridge or ros2_control
controller packages needed for aerial manipulation integration.

No packages were installed and no runtime behavior was changed during this
audit.

## PASS Items

- Workspace root confirmed:
  `/home/clcwork/UAV_capture/px4_ros2_ws`.
- ROS 2 CLI is available:
  `ros2 --help >/dev/null && echo ROS2_OK` returned `ROS2_OK`.
- Active ROS distribution:
  `ROS_DISTRO=jazzy`, with `/opt/ros/jazzy` on `AMENT_PREFIX_PATH`.
- Gazebo Sim is available:
  `gz sim --versions` returned `8.11.0`.
- LeRobot is available in the project conda environment:
  `/home/clcwork/miniconda3/envs/lerobot/bin/python` can import `lerobot`;
  installed distribution version is `0.5.2`.
- Required PX4 Gazebo model files exist and are non-empty:
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500_mono_cam/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/mono_cam/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/arucotag/model.sdf`

## WARN Items

- The active `/usr/bin/python3` environment cannot import `lerobot`.
  Use `/home/clcwork/miniconda3/envs/lerobot/bin/python` or activate the
  `lerobot` conda environment for LeRobot work.
- The following ROS 2 packages are missing from the active ROS 2 Jazzy
  environment:
  - `ros_gz_bridge`
  - `gz_ros2_control`
  - `controller_manager`
  - `joint_state_broadcaster`
  - `forward_command_controller`
  - `joint_trajectory_controller`
- `dpkg-query` did not report installed Debian packages matching the required
  ROS/Gazebo bridge or ros2_control controller packages.
- `ros2 --version` is not supported by this ROS 2 CLI; version evidence is from
  `ROS_DISTRO`, `/opt/ros/jazzy`, and `ros2 doctor --report`.

## Concrete Missing Packages

The following package names should be treated as missing for Stage 2 planning
until a later task explicitly installs or vendors them:

```text
ros_gz_bridge
gz_ros2_control
controller_manager
joint_state_broadcaster
forward_command_controller
joint_trajectory_controller
```

Likely Debian package names for ROS 2 Jazzy are:

```text
ros-jazzy-ros-gz-bridge
ros-jazzy-gz-ros2-control
ros-jazzy-controller-manager
ros-jazzy-joint-state-broadcaster
ros-jazzy-forward-command-controller
ros-jazzy-joint-trajectory-controller
```

These were not installed in this task, per the task requirement to record
missing dependencies as risks only.

## Stage 2 Readiness

Status: `WARN`

PX4/Gazebo assets and base ROS 2/Gazebo tooling are present, and LeRobot exists
in the dedicated conda environment. Stage 2 aerial manipulation packages should
not assume ROS/Gazebo bridge or ros2_control controller availability until the
missing ROS 2 packages are installed and rechecked.
