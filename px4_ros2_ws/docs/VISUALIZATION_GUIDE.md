# Demo Visualization Guide

This guide covers the standard visualization outputs for Demo 1-4 in
`/home/clcwork/UAV_capture/px4_ros2_ws`.

## Standard Output Layout

Demo visualizations are written to timestamped directories:

```text
visualizations/<demo>/<YYYYMMDD_HHMMSS>/
```

The current standard files are:

| File | Purpose |
| --- | --- |
| `trajectory.csv` | Raw time series: position, velocity, speed, target position, and tracking error. |
| `trajectory_3d.png` | 3D actual and target trajectory. |
| `xy_path.png` | Top-down XY path with start/end markers. |
| `height_curve.png` | Altitude over time with target altitude when available. |
| `speed_curve.png` | Speed over time with the configured pass limit. |
| `tracking_error.png` | 3D, XY, and height tracking error over time. |
| `trajectory.mp4` | Optional XY animation when `ffmpeg` is available. |
| `summary.md` | Metrics and generated output list. |
| `result.txt` | PASS/FAIL status and reason. |

Older visualization directories may contain only `trajectory.png` plus
`trajectory.csv`. Do not rename, delete, or overwrite those historical results.

## Demo Output Names

Each current demo runner uses `scripts/run_trajectory_recorder.sh`, which starts
the `trajectory_recorder` ROS 2 node and writes the same standard file names.

| Demo | Runner | Visualization root | Standard files |
| --- | --- | --- | --- |
| Demo 01 Offboard Hover | `scripts/run_demo01_hover.sh` | `visualizations/demo01_hover/<timestamp>/` | `trajectory.csv`, `trajectory_3d.png`, `xy_path.png`, `height_curve.png`, `speed_curve.png` |
| Demo 02 Waypoint Flight | `scripts/run_demo02_waypoint_flight.sh` | `visualizations/demo02_waypoint_flight/<timestamp>/` | `trajectory.csv`, `trajectory_3d.png`, `xy_path.png`, `height_curve.png`, `speed_curve.png` |
| Demo 03 Circle Trajectory | `scripts/run_demo03_circle_trajectory.sh` | `visualizations/demo03_circle_trajectory/<timestamp>/` | `trajectory.csv`, `trajectory_3d.png`, `xy_path.png`, `height_curve.png`, `speed_curve.png` |
| Demo 04 External Setpoint Bridge | `scripts/run_demo04_external_setpoint.sh` | `visualizations/demo04_external_setpoint/<timestamp>/` | `trajectory.csv`, `trajectory_3d.png`, `xy_path.png`, `height_curve.png`, `speed_curve.png` |

## Demo 10 Air-Reach Visualizations

Demo 10 presentation plots are generated offline from the evidence under
`logs/demo10_air_reach/<timestamp>/`:

```bash
python3 scripts/generate_demo10_visualizations.py --latest-live
```

The `--latest-live` mode selects the newest successful `mode=live` run with
episode recorder observations and actions. If no sufficient live run exists, it
falls back to the newest successful dry-run evidence and writes
`mode=dry-run fallback` in `summary.json` and plot titles.

To render a specific run:

```bash
python3 scripts/generate_demo10_visualizations.py \
  --run-dir logs/demo10_air_reach/<timestamp>
```

Inputs are used when present:

| Input | Purpose |
| --- | --- |
| `metrics.json` | PASS/WARN labels, limits, aggregate flight, visibility, joint, timeout, and endpoint metrics. |
| `sequence_events.jsonl` | Phase start times for the sequence timeline. |
| `episodes/<episode>/observations.jsonl` | UAV position, target visibility, arm joint positions, and endpoint samples. |
| `episodes/<episode>/actions.jsonl` | UAV target commands and arm joint commands. |
| `episodes/<episode>/task_status.jsonl` | Task completion status for the generated summary. |

Outputs are written to:

```text
visualizations/demo10_air_reach/<timestamp>/
```

The generated files are:

| File | Purpose |
| --- | --- |
| `trajectory_3d.png` | UAV NED trajectory with commanded UAV target path. |
| `phase_timeline.png` | Stable hover, tag detection, coordinated approach, and endpoint hold timing. |
| `flight_error.png` | UAV tracking error against the latest target command, or aggregate metrics when samples are unavailable. |
| `target_visibility.png` | Target visibility samples or aggregate visible ratio. |
| `joint_positions.png` | Recorded arm joint positions with configured joint limit bands when available. |
| `endpoint_error.png` | End-effector target error samples or final endpoint error metric. |
| `summary.json` | Source paths, mode, PASS/WARN status, metrics, warnings, and generated file list. |

When a live run lacks a specific stream, the script still creates the expected
plot and labels the missing data with a WARN placeholder. Dry-run fallback
summaries must be treated as presentation placeholders, not live flight
evidence.

## Generate New Results

Run demos from the workspace root:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

./scripts/run_demo01_hover.sh
./scripts/run_demo02_waypoint_flight.sh
./scripts/run_demo03_circle_trajectory.sh
./scripts/run_demo04_external_setpoint.sh
```

Demo 04 now runs the bridge-backed external setpoint workflow by default:

```bash
DEMO04_MODE=bridge ./scripts/run_demo04_external_setpoint.sh
```

The runner starts `scripts/start_stack.sh`, records with
`scripts/run_trajectory_recorder.sh`, runs
`ros2 run px4_offboard_hover uav_control_bridge`, and publishes the existing
square target sequence to `/uav/target_position` as NED
`geometry_msgs/msg/Point` commands. The square uses z=-2.0, which means 2 m
positive altitude in PX4 NED coordinates.

The bridge-backed runner passes these bridge parameters by default:

| Parameter | Runner value | Bridge node default |
| --- | --- | --- |
| `target_timeout` | `25.0` | `1.0` |
| `target_jump_limit` | `2.5` | `1.5` |
| `max_altitude` | `5.0` | `5.0` |
| `min_altitude` | `0.5` | `0.5` |
| `max_horizontal_range` | `5.0` | `5.0` |

The larger demo timeout and jump limit are only for the square-sequence demo.
Manual bridge runs should start from the node defaults unless a test requires
different limits.

The original direct Demo 04 node is still available for comparison:

```bash
DEMO04_MODE=legacy ./scripts/run_demo04_external_setpoint.sh
```

To inspect the bridge command path without launching PX4/Gazebo:

```bash
DRY_RUN=1 ./scripts/run_demo04_external_setpoint.sh
```

To publish one safe manual target while the bridge is running:

```bash
ros2 topic pub --once /uav/target_position geometry_msgs/msg/Point \
  '{x: 0.0, y: 0.0, z: -2.0}'
```

`/uav/target_position.z` is NED down. A positive altitude of 2 m must be sent as
`z=-2.0`; sending `z=2.0` asks for a point below the local origin and the
bridge will reject it.

Each runner creates a new timestamped directory under `logs/<demo>/` and
`visualizations/<demo>/`. The runner prints the exact output paths after the
trajectory recorder finishes.

## Check Existing Results

List available PNG outputs:

```bash
find visualizations -name "*.png" | sort
```

Check the newest directory for each demo:

```bash
for demo in demo01_hover demo02_waypoint_flight demo03_circle_trajectory demo04_external_setpoint; do
  latest="$(find "visualizations/$demo" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
  echo "$demo -> $latest"
  ls "$latest"/trajectory.csv \
     "$latest"/trajectory_3d.png \
     "$latest"/xy_path.png \
     "$latest"/height_curve.png \
     "$latest"/speed_curve.png
done
```

## View Results Locally

Generate the current presentation-oriented simulation showcase:

```bash
python3 scripts/generate_simulation_showcase.py
```

Open the generated page from the workspace:

```text
deliverables/simulation_showcase.html
```

The showcase links the latest verified Demo 01-04 trajectory artifacts, Demo 07
camera sample or capture status, and Demo 10 phase/trajectory/arm/error
visualizations. It does not overwrite timestamped visualization directories.

Open PNG files from the timestamped visualization directory with an image viewer:

```bash
xdg-open visualizations/demo01_hover/<timestamp>/trajectory_3d.png
xdg-open visualizations/demo01_hover/<timestamp>/xy_path.png
xdg-open visualizations/demo01_hover/<timestamp>/height_curve.png
xdg-open visualizations/demo01_hover/<timestamp>/speed_curve.png
```

Read metrics and status:

```bash
cat visualizations/demo01_hover/<timestamp>/summary.md
cat visualizations/demo01_hover/<timestamp>/result.txt
```

## Copy Results To Mac

From the Mac terminal, copy one timestamped result directory:

```bash
scp -r <linux_user>@<linux_host>:/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo01_hover/<timestamp> ~/Desktop/px4_demo01_hover_<timestamp>
```

Copy all Demo 1-4 visualization results:

```bash
scp -r <linux_user>@<linux_host>:/home/clcwork/UAV_capture/px4_ros2_ws/visualizations ~/Desktop/px4_visualizations
```

Copy the newest bridge-backed Demo 04 result by first checking the timestamp on
Linux:

```bash
find /home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo04_external_setpoint \
  -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1
```

Then run `scp` from the Mac terminal with that timestamp:

```bash
scp -r <linux_user>@<linux_host>:/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo04_external_setpoint/<timestamp> ~/Desktop/px4_demo04_bridge_<timestamp>
```

Replace `<linux_user>` and `<linux_host>` with the SSH user and host for the
Linux machine. If SSH uses a non-default port, add `-P <port>` after `scp`.

## Current Missing Metrics

The current recorder covers position, velocity magnitude, target position,
tracking error, summary PASS/FAIL, and optional animation. It does not currently
plot or summarize:

- attitude, yaw, or yaw-rate tracking;
- acceleration or jerk;
- battery, estimator, actuator, or failsafe status;
- per-waypoint arrival time and dwell time;
- rosbag-based replay or offline redraw from a saved bag.
