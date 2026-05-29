# Task 041: Add Visualization Video Packaging

## Task goal

- Add a reusable packaging command that regenerates selected MP4 visualization
  clips from latest verified evidence.
- Keep video generation optional when `ffmpeg` or required source frames are not
  available.

## Allowed changes

- `scripts/package_visualization_videos.py`
- `docs/VISUALIZATION_GUIDE.md`
- `visualizations/**/frames/**`
- `visualizations/**/*.mp4`
- `visualizations/visualization_manifest.json`
- `codex-logs/041-add-visualization-video-packaging.log`

## Implementation requirements

- Add CLI options:
  - `--latest`;
  - `--demo10`;
  - `--flight-comparison`;
  - `--all`;
  - `--dry-run`.
- Detect `ffmpeg` and `ffprobe`; report WARN when unavailable.
- Generate or validate these MP4 outputs when source artifacts exist:
  - Demo 10 `advanced_replay.mp4`;
  - flight comparison `flight_comparison_3d.mp4`;
  - latest Demo 01-04 `trajectory.mp4`;
  - optional `diagnostics_overview.mp4` if dashboard frames are generated.
- Write a concise `video_packaging_summary.json` with codec, duration, size,
  source paths, and warnings.
- Update the manifest without deleting old clips.

## Required commands

```bash
python3 -m py_compile scripts/package_visualization_videos.py
python3 scripts/package_visualization_videos.py --dry-run --all
python3 scripts/package_visualization_videos.py --latest --all | tee codex-logs/041-add-visualization-video-packaging.log
python3 scripts/collect_visualization_sources.py
```

## Deliverables

- Reusable MP4 packaging script.
- Video packaging summary.
- Updated visualization manifest.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `mp4 outputs`
- `ffmpeg status`
- `known risks`
