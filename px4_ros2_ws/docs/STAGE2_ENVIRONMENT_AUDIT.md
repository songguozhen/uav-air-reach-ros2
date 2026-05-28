# Stage 2 Environment Audit

Task: `023-stage2-environment-preflight`

Audit date: 2026-05-27

Workspace:

```text
/home/clcwork/UAV_capture/px4_ros2_ws
```

Reusable preflight:

```bash
bash scripts/check_stage2_environment.sh
```

Raw command log:

```text
codex-logs/023-stage2-environment-preflight.log
```

## Current Status

Status: `WARN`

Live Stage 2 / Demo 10 readiness: `NO`

Dry-run readiness: `YES`

No packages were installed and no runtime code or package manifests were
changed during this audit.

## PASS Items

- Workspace root confirmed:
  `/home/clcwork/UAV_capture/px4_ros2_ws`.
- ROS 2 CLI is available:
  `/opt/ros/jazzy/bin/ros2`.
- Active ROS distribution is Jazzy:
  `ROS_DISTRO=jazzy`, prefix `/opt/ros/jazzy`.
- Gazebo Sim is available:
  `gz sim --versions` returned `8.11.0`.
- PX4 SITL binary is executable:
  `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/build/px4_sitl_default/bin/px4`.
- Micro XRCE-DDS Agent is executable:
  `/home/clcwork/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent`.
- Required PX4 Gazebo model files exist and are non-empty:
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500_mono_cam/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/mono_cam/model.sdf`
  - `/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/arucotag/model.sdf`
- Stage 2 local Gazebo assets exist and are non-empty:
  - `src/aerial_manip_gazebo/models/x500_arm_2dof/model.sdf`
  - `src/aerial_manip_gazebo/models/fiducial_target_aruco/model.sdf`
  - `src/aerial_manip_gazebo/worlds/x500_arm_2dof_smoke.sdf`
- LeRobot is available in the project conda environment:
  `/home/clcwork/miniconda3/envs/lerobot/bin/python` reports `lerobot`
  version `0.5.2`.

## WARN Items

- The active `/usr/bin/python3` environment cannot import `lerobot`.
  Use `/home/clcwork/miniconda3/envs/lerobot/bin/python` or activate the
  `lerobot` conda environment for LeRobot training and policy work.
- The following ROS 2 packages are missing from the active ROS 2 Jazzy
  environment:
  - `ros_gz_bridge`
  - `gz_ros2_control`
  - `controller_manager`
  - `joint_state_broadcaster`
  - `forward_command_controller`
  - `joint_trajectory_controller`

## Concrete Missing Packages

Missing ROS package names:

```text
ros_gz_bridge
gz_ros2_control
controller_manager
joint_state_broadcaster
forward_command_controller
joint_trajectory_controller
```

Likely Debian package names for ROS 2 Jazzy:

```text
ros-jazzy-ros-gz-bridge
ros-jazzy-gz-ros2-control
ros-jazzy-controller-manager
ros-jazzy-joint-state-broadcaster
ros-jazzy-forward-command-controller
ros-jazzy-joint-trajectory-controller
```

These were not installed in this task. Recheck after any future dependency
installation with:

```bash
ros2 pkg prefix ros_gz_bridge
ros2 pkg prefix gz_ros2_control
ros2 pkg prefix controller_manager
ros2 pkg prefix joint_state_broadcaster
ros2 pkg prefix forward_command_controller
ros2 pkg prefix joint_trajectory_controller
/usr/bin/python3 -c 'import importlib.util; print(importlib.util.find_spec("lerobot"))'
```

## Stage 2 Readiness

Task 012-022 dry-run paths can continue. The current environment should keep
Demo 10 in dry-run or automatic dry-run mode because live ROS/Gazebo bridge and
ros2_control prerequisites are missing.

Use `DEMO10_MODE=live` only after `bash scripts/check_stage2_environment.sh`
reports `live_ready=YES`. A warning for active `/usr/bin/python3` missing
`lerobot` does not by itself block Demo 10 live runs, because the dedicated
LeRobot conda Python is available for policy work.
