# Project Audit Summary

- generated_at: `2026-05-28T08:35:46+08:00`
- workspace: `/home/clcwork/UAV_capture/px4_ros2_ws`
- overall_status: `Warning`
- detected_stack: `ROS 2 Jazzy`, `PX4 SITL`, `Gazebo Sim 8.11.0`, `Micro XRCE-DDS Agent`, `Python/rclpy`, `colcon`, shell automation

## Current Evidence

- Demo 10 dry-run: `PASS` at `logs/demo10_air_reach/20260528_002122`
- Demo 10 checker: `PASS` for `logs/demo10_air_reach/20260528_002122`
- Demo 10 live-smoke: `PASS` at `logs/demo10_air_reach/20260528_001327`
- Demo 10 full live: `UNVERIFIED`
- Vision smoke: `WARN` at `visualizations/demo_07_camera/20260528_000310`
- Camera sample frame: `not_captured`; `ros_gz_bridge` is missing
- Stage 2 environment preflight: `WARN`, `live_ready=NO`, `dry_run_ready=YES`

## Latest Commands

- `python3 -m compileall src scripts`: `PASS` (codex-logs/030-refresh-project-status-deliverables.log)
- `bash -n run_codex_queue.sh`: `PASS` (codex-logs/030-refresh-project-status-deliverables.log)
- `DEMO10_MODE=dry-run bash scripts/run_regression_demo_10.sh`: `PASS` (logs/demo10_air_reach/20260528_002122)
- `python3 scripts/check_demo_10.py logs/demo10_air_reach`: `PASS` (logs/demo10_air_reach/20260528_002122)
- `bash scripts/check_stage2_environment.sh`: `WARN` (codex-logs/030-refresh-project-status-deliverables.log)

## Live Validation Gaps

- Missing ROS/Gazebo bridge and ros2_control packages: `ros_gz_bridge`, `gz_ros2_control`, `controller_manager`, `joint_state_broadcaster`, `forward_command_controller`, `joint_trajectory_controller`.
- Full `DEMO10_MODE=live` has not been run after the latest hardening; latest live evidence is stack readiness only.
- Camera bridge sample frame was not captured because `ros_gz_bridge` is unavailable.
- Active `/usr/bin/python3` cannot import `lerobot`; `/home/clcwork/miniconda3/envs/lerobot/bin/python` reports `lerobot_version=0.5.2`.

## Important Modules

- `src/px4_offboard_hover`: `present` - Demo 01-04 offboard control and UAV bridge package.
- `src/aerial_manip_msgs`: `present` - Stage 2 arm/platform/observation messages and Approach action.
- `src/aerial_manip_control`: `present` - Arm bridge, state aggregator, approach coordinator, ros2_control launch/config.
- `src/aerial_manip_gazebo`: `present` - x500_arm_2dof model, smoke world, camera bridge config.
- `src/aerial_manip_vision`: `present` - Target pose node with explicit placeholder support.
- `src/aerial_manip_eval`: `present` - Demo 10 dry-run/live runner support, synthetic controller, episode recorder.
- `src/aerial_manip_policy`: `present` - LeRobot baseline training and policy bridge scaffolding.

## Next Actions

- Install the missing ROS 2 Jazzy bridge/control packages when approved.
- Rerun bash scripts/check_stage2_environment.sh and bash scripts/smoke_vision_bridge.sh after package installation.
- Rerun DEMO10_MODE=live-smoke RESET_STACK=1 bash scripts/run_regression_demo_10.sh before full live Demo 10.
- Run DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh only after live prerequisites pass.
