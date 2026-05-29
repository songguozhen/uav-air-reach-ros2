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

## Demo 10 Advanced 3D Replay

Generate the richer 3D replay from the same Demo 10 evidence:

```bash
python3 scripts/generate_demo10_advanced_replay.py --latest-live
```

To render a specific run directory:

```bash
python3 scripts/generate_demo10_advanced_replay.py \
  --run-dir logs/demo10_air_reach/<timestamp>
```

The script prefers the latest successful live run with episode data and falls
back to successful dry-run evidence only when no suitable live run is present.
It writes a self-contained replay under:

```text
visualizations/demo10_air_reach/<timestamp>/advanced/
```

Generated files:

| File | Purpose |
| --- | --- |
| `advanced_replay.html` | Standalone 3D replay page with UAV path, arm endpoint, target trail, command path, phase markers, safety/workspace boxes, and camera frustum overlay. |
| `advanced_replay_summary.json` | Machine-readable status, source paths, badge, warning list, metrics, and output inventory. |
| `advanced_replay.mp4` | Optional compact clip from the same evidence when `ffmpeg` is installed. |
| `frames/` | Temporary rendered frame set kept only when MP4 export is attempted. |

The replay page does not require ROS to view it. A clear badge marks
`LIVE PASS`, `LIVE WARN`, or `DRY-RUN FALLBACK`. Missing camera-frustum or
target-pose evidence is recorded as `WARN` in the summary instead of failing
generation.

## Demo 10 2D Diagnostics Dashboard

Generate the auxiliary 2D dashboard and poster sheets from the latest
successful live Demo 10 evidence:

```bash
python3 scripts/generate_visual_diagnostics_dashboard.py
```

The script selects the newest `mode=live` and `RESULT=PASS` run with episode
observations and actions, reuses existing Demo 10 PNGs when present, and
redraws the remaining panels from JSONL evidence. Outputs are written to:

```text
visualizations/diagnostics/<timestamp>/
```

Generated files:

| File | Purpose |
| --- | --- |
| `diagnostics_dashboard.html` | Self-contained 2D dashboard with phase timeline, XY path, altitude, speed, flight error, target visibility, joint positions, endpoint error, and final task status. |
| `overview_sheet.png` | Static poster sheet focused on trajectory, sequence timing, and XY motion. |
| `metrics_sheet.png` | Static poster sheet focused on altitude, speed, and the main tracking and endpoint metrics. |
| `diagnostics_summary.json` | Machine-readable source paths, panel readiness, warnings, and output inventory. |

The HTML dashboard reuses these Demo 10 presentation plots from
`visualizations/demo10_air_reach/<source_timestamp>/` when available:
`phase_timeline.png`, `flight_error.png`, `target_visibility.png`,
`joint_positions.png`, and `endpoint_error.png`. Missing streams remain usable
through `WARN` placeholders instead of failing generation.

## Advanced Visualization Plan

The next visualization stage is documented in
`docs/ADVANCED_VISUALIZATION_PLAN.md`. It adds a queued plan for richer 3D
replays, 2D diagnostic dashboards, static poster sheets, and presentation MP4
clips while preserving all existing timestamped evidence directories.

The planned advanced outputs include:

| Output | Purpose |
| --- | --- |
| `advanced/advanced_replay.html` / `advanced/advanced_replay.mp4` | Demo 10 UAV, arm, target, command path, phase markers, camera frustum, and workspace overlays. |
| `flight_comparison_3d.html` / `flight_comparison_3d.mp4` | Combined Demo 01-04 3D trajectory comparison. |
| `diagnostics_dashboard.html` | 2D synchronized assist view for phase, path, errors, visibility, joints, and task status. |
| `overview_sheet.png`, `metrics_sheet.png` | Static slide/report images. |
| `visualization_manifest.json` | Machine-readable source and artifact inventory. |

## Demo 01-04 Flight Comparison 3D

Generate the latest comparative 3D board from the newest Demo 01-04
timestamped trajectories:

```bash
python3 scripts/generate_flight_comparison_3d.py
```

The script writes a new output directory:

```text
visualizations/flight_comparison/<timestamp>/
```

Generated files:

| File | Purpose |
| --- | --- |
| `flight_comparison_3d.html` | Self-contained comparison page with the rendered board and per-demo metrics cards. |
| `flight_comparison_3d.png` | Static comparison board with a shared 3D NED path view and altitude profile panel. |
| `flight_comparison_3d.mp4` | Optional compact rotating 3D clip when `ffmpeg` is installed. |
| `summary.json` | Machine-readable source runs, artifact paths, and warnings. |

The comparison board reads the latest `trajectory.csv`, `summary.md`, and
`result.txt` from Demo 01-04. Solid lines show actual trajectories, dashed
lines show target paths when present, circle markers show starts, X markers
show endpoints, and the altitude panel uses `-z` so positive values represent
height above the local PX4 NED origin.

If the latest Demo 01-04 directories already contain `trajectory.mp4`, the
script leaves them unchanged. When a latest run is missing its MP4 and source
data is sufficient, the task workflow may backfill the clip in that same
timestamped directory.

The implementation tasks are queued as `codex-tasks/037` through
`codex-tasks/042`. Inspect the order without running work:

```bash
./run_codex_queue.sh --dry-run --from 037
```

Run the new advanced visualization queue:

```bash
./run_codex_queue.sh --from 037
```

Task 037 also fixes the machine-readable evidence manifest at:

```text
visualizations/visualization_manifest.json
```

Regenerate it from the workspace root with:

```bash
python3 scripts/collect_visualization_sources.py
python3 scripts/generate_simulation_showcase.py
```

## Showcase And Status Entry Points

The main entry point for readers is:

```text
deliverables/status.html
```

From there, jump into the advanced visualization section of:

```text
deliverables/simulation_showcase.html#advanced-visualizations
```

The showcase integrates these advanced layers when present and labels each one
with `PASS`, `WARN`, or `MISSING`:

| Layer | Expected links |
| --- | --- |
| Demo 10 advanced replay | `advanced_replay.html`, `advanced_replay_summary.json`, optional `advanced_replay.mp4` |
| Demo 01-04 comparison | `flight_comparison_3d.html`, `flight_comparison_3d.png`, optional `flight_comparison_3d.mp4`, `summary.json` |
| 2D diagnostics | `diagnostics_dashboard.html`, `overview_sheet.png`, `metrics_sheet.png`, `diagnostics_summary.json`, optional `diagnostics_overview.mp4` |
| Video packaging | `visualizations/video_packaging_summary.json` |
| Evidence manifest | `visualizations/visualization_manifest.json` |

`PASS` means all expected core artifacts are present. `WARN` means the layer is
usable but has optional gaps such as missing MP4 packaging. `MISSING` means the
core HTML or manifest-style output for that layer is absent.

The manifest records the latest Demo 01-04, Demo 07, Demo 10 source evidence,
planned advanced artifact paths, per-layer readiness, missing-data warnings,
and file sizes for the selected source artifacts.

## Package Visualization Videos

Use the packaging helper to regenerate or validate reusable MP4 clips from the
latest verified visualization evidence without rerunning PX4 or Gazebo:

```bash
python3 scripts/package_visualization_videos.py --dry-run --all
python3 scripts/package_visualization_videos.py --latest --all
```

Supported selectors:

| Option | Scope |
| --- | --- |
| `--latest` | Latest PASS Demo 01-04 `trajectory.mp4` clips from `trajectory.csv`. |
| `--demo10` | Demo 10 `advanced/advanced_replay.mp4` and optional diagnostics `diagnostics_overview.mp4`. |
| `--flight-comparison` | Latest `flight_comparison_3d.mp4` under `visualizations/flight_comparison/<timestamp>/`. |
| `--all` | Equivalent to `--latest --demo10 --flight-comparison`. |
| `--dry-run` | Report planned actions and warnings without writing files. |

The packaging script checks `ffmpeg` and `ffprobe` first. When either tool is
missing, it reports `WARN` instead of failing the run:

- missing `ffmpeg`: generation is skipped and any existing MP4 is only
  validated by file presence;
- missing `ffprobe`: codec and duration fields are left empty in the generated
  summary.

Generated metadata files:

| File | Purpose |
| --- | --- |
| `visualizations/video_packaging_summary.json` | Concise per-target packaging summary with codec, duration, file size, source paths, and warnings. |
| `visualizations/visualization_manifest.json` | Existing manifest plus the latest `video_packaging` section. |

Expected MP4 targets when source artifacts exist:

| Output | Source evidence |
| --- | --- |
| `visualizations/demo10_air_reach/<timestamp>/advanced/advanced_replay.mp4` | Demo 10 PNG panels and `advanced_replay_summary.json`. |
| `visualizations/flight_comparison/<timestamp>/flight_comparison_3d.mp4` | Latest `flight_comparison_3d.png` and `summary.json`. |
| `visualizations/demo0x_*/<timestamp>/trajectory.mp4` | Latest PASS `trajectory.csv`, `summary.md`, and `result.txt`. |
| `visualizations/diagnostics/<timestamp>/diagnostics_overview.mp4` | Optional diagnostics poster sheets when they exist. |

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
