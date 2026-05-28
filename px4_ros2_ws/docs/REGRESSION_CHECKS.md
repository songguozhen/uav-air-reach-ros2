# Demo Regression Checks

This workspace provides a lightweight output checker for Demo 1-4 visualization
results and legacy hover verification logs.

## Script

Run from the workspace root:

```bash
./scripts/check_demo_outputs.sh visualizations/demo01_hover/<timestamp>
./scripts/check_demo_outputs.sh logs/offboard_hover/<timestamp>
```

The script prints `CHECK=PASS` and exits `0` when the checked output directory
passes. It prints `CHECK=FAIL`, lists missing files or fields, and exits non-zero
when a required check fails.

If the argument is a demo root such as `visualizations/demo01_hover`, the script
checks the newest timestamped child directory. If the argument is a current demo
log directory such as `logs/demo02_waypoint_flight/<timestamp>` and the matching
visualization directory exists, the script checks the visualization output.

## Current Demo 1-4 Checks

Current visualization directories are expected to contain:

```text
trajectory.csv
trajectory_3d.png
xy_path.png
height_curve.png
speed_curve.png
tracking_error.png
summary.md
result.txt
```

The checker also requires `result.txt` to contain:

```text
RESULT=PASS
```

`trajectory.csv` must contain a header with `timestamp` or `t`, plus all of:

```text
x
y
z
vx
vy
vz
```

Run the current Demo 1-4 smoke checks from the workspace root:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/check_demo_outputs.sh visualizations/demo01_hover
./scripts/check_demo_outputs.sh visualizations/demo02_waypoint_flight
./scripts/check_demo_outputs.sh visualizations/demo03_circle_trajectory
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint
```

Passing output contains `CHECK=PASS`. A non-zero exit means the directory is
missing a required file, a required CSV field, or a `RESULT=PASS` marker.

## Demo 04 Bridge Check

Demo 04 should normally be generated with the bridge-backed runner:

```bash
./scripts/run_demo04_external_setpoint.sh
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint
```

This starts the stack, runs `uav_control_bridge`, publishes the existing square
sequence to `/uav/target_position`, and records outputs under
`visualizations/demo04_external_setpoint/<timestamp>/`. Use this dry-run path
when the full PX4/Gazebo simulation is not available:

```bash
DRY_RUN=1 ./scripts/run_demo04_external_setpoint.sh
```

The target sequence uses NED `geometry_msgs/msg/Point` commands. For example,
`{x: 2.0, y: 0.0, z: -2.0}` means 2 m north, 0 m east, and 2 m positive
altitude because `/uav/target_position.z` is NED down.

For legacy comparison only, run:

```bash
DEMO04_MODE=legacy ./scripts/run_demo04_external_setpoint.sh
```

After a full Demo 04 run, check the newest output:

```bash
./scripts/check_demo_outputs.sh visualizations/demo04_external_setpoint
```

Latest bridge-backed simulation check:

```text
timestamp: 20260527_085025
result: RESULT=PASS reason=ok
check: CHECK=PASS
samples: 5725
duration_s: 119.94
avg_error_3d_m: 0.20
final_error_3d_m: 0.02
final_position_ned: (-0.01, -0.01, -2.01)
```

The immediately preceding run at `20260527_084530` failed because a stale
Gazebo `default.sdf` server from an earlier day was still running. `RESET_STACK`
and `stop_stack.sh` now clean the project Gazebo world process before reruns.

Visualization-copy commands for Mac are documented in
`docs/VISUALIZATION_GUIDE.md`.

## Stage 2 Frame and Schema Check

Task 026 adds a deterministic regression for the stage-2 frame boundary and
2-DOF arm schema. It does not start PX4, Gazebo, Micro XRCE-DDS, or any ROS
nodes.

Run from the workspace root:

```bash
python3 scripts/check_stage2_schema.py
```

Passing output contains:

```text
CHECK=PASS report=logs/demo_06_state_agg/<timestamp>/tf_report.json
```

The generated `tf_report.json` uses
`stage2_frame_schema_regression_v1` and records every enforced invariant. The
checker currently enforces:

- frame names: `map`, `uav/base_link`, `uav/arm_base`, `uav/ee_link`,
  `uav/camera_link`;
- TF chain: `map -> uav/base_link -> uav/arm_base -> uav/ee_link ->
  uav/camera_link`;
- NED-to-ENU TF conversion: `enu_x=ned_y`, `enu_y=ned_x`, `enu_z=-ned_z`;
- NED/ENU round trips for `(0, 0, 0)`, `(1, 2, -3)`, and
  `(-4.5, 0.25, 2.0)`;
- 2-DOF arm joint names: `arm_shoulder_pitch_joint`,
  `arm_elbow_pitch_joint`;
- two-element arm vectors for positions, velocities, efforts, limits, and
  default velocity limits;
- `ArmCommand`, `ArmState`, `PlatformState`, and `SystemObservation` message
  fields that make up the stage-2 state schema.

Use a fixed timestamp when a reproducible report path is needed:

```bash
python3 scripts/check_stage2_schema.py --timestamp 20260527_026_regression
```

## Demo 10 Air Reach Check

Demo 10 combines the stage-2 UAV bridge, tag target pose, approach coordinator,
arm bridge, and episode recorder into an air-reach regression. The default
runner is safe for development machines that do not currently have PX4/Gazebo
running:

```bash
bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

## Stage 2 Evidence Validator

Task 029 adds an artifact-based Stage 2 validator so Task 012-022 completion can
be checked against run evidence, docs, logs, and `.done` markers instead of
queue markers alone:

```bash
python3 scripts/check_stage2_evidence.py
```

The validator writes:

```text
deliverables/task-status.json
deliverables/task-summary.md
```

It reports Demo 10 dry-run and live/live-smoke evidence separately. The dry-run
check validates the latest dry-run `metrics.json`, `result.txt`,
`sequence_events.jsonl`, PASS result, required Demo 10 phase sequence, and
metric thresholds. The live check validates the latest live or live-smoke PASS
result and, for live-smoke runs, PX4 stack readiness in `stack_readiness.txt`.

The same report verifies that Stage 2 frame, control, vision, dataset, policy,
coordinator, and Demo 10 docs exist, then checks Task 012-022 task logs against
their `.done` markers and records any mismatch.

Default `DEMO10_MODE=auto` writes a deterministic dry-run artifact under:

```text
logs/demo10_air_reach/<timestamp>/
```

Use the bounded live stack smoke before a longer live run:

```bash
DEMO10_MODE=live-smoke RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

The smoke starts PX4/Gazebo and Micro XRCE-DDS, waits for PX4 to reach
`Ready for takeoff`, records the result in
`logs/demo10_air_reach/<timestamp>/stack_readiness.txt`, and then stops the
stack. If PX4 never reaches readiness, the file records the latest matching
preflight failure line or a timeout.

Latest bounded live-smoke check:

```text
timestamp: 20260528_001327
result: RESULT=PASS mode=live-smoke reason=stack_ready
readiness: STACK_READY=YES reason=ready_for_takeoff detail=PX4 reached Ready for takeoff
process cleanup: PASS; only the pre-existing uav_codex tmux/log command lines matched the broad pgrep command
```

Use a live stack only when PX4/Gazebo, Micro XRCE-DDS, ROS 2, and the stage-2
packages are built and available:

```bash
DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

The checker requires:

```text
metrics.json
sequence_events.jsonl
result.txt
```

`metrics.json` must use `demo10_air_reach_metrics_v1` and include PASS/FAIL
metrics for:

```text
flight_error.max_m <= flight_error.limit_m
joint_limits.violations == 0
target_visibility.visible_ratio >= target_visibility.min_visible_ratio
task_timeout.timed_out == false
final_endpoint_error.error_m <= final_endpoint_error.limit_m
```

The required phase sequence is:

```text
stable_hover
tag_detection
coordinated_approach
endpoint_hold
```

## Legacy Hover Check

Older hover experiment directories under `logs/offboard_hover/<timestamp>` may
not contain visualization files. For those directories, the checker accepts
`verify.log` when it contains:

```text
RESULT=PASS
```

## Known Limits

These checks are regression smoke checks, not full flight-quality validation.
They verify that standard artifacts exist, required CSV columns are present, and
the recorded PASS marker is present. They do not recompute trajectory metrics,
inspect image contents, validate MP4 playback, or prove that the vehicle followed
the expected path. The stage-2 frame/schema checker validates static conversion
and schema contracts only; it does not prove TF timing, live transforms, or arm
controller dynamics.
