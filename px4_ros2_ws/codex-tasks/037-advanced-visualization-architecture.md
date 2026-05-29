# Task 037: Advanced Visualization Architecture

## Task goal

- Convert `docs/ADVANCED_VISUALIZATION_PLAN.md` into a concrete artifact schema
  and source inventory for advanced project visualization.
- Do not generate heavy videos in this task; focus on stable contracts for later
  render tasks.

## Allowed changes

- `docs/ADVANCED_VISUALIZATION_PLAN.md`
- `docs/VISUALIZATION_GUIDE.md`
- `scripts/collect_visualization_sources.py`
- `visualizations/visualization_manifest.json`
- `codex-logs/037-advanced-visualization-architecture.log`

## Implementation requirements

- Add a source inventory script that detects the latest Demo 01-04, Demo 07, and
  Demo 10 evidence without overwriting timestamped outputs.
- Define `visualization_manifest.json` with:
  - generated timestamp;
  - source run paths;
  - artifact paths;
  - status per visualization layer;
  - missing data warnings;
  - file sizes for generated or selected artifacts.
- Keep paths relative to `/home/clcwork/UAV_capture/px4_ros2_ws`.
- Update the guide with the manifest location and regeneration command.

## Required commands

```bash
python3 -m py_compile scripts/collect_visualization_sources.py
python3 scripts/collect_visualization_sources.py | tee codex-logs/037-advanced-visualization-architecture.log
bash -n run_codex_queue.sh
```

## Deliverables

- `scripts/collect_visualization_sources.py`
- `visualizations/visualization_manifest.json`
- Updated advanced visualization documentation.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `manifest path`
- `known risks`
