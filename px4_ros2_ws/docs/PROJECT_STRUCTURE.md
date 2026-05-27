# px4_ros2_ws Project Structure

This document summarizes the current structure of `/home/clcwork/UAV_capture/px4_ros2_ws` for Task 001. The raw audit command output is saved in `codex-logs/001-audit-project-structure.log`.

## Workspace Overview

Top-level workspace areas:

| Path | Role | Notes |
| --- | --- | --- |
| `src/` | ROS 2 source packages | Main editable package area for this workspace. |
| `scripts/` | Stack, demo, experiment, and recorder launch helpers | Prefer these scripts for PX4/Gazebo/Micro XRCE-DDS and demo runs. |
| `logs/` | Experiment/runtime logs | Contains timestamped demo and hover logs. Do not delete. |
| `visualizations/` | Generated visualization artifacts | Contains timestamped demo outputs such as CSV, plots, videos, summaries, and results. Do not delete or overwrite existing timestamped runs. |
| `codex-tasks/` | Task definitions | Current task queue and requirements. |
| `codex-logs/` | Codex task execution logs | Includes this task's audit log. |
| `build/` | Colcon build output | Generated build artifacts. |
| `install/` | Colcon install output | Generated install artifacts and setup files. |
| `log/` | Colcon build logs | Generated build logs from previous `colcon` runs. |

## ROS 2 Packages

Current packages under `src/`:

| Package | Build type | Purpose |
| --- | --- | --- |
| `px4_msgs` | `ament_cmake` | PX4 uORB-equivalent ROS message and service definitions. This directory contains many generated interface definitions under `msg/` and `srv/`, and should be treated as upstream PX4 message source unless a task explicitly requires changes. |
| `px4_offboard_hover` | `ament_python` | Custom Python package for PX4 offboard demos, trajectory recording, and hover verification. |

`px4_offboard_hover` Python modules currently include:

- `hover.py`
- `verify_hover.py`
- `waypoint_flight.py`
- `circle_trajectory.py`
- `external_setpoint.py`
- `trajectory_recorder.py`
- `offboard_base.py`

Installed console entry points from `px4_offboard_hover/setup.py`:

- `hover`
- `verify_hover`
- `demo02_waypoint_flight`
- `demo03_circle_trajectory`
- `demo04_external_setpoint`
- `trajectory_recorder`

## Scripts

Current files under `scripts/`:

| Script | Purpose |
| --- | --- |
| `start_stack.sh` | Starts the PX4/Gazebo/Micro XRCE-DDS stack used by the demos. |
| `stop_stack.sh` | Stops the running stack. |
| `run_demo01_hover.sh` | Demo 01 Offboard Hover runner. |
| `run_demo02_waypoint_flight.sh` | Demo 02 Waypoint Flight runner. |
| `run_demo03_circle_trajectory.sh` | Demo 03 Circle Trajectory runner. |
| `run_demo04_external_setpoint.sh` | Demo 04 External Setpoint Interface runner. |
| `run_hover_experiment.sh` | Earlier/offboard hover experiment runner. |
| `run_trajectory_recorder.sh` | Trajectory recorder helper used by demo visualization workflows. |

These scripts are existing workflow entry points and were not modified during this audit.

## Experiment Logs

Runtime logs are stored under `logs/` by demo or experiment name:

- `logs/demo01_hover/`
- `logs/demo02_waypoint_flight/`
- `logs/demo03_circle_trajectory/`
- `logs/demo04_external_setpoint/`
- `logs/offboard_hover/`

Each demo directory contains timestamped runs. Observed log file names include:

- `demo01.log`
- `demo02.log`
- `demo03.log`
- `demo04.log`
- `trajectory_recorder.log`
- `target_sequence.log`
- `hover.log`
- `verify.log`
- `agent_tail.log`
- `px4_tail.log`

These are experiment results and diagnostic logs. They should not be deleted, truncated, or overwritten unless a task explicitly requires it and the user confirms.

## Visualization Outputs

Visualization results are stored under `visualizations/<demo>/<timestamp>/`.

Current demo visualization roots:

- `visualizations/demo01_hover/`
- `visualizations/demo02_waypoint_flight/`
- `visualizations/demo03_circle_trajectory/`
- `visualizations/demo04_external_setpoint/`

Observed standard output files:

- `trajectory.csv`
- `trajectory_3d.png`
- `xy_path.png`
- `height_curve.png`
- `speed_curve.png`
- `tracking_error.png`
- `trajectory.mp4`
- `summary.md`
- `result.txt`

Some earlier runs also contain `trajectory.png` instead of the newer split plot names. Existing timestamped visualization directories are experiment results and should not be deleted or overwritten.

## Source vs Generated vs Results

Source/editable project areas:

- `src/px4_offboard_hover/`
- `scripts/`
- `docs/`
- `codex-tasks/`
- Top-level project documents such as `BASIC_CONTROL_DEMOS.md`, `OFFBOARD_HOVER_EXPERIMENT.md`, and `TOOLS_AND_SCRIPTS_GUIDE.md`

External/upstream or avoid-editing areas:

- `src/px4_msgs/`: PX4 message/interface package. Avoid modifying unless the task explicitly requires it.

Generated build areas:

- `build/`
- `install/`
- `log/`

Experiment/result areas that should not be deleted:

- `logs/`
- `visualizations/`
- `codex-logs/`
- Any timestamped run directory under `logs/` or `visualizations/`
- Data artifacts such as `trajectory.csv`, plots, videos, summaries, and result files

## Audit Notes

- The workspace root itself is not a Git repository according to `git status`; however, `src/px4_msgs/` contains its own `.git` directory.
- Demo 1-4 have existing runtime logs and visualization outputs.
- The audit deliverable log for this task is `codex-logs/001-audit-project-structure.log`.
