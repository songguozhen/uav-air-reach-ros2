# Task 035: Generate Demo 10 Visualizations

## Task goal

- Convert the latest Demo 10 evidence into visual artifacts for presentation.
- Prefer the latest successful live run; use dry-run evidence only as an explicitly labeled fallback.
- Do not change Demo 10 control behavior in this task.

## Allowed changes

- `scripts/generate_demo10_visualizations.py`
- `docs/VISUALIZATION_GUIDE.md`
- `visualizations/demo10_air_reach/**`
- `codex-logs/035-generate-demo10-visualizations.log`

## Implementation requirements

- Add a script that can locate the latest successful live Demo 10 run or accept an explicit `--run-dir`.
- Read these inputs when present:
  - `logs/demo10_air_reach/<timestamp>/metrics.json`
  - `logs/demo10_air_reach/<timestamp>/sequence_events.jsonl`
  - episode recorder observations/actions/task status
- Generate these outputs under `visualizations/demo10_air_reach/<timestamp>/`:
  - `trajectory_3d.png`
  - `phase_timeline.png`
  - `flight_error.png`
  - `target_visibility.png`
  - `joint_positions.png`
  - `endpoint_error.png`
  - `summary.json`
- If live data is insufficient and dry-run is used, every generated summary must state `mode=dry-run fallback`.
- Keep plots readable for a project presentation: clear titles, axes, units, and PASS/WARN status labels.

## Required commands

```bash
python3 -m py_compile scripts/generate_demo10_visualizations.py
python3 scripts/generate_demo10_visualizations.py --latest-live | tee codex-logs/035-generate-demo10-visualizations.log
```

## Deliverables

- Demo 10 visualization script.
- Timestamped Demo 10 visualization directory.
- Updated visualization guide documenting inputs, outputs, and fallback behavior.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `visualization output path`
