# Codex Runbook

This file is the required operating record for every Codex run in this
workspace. Read it together with `AGENTS.md` before changing files or running
simulation tasks.

## Workspace

Root workspace:

```text
/home/clcwork/UAV_capture/px4_ros2_ws
```

Related external paths:

```text
/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot
/home/clcwork/Micro-XRCE-DDS-Agent/build
/home/clcwork/miniconda3/envs/lerobot
```

This directory is not currently a git repository. Treat existing files,
generated artifacts, logs, and user edits as persistent project state.

## Current Project State

Implemented ROS 2 package:

```text
src/px4_offboard_hover
```

Available PX4 offboard demos and tools:

- Demo 01 hover: `scripts/run_demo01_hover.sh`
- Demo 02 waypoint flight: `scripts/run_demo02_waypoint_flight.sh`
- Demo 03 circle trajectory: `scripts/run_demo03_circle_trajectory.sh`
- Demo 04 external setpoint / UAV bridge: `scripts/run_demo04_external_setpoint.sh`
- Hover experiment: `scripts/run_hover_experiment.sh`
- Trajectory recorder: `scripts/run_trajectory_recorder.sh`
- Output checker: `scripts/check_demo_outputs.sh`
- Stack startup and cleanup: `scripts/start_stack.sh`, `scripts/stop_stack.sh`

Implemented UAV bridge:

```text
src/px4_offboard_hover/px4_offboard_hover/uav_control_bridge.py
```

The bridge exposes high-level UAV control topics:

```text
/uav/target_position      geometry_msgs/msg/Point
/uav/current_position     geometry_msgs/msg/PointStamped
/uav/current_target       geometry_msgs/msg/PointStamped
/uav/reached_target       std_msgs/msg/Bool
/uav/control_state        std_msgs/msg/String
```

External modules, including future vision, LeRobot, planner, and UAV-arm work,
must use `/uav/*` topics by default. Do not publish directly to PX4
`/fmu/in/*` topics from external modules unless a task explicitly requires it.

Current bridge safety parameters include:

```text
initial_x
initial_y
initial_z
yaw
target_timeout
max_altitude
min_altitude
max_horizontal_range
target_jump_limit
reach_xy_tolerance
reach_z_tolerance
reach_hold_time
```

Coordinate rule: `/uav/target_position` is local PX4 NED. Positive altitude is
represented as negative `z`. For example, 2 m altitude is `z: -2.0`.

Latest recorded full Demo 04 bridge simulation:

```text
timestamp: 20260527_085025
visuals: visualizations/demo04_external_setpoint/20260527_085025
logs: logs/demo04_external_setpoint/20260527_085025
result: RESULT=PASS reason=ok
checker: CHECK=PASS
avg_error_3d_m: 0.20
final_error_3d_m: 0.02
final_position_ned: (-0.01, -0.01, -2.01)
```

The preceding run at `20260527_084530` failed because a stale Gazebo
`default.sdf` server from an earlier day was still running. `RESET_STACK=1` and
`scripts/stop_stack.sh` now clean this project Gazebo world process before
reruns.

## File Path Management

Use these path rules consistently:

- Use workspace-relative paths in commands and documentation when already under
  `/home/clcwork/UAV_capture/px4_ros2_ws`.
- Use absolute paths when referring to artifacts in final reports, cross-root
  scripts, or external paths outside this workspace.
- Keep source code under `src/`.
- Keep reusable shell entry points under `scripts/`.
- Keep task definitions under `codex-tasks/`.
- Keep Codex execution logs and done markers under `codex-logs/`.
- Keep project documentation under `docs/` or top-level Markdown files.
- Keep simulation logs under `logs/<demo>/<timestamp>/`.
- Keep visualization outputs under `visualizations/<demo>/<timestamp>/`.
- Do not hand-edit generated build outputs under `build/`, `install/`, or
  `log/build_*` unless the task is explicitly about generated artifacts.
- Do not overwrite or delete existing timestamped `logs/` or
  `visualizations/` directories.

Stable generated Demo output names:

```text
trajectory.csv
trajectory_3d.png
xy_path.png
height_curve.png
speed_curve.png
tracking_error.png
trajectory.mp4
summary.md
result.txt
```

## Required Codex Run Procedure

Every Codex run must follow this procedure:

1. Confirm the working directory is the workspace root:

   ```bash
   cd /home/clcwork/UAV_capture/px4_ros2_ws
   ```

2. Read the governing files before planning edits:

   ```text
   AGENTS.md
   codex.md
   relevant codex-tasks/<task>.md
   relevant docs/*.md or source files
   ```

3. Before editing, identify the exact files to touch and avoid unrelated
   refactors.

4. Preserve all existing user changes and generated results. Never run
   destructive cleanup such as `git reset --hard`, broad `rm -rf`, or deleting
   log/result directories unless the user explicitly asks.

5. Use `apply_patch` for manual file edits. Use formatting/build tools only
   after the target files are clear.

6. Record the task execution in `codex-logs/`:

   ```text
   codex-logs/<task-stem>-<YYYYMMDD_HHMMSS>.log
   codex-logs/<task-stem>.done
   ```

   `run_codex_queue.sh` creates these automatically. For manual one-off work,
   create or preserve equivalent logs when practical.

7. For shell script changes, run at least:

   ```bash
   bash -n <script>
   ```

8. For Python node changes, run at least one relevant Python check:

   ```bash
   python3 -m compileall src scripts
   ```

   Use `colcon build --packages-select <package>` when package metadata,
   console entry points, dependencies, or ROS node code changed.

9. For demo/output changes, run the relevant smoke checker:

   ```bash
   ./scripts/check_demo_outputs.sh visualizations/<demo>
   ```

10. For PX4/Gazebo simulation runs, prefer existing scripts. Use
    `RESET_STACK=1` for reproducible runs, and call `scripts/stop_stack.sh`
    before finishing unless the user explicitly wants the stack left running.

11. If project state changes, update the appropriate Markdown record in the same
    run. Examples:

    ```text
    codex.md
    docs/REGRESSION_CHECKS.md
    docs/UAV_CONTROL_API.md
    docs/VISUALIZATION_GUIDE.md
    TOOLS_AND_SCRIPTS_GUIDE.md
    ```

12. Final reports must include:

    ```text
    changed files
    commands run
    test result
    known risks
    output paths, when logs or visualizations were generated
    ```

## Codex Queue Requirements

`run_codex_queue.sh` is the standard runner for queued task files. It must:

- verify `AGENTS.md`, `codex.md`, `codex-tasks/`, and `codex-logs/` exist;
- pass the contents of `codex.md` together with the task file to Codex;
- write timestamped logs under `codex-logs/`;
- create `.done` markers only after a task exits successfully;
- support `--dry-run`, `--from <prefix>`, and `--task <file>`;
- skip completed queued tasks unless `--task` is used.

Before adding a new queued task, create a numbered Markdown file:

```text
codex-tasks/010-short-task-name.md
```

The task file should state:

```text
goal
allowed files or directories
required validation commands
required documentation updates
expected final report fields
```

## Current Validation Commands

Known passing checks after the latest bridge work:

```bash
bash -n run_codex_queue.sh
bash -n scripts/check_demo_outputs.sh
bash -n scripts/run_demo04_external_setpoint.sh
bash -n scripts/start_stack.sh
bash -n scripts/stop_stack.sh
python3 -m compileall src scripts
colcon build --packages-select px4_offboard_hover
./scripts/check_demo_outputs.sh visualizations/demo01_hover
./scripts/check_demo_outputs.sh visualizations/demo02_waypoint_flight
./scripts/check_demo_outputs.sh visualizations/demo03_circle_trajectory
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint
```

Latest full bridge simulation command:

```bash
./scripts/run_demo04_external_setpoint.sh
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint/20260527_085025
```

