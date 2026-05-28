# Stage 2 Environment Audit

Task: `031-install-and-verify-live-dependencies`

Audit date: 2026-05-28

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
codex-logs/031-install-and-verify-live-dependencies.log
```

## Current Status

Status: `WARN`

Live Stage 2 / Demo 10 readiness: `YES`

Dry-run readiness: `YES`

Installed the missing ROS 2 Jazzy live dependencies with `apt-get` during this
audit. No runtime code or package manifests were changed.

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
- Required ROS 2 Jazzy live packages are visible through `ros2 pkg prefix`:
  - `ros_gz_bridge`
  - `gz_ros2_control`
  - `controller_manager`
  - `joint_state_broadcaster`
  - `forward_command_controller`
  - `joint_trajectory_controller`
- LeRobot is available in the project conda environment:
  `/home/clcwork/miniconda3/envs/lerobot/bin/python` reports `lerobot`
  version `0.5.2`.

## WARN Items

- The active `/usr/bin/python3` environment cannot import `lerobot`.
  Use `/home/clcwork/miniconda3/envs/lerobot/bin/python` or activate the
  `lerobot` conda environment for LeRobot training and policy work.

## Installed Packages

The following Debian packages were installed for live Stage 2 / Demo 10
readiness:

```text
ros-jazzy-ros-gz-bridge
ros-jazzy-gz-ros2-control
ros-jazzy-controller-manager
ros-jazzy-joint-state-broadcaster
ros-jazzy-forward-command-controller
ros-jazzy-joint-trajectory-controller
```

Final preflight result:

```text
SUMMARY pass=20 warn=1 fail=0
RESULT=WARN live_ready=YES dry_run_ready=YES reason=optional_warnings
```

Recheck package visibility with:

```bash
ros2 pkg prefix ros_gz_bridge
ros2 pkg prefix gz_ros2_control
ros2 pkg prefix controller_manager
ros2 pkg prefix joint_state_broadcaster
ros2 pkg prefix forward_command_controller
ros2 pkg prefix joint_trajectory_controller
```

## Stage 2 Readiness

Task 012-022 dry-run paths can continue. The current environment now passes the
live ROS/Gazebo bridge and ros2_control prerequisite checks for Demo 10.

`DEMO10_MODE=live` is allowed from the dependency preflight perspective when
`bash scripts/check_stage2_environment.sh` continues to report
`live_ready=YES`. A warning for active `/usr/bin/python3` missing `lerobot`
does not by itself block Demo 10 live runs, because the dedicated LeRobot conda
Python is available for policy work.
