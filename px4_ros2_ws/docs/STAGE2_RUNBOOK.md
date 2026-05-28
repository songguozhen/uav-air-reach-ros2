# Stage 2 Runbook

This runbook covers the current aerial manipulation stack from Task 012-022.
External modules must use the high-level `/uav/*`, `/arm/*`, and `/approach`
interfaces instead of publishing directly to PX4 `/fmu/in/*` topics.

## Environment Preflight

Run the preflight before live aerial manipulation work:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
bash scripts/check_stage2_environment.sh
```

The script reports each item as `PASS`, `WARN`, or `FAIL`, lists exact missing
ROS package names, and prints recheck commands. It does not install packages.

Current result from `codex-logs/031-install-and-verify-live-dependencies.log`:

```text
RESULT=WARN live_ready=YES dry_run_ready=YES reason=optional_warnings
```

## Demo 10 Mode Rule

Keep Demo 10 in dry-run mode when the preflight reports either:

```text
RESULT=FAIL
live_ready=NO
```

The current environment now has these live prerequisites installed and visible
to ROS 2 Jazzy:

```text
ros_gz_bridge
gz_ros2_control
controller_manager
joint_state_broadcaster
forward_command_controller
joint_trajectory_controller
```

Use the dry-run regression:

```bash
bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

Equivalent explicit mode:

```bash
DEMO10_MODE=dry-run bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

Use the live runner when the preflight reports `live_ready=YES`:

```bash
DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

An active `/usr/bin/python3` LeRobot warning alone does not force Demo 10 to
stay dry-run. LeRobot work should use:

```bash
/home/clcwork/miniconda3/envs/lerobot/bin/python
```

## Recheck Commands

After installing or otherwise providing dependencies in a separate approved
task, rerun:

```bash
bash scripts/check_stage2_environment.sh
ros2 pkg prefix ros_gz_bridge
ros2 pkg prefix gz_ros2_control
ros2 pkg prefix controller_manager
ros2 pkg prefix joint_state_broadcaster
ros2 pkg prefix forward_command_controller
ros2 pkg prefix joint_trajectory_controller
```
