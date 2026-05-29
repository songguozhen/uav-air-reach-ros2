# Task 038: Build Demo 10 Advanced 3D Replay

## Task goal

- Add a richer Demo 10 3D replay with UAV path, arm endpoint, target, command
  path, phase markers, camera frustum, and safety/workspace overlays.
- Export a compact MP4 clip from the same source evidence when `ffmpeg` is
  available.

## Allowed changes

- `scripts/generate_demo10_advanced_replay.py`
- `docs/VISUALIZATION_GUIDE.md`
- `visualizations/demo10_air_reach/**`
- `visualizations/visualization_manifest.json`
- `codex-logs/038-build-demo10-advanced-3d-replay.log`

## Implementation requirements

- Prefer the latest successful live Demo 10 run. Accept `--run-dir` for an
  explicit source.
- Generate under `visualizations/demo10_air_reach/<timestamp>/advanced/`:
  - `advanced_replay.html`;
  - `advanced_replay.mp4` when `ffmpeg` is installed;
  - `frames/` only if needed for MP4 generation;
  - `advanced_replay_summary.json`.
- The HTML must be self-contained and viewable without a ROS environment.
- The 3D scene must include readable labels and a clear live/dry-run/fallback
  badge.
- If camera frustum or target-pose evidence is missing, create the replay with a
  WARN entry instead of failing.
- Update the manifest with generated paths, status, size, and warnings.

## Required commands

```bash
python3 -m py_compile scripts/generate_demo10_advanced_replay.py
python3 scripts/generate_demo10_advanced_replay.py --latest-live | tee codex-logs/038-build-demo10-advanced-3d-replay.log
python3 scripts/collect_visualization_sources.py
```

## Deliverables

- Advanced Demo 10 3D replay HTML.
- Optional Demo 10 MP4 clip.
- Updated visualization manifest.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `output path`
- `mp4 status`
- `known risks`
