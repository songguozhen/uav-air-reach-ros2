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

## Demo 10 Air Reach Check

Demo 10 combines the stage-2 UAV bridge, tag target pose, approach coordinator,
arm bridge, and episode recorder into an air-reach regression. The default
runner is safe for development machines that do not currently have PX4/Gazebo
running:

```bash
bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

Default `DEMO10_MODE=auto` writes a deterministic dry-run artifact under:

```text
logs/demo10_air_reach/<timestamp>/
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
the expected path.
