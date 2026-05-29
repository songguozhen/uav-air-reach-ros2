# Task 039: Build Flight Comparison 3D Visuals

## Task goal

- Build a comparative 3D visualization for Demo 01-04 trajectories.
- Generate short MP4 clips for the comparison and for any demo whose latest
  timestamped output lacks `trajectory.mp4`.

## Allowed changes

- `scripts/generate_flight_comparison_3d.py`
- `docs/VISUALIZATION_GUIDE.md`
- `visualizations/flight_comparison/**`
- `visualizations/demo01_hover/**`
- `visualizations/demo02_waypoint_flight/**`
- `visualizations/demo03_circle_trajectory/**`
- `visualizations/demo04_external_setpoint/**`
- `visualizations/visualization_manifest.json`
- `codex-logs/039-build-flight-comparison-3d-visuals.log`

## Implementation requirements

- Read the latest Demo 01-04 `trajectory.csv` files and result summaries.
- Generate:
  - `visualizations/flight_comparison/<timestamp>/flight_comparison_3d.html`;
  - `visualizations/flight_comparison/<timestamp>/flight_comparison_3d.png`;
  - `visualizations/flight_comparison/<timestamp>/flight_comparison_3d.mp4`
    when `ffmpeg` is available;
  - missing-video MP4 clips for Demo 01-04 latest outputs when source data is
    sufficient.
- Show actual path, target path when present, start/end markers, altitude
  profile, and PASS/WARN result labels.
- Keep generated comparison videos under 80 MB each unless explicitly justified
  in the summary.
- Update the manifest with paths and warnings.

## Required commands

```bash
python3 -m py_compile scripts/generate_flight_comparison_3d.py
python3 scripts/generate_flight_comparison_3d.py | tee codex-logs/039-build-flight-comparison-3d-visuals.log
python3 scripts/collect_visualization_sources.py
```

## Deliverables

- 3D flight comparison HTML/PNG.
- MP4 comparison clip when available.
- Backfilled Demo 01-04 MP4 clips where needed.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `comparison path`
- `mp4 outputs`
- `known risks`
