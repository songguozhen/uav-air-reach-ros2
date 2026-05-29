# Task 040: Add 2D Diagnostics Dashboard

## Task goal

- Add 2D auxiliary visualization that explains the advanced 3D outputs with
  synchronized diagnostics and static poster sheets.

## Allowed changes

- `scripts/generate_visual_diagnostics_dashboard.py`
- `docs/VISUALIZATION_GUIDE.md`
- `visualizations/diagnostics/**`
- `visualizations/demo10_air_reach/**`
- `visualizations/visualization_manifest.json`
- `codex-logs/040-add-2d-diagnostics-dashboard.log`

## Implementation requirements

- Use the latest successful Demo 10 visualizations and episode evidence.
- Generate:
  - `visualizations/diagnostics/<timestamp>/diagnostics_dashboard.html`;
  - `visualizations/diagnostics/<timestamp>/overview_sheet.png`;
  - `visualizations/diagnostics/<timestamp>/metrics_sheet.png`;
  - `visualizations/diagnostics/<timestamp>/diagnostics_summary.json`.
- Include 2D panels for phase timeline, XY path, altitude, speed, flight error,
  target visibility, joint positions, endpoint error, and final task status.
- Use existing generated PNGs when available; redraw from JSONL or CSV when
  needed.
- Mark missing streams as WARN while keeping the dashboard usable.
- Update the manifest with dashboard and poster-sheet paths.

## Required commands

```bash
python3 -m py_compile scripts/generate_visual_diagnostics_dashboard.py
python3 scripts/generate_visual_diagnostics_dashboard.py | tee codex-logs/040-add-2d-diagnostics-dashboard.log
python3 scripts/collect_visualization_sources.py
```

## Deliverables

- 2D diagnostics dashboard.
- Static overview and metrics sheets.
- Updated visualization manifest.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `dashboard path`
- `sheet paths`
- `known risks`
