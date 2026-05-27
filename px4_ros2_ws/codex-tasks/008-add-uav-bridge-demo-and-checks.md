# Task 008: Add UAV Bridge Demo and Checks

## Task goal

- Add a runnable demo path that uses `uav_control_bridge` for the external setpoint workflow.
- Preserve old Demo 04 behavior as much as possible, but prefer the bridge path for future runs.

## Required behavior

- Add or update a script under `scripts/` that runs the bridge-backed external setpoint demo.
- The script must:
  - Start the existing stack with `scripts/start_stack.sh`.
  - Start the trajectory recorder using `scripts/run_trajectory_recorder.sh`.
  - Run `ros2 run px4_offboard_hover uav_control_bridge`.
  - Publish the same square target sequence used by Demo 04 to `/uav/target_position`.
  - Write logs under `logs/demo04_external_setpoint/<timestamp>/`.
  - Write visualization artifacts under `visualizations/demo04_external_setpoint/<timestamp>/`.
- Keep standard output names:
  - `trajectory.csv`
  - `trajectory_3d.png`
  - `xy_path.png`
  - `height_curve.png`
  - `speed_curve.png`
  - `tracking_error.png`
  - `trajectory.mp4`
  - `summary.md`
  - `result.txt`
- If the full simulation cannot be run in the current environment, still add syntax checks and a dry-run or documented manual command path.

## Allowed changes

- `scripts/`
- `docs/VISUALIZATION_GUIDE.md`
- `docs/REGRESSION_CHECKS.md`
- `codex-logs/008-add-uav-bridge-demo-and-checks.log`

Do not delete or overwrite existing `logs/` or `visualizations/` results.

## Required commands

Save command output to `codex-logs/008-add-uav-bridge-demo-and-checks.log`:

```bash
chmod +x scripts/*.sh
bash -n scripts/run_codex_queue.sh 2>/dev/null || true
bash -n run_codex_queue.sh
bash -n scripts/check_demo_outputs.sh
bash -n <new-or-updated-demo-script>
./scripts/check_demo_outputs.sh visualizations/demo01_hover
./scripts/check_demo_outputs.sh visualizations/demo02_waypoint_flight
./scripts/check_demo_outputs.sh visualizations/demo03_circle_trajectory
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint
```

If a full bridge demo is executed, also run `./scripts/check_demo_outputs.sh` on the newly generated Demo 04 visualization directory.

## Deliverables

- Bridge-backed Demo 04 script or clearly updated existing Demo 04 script.
- Updated docs for running and checking the bridge-backed demo.
- `codex-logs/008-add-uav-bridge-demo-and-checks.log`

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

