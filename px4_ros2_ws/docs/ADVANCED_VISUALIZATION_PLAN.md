# Advanced Visualization Plan

This plan extends the current Demo 01-04, Demo 07, and Demo 10 visualization
outputs into a presentation-grade visualization pipeline. It keeps generated
artifacts under timestamped `visualizations/<demo>/<timestamp>/` directories and
does not overwrite historical logs or evidence.

## Goals

- Show the UAV, arm, target, camera, command path, and safety envelopes in a
  richer 3D replay.
- Add 2D diagnostic panels that explain the 3D motion with timelines, error
  bands, waypoint tables, visibility, and control-mode state.
- Generate compact MP4 clips for presentation and review without requiring a
  browser or ROS environment.
- Keep every generated artifact tied to its source run directory, metrics file,
  and PASS/WARN status.

## Visualization Layers

| Layer | Output | Purpose | Source evidence |
| --- | --- | --- | --- |
| 3D mission replay | `advanced_replay.html`, `advanced_replay.mp4` | UAV path, arm endpoint, tag target, command setpoints, phase markers, keep-in volume, and camera frustum. | Demo 10 episode observations/actions, metrics, sequence events. |
| 3D comparative flight board | `flight_comparison_3d.html`, `flight_comparison_3d.mp4` | Compare Demo 01-04 paths, start/end points, altitude changes, and tracking envelopes in one scene. | Demo 01-04 `trajectory.csv` and `result.txt`. |
| 3D workspace and reach view | `workspace_reach_3d.html`, `workspace_reach_3d.mp4` | Show arm reach shell, endpoint path, target pose, joint-limit bands, and final error. | Demo 10 observations/actions and model metadata. |
| 2D assist dashboard | `diagnostics_dashboard.html` | Synchronized phase timeline, tracking error, target visibility, joint positions, endpoint error, and task status. | Existing Demo 10 metrics, JSONL streams, and generated PNGs. |
| 2D poster sheets | `overview_sheet.png`, `metrics_sheet.png` | Static images suitable for slides and offline reports. | Latest verified visualization artifacts. |
| Evidence index | `visualization_manifest.json` | Machine-readable artifact list, source paths, status, warnings, and hashes/sizes. | Generated artifacts and source run metadata. |

## Artifact Schema And Output Roots

Task 037 fixes the source and output contract before any heavy render work:

- Source inventory script: `scripts/collect_visualization_sources.py`
- Generated manifest: `visualizations/visualization_manifest.json`
- Regeneration command: `python3 scripts/collect_visualization_sources.py`
- Path rule: all paths stored in the manifest are relative to
  `/home/clcwork/UAV_capture/px4_ros2_ws`

The manifest uses this schema:

| Field | Meaning |
| --- | --- |
| `schema_version` | Manifest contract version for later render tasks. |
| `generated_at` | Local timestamp for the manifest write. |
| `manifest_path` | Relative path to `visualizations/visualization_manifest.json`. |
| `source_runs` | Latest detected Demo 01-04, Demo 07, Demo 10 run directories and selected evidence files. |
| `visualization_layers` | Per-layer readiness, selected source artifacts, planned output paths, and warnings. |
| `missing_data_warnings` | Flattened warning list for missing required or optional evidence. |

Planned output roots are now fixed as:

| Layer | Planned output root |
| --- | --- |
| Demo 10 advanced replay | `visualizations/demo10_air_reach/<timestamp>/` |
| Demo 10 workspace reach | `visualizations/demo10_air_reach/<timestamp>/` |
| Demo 10 diagnostics dashboard | `visualizations/demo10_air_reach/<timestamp>/` |
| Demo 10 poster sheets | `visualizations/demo10_air_reach/<timestamp>/` |
| Demo 01-04 comparison board | `visualizations/demo01_04_comparison/<timestamp>/` |
| Evidence index | `visualizations/` |

Each layer entry in the manifest contains:

- `status`: `GENERATED`, `READY`, `PARTIAL`, or `MISSING`
- `source_run_paths`: latest run or visualization directories selected for that layer
- `selected_artifacts`: current evidence files with relative path, existence, and `size_bytes`
- `artifact_paths`: planned output files for later render tasks
- `missing_data_warnings`: layer-local gaps that later tasks must handle or annotate

## 3D Content Requirements

- Use a stable NED-to-display transform and label axes clearly as north, east,
  and altitude.
- Render actual UAV trajectory, commanded target trajectory, arm endpoint path,
  target position, phase transitions, and start/end markers.
- Include camera frustum and target line-of-sight when camera or target-pose
  evidence is available; otherwise show a WARN annotation in the manifest.
- Include configurable keep-in volume and reach radius shells. These should be
  visual aids only, not new control constraints.
- Add playback controls, speed control, frame scrubber, and current metric
  readout in HTML outputs.
- MP4 exports should be deterministic from the same source data and should not
  need a live simulator.

## 2D Assist Requirements

- Add synchronized 2D panels below or beside the 3D replay:
  - phase timeline and task status;
  - XY top-down path with target and command overlays;
  - altitude, speed, and tracking error;
  - joint positions with limit bands;
  - target visibility and endpoint error;
  - final PASS/WARN table with source artifact links.
- Static sheets should use readable labels, units, and explicit live/dry-run
  status.
- Missing data should produce a WARN panel instead of failing the full package
  unless the required source run is missing entirely.

## MP4 Generation Policy

- Generate short clips first: 10-30 seconds at 24 or 30 fps.
- Prefer `ffmpeg` for assembling frames. Use browser-based capture only for
  interactive Three.js scenes that cannot be reproduced by Matplotlib.
- Use H.264 MP4 defaults compatible with common slide software:

```bash
ffmpeg -y -framerate 30 -i frames/frame_%05d.png \
  -pix_fmt yuv420p -c:v libx264 -crf 22 advanced_replay.mp4
```

- Store intermediate frames under the same timestamped visualization directory,
  for example `visualizations/demo10_air_reach/<timestamp>/frames/`.
- Keep MP4 size reasonable for review. The target is under 80 MB per clip unless
  a task explicitly documents why a larger video is needed.

## Generation Sequence

1. Inventory current visualization evidence and define a manifest schema.
2. Build the advanced 3D replay for Demo 10 and export its HTML plus MP4.
3. Build 3D comparative views for Demo 01-04 trajectories.
4. Add 2D synchronized diagnostic dashboards and poster sheets.
5. Add a video packaging command that regenerates selected MP4 outputs from the
   latest verified evidence.
6. Refresh the simulation showcase so it links to the advanced artifacts and
   clearly marks missing or fallback evidence.

## Task Queue Additions

The detailed implementation work is queued as:

| Task | Title | Primary deliverable |
| --- | --- | --- |
| 037 | Advanced visualization architecture and manifest | Plan-backed schema and source inventory. |
| 038 | Demo 10 advanced 3D replay and MP4 | `advanced_replay.html`, `advanced_replay.mp4`. |
| 039 | Demo 01-04 3D comparison and MP4 clips | Comparative 3D board and videos. |
| 040 | 2D diagnostic dashboard and poster sheets | Synchronized dashboard and static sheets. |
| 041 | Visualization video packaging pipeline | Reusable MP4 generation script and manifest updates. |
| 042 | Showcase integration and verification | Updated showcase, guide, and evidence checks. |

Run the new queue range with:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./run_codex_queue.sh --from 037
```

Use dry-run first to inspect the task order:

```bash
./run_codex_queue.sh --dry-run --from 037
```

## Validation

- `python3 -m compileall src scripts`
- `bash -n run_codex_queue.sh`
- `python3 scripts/check_stage2_evidence.py`
- For generated HTML, verify the page is non-empty and links resolve relative
  to `px4_ros2_ws`.
- For MP4, verify `ffprobe` reports duration, codec, frame size, and frame count
  when `ffprobe` is available.

## Showcase Integration Policy

Task 042 promotes the advanced visualization outputs into the reader-facing
deliverables:

- `deliverables/status.html` remains the top-level entry page.
- `deliverables/simulation_showcase.html#advanced-visualizations` is the
  dedicated advanced section.
- `visualizations/visualization_manifest.json` and
  `visualizations/video_packaging_summary.json` must be linked directly from the
  showcase when present.

Evidence checks follow these rules:

- Missing optional MP4 files are reported as `WARN`.
- Missing core HTML or manifest-style outputs become `FAIL` only after the
  corresponding queued task has already been run.
- Historical timestamped visualization directories are never rewritten or
  deleted during showcase refresh work.
