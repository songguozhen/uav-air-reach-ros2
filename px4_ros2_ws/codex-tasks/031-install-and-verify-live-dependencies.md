# Task 031: Install and Verify Live Dependencies

## Task goal

- Make the Stage 2 live PX4/Gazebo/ROS 2 path ready for full Demo 10 execution.
- Verify the required ROS/Gazebo bridge and ros2_control packages are visible to ROS 2 Jazzy.
- Keep this task focused on environment readiness; do not implement visualization or Demo behavior changes here.

## Allowed changes

- `docs/STAGE2_ENVIRONMENT_AUDIT.md`
- `docs/STAGE2_RUNBOOK.md`
- `codex-logs/031-install-and-verify-live-dependencies.log`

## Implementation requirements

- Run the existing preflight first to capture current state.
- Check these packages and install them if the environment permits:
  - `ros-jazzy-ros-gz-bridge`
  - `ros-jazzy-gz-ros2-control`
  - `ros-jazzy-controller-manager`
  - `ros-jazzy-joint-state-broadcaster`
  - `ros-jazzy-forward-command-controller`
  - `ros-jazzy-joint-trajectory-controller`
- Do not modify PX4-Autopilot source code.
- After any installation or environment correction, rerun the preflight and record whether `live_ready=YES`.
- If package installation is blocked by sudo, apt source, network, or permissions, do not fake success; record the exact blocker and the command the user should rerun.

## Required commands

```bash
bash scripts/check_stage2_environment.sh | tee codex-logs/031-install-and-verify-live-dependencies.log
```

If packages are missing and installation is allowed:

```bash
sudo apt-get update
sudo apt-get install -y \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-gz-ros2-control \
  ros-jazzy-controller-manager \
  ros-jazzy-joint-state-broadcaster \
  ros-jazzy-forward-command-controller \
  ros-jazzy-joint-trajectory-controller
bash scripts/check_stage2_environment.sh | tee -a codex-logs/031-install-and-verify-live-dependencies.log
```

## Deliverables

- Updated environment audit/runbook notes if current live readiness differs from the previous status.
- A log showing the package status and final `live_ready` result.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `missing or installed packages`
