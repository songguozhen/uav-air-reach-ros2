# Task 042: Integrate Advanced Visualization Showcase

## Task goal

- Integrate all advanced 3D, 2D, and MP4 artifacts into the simulation showcase
  and project status deliverables.
- Verify the advanced visualization package end to end.

## Allowed changes

- `scripts/generate_simulation_showcase.py`
- `scripts/check_stage2_evidence.py`
- `docs/VISUALIZATION_GUIDE.md`
- `docs/ADVANCED_VISUALIZATION_PLAN.md`
- `deliverables/simulation_showcase.html`
- `deliverables/status.html`
- `deliverables/project-audit.json`
- `deliverables/project-summary.md`
- `visualizations/visualization_manifest.json`
- `codex-logs/042-integrate-advanced-visualization-showcase.log`

## Implementation requirements

- Link these artifacts from `deliverables/simulation_showcase.html` when they
  exist:
  - Demo 10 advanced 3D replay HTML and MP4;
  - Demo 01-04 comparison 3D HTML/PNG/MP4;
  - 2D diagnostics dashboard and sheets;
  - video packaging summary;
  - `visualization_manifest.json`.
- Add visible PASS/WARN/MISSING labels for every advanced layer.
- Extend evidence checks so missing optional MP4 outputs are WARN and missing
  core HTML/manifest outputs are FAIL only after their corresponding task has
  been run.
- Keep `deliverables/status.html` as the status entry point and add a clear link
  to the advanced visualization section.
- Do not delete or rewrite historical timestamped visualizations.

## Required commands

```bash
python3 -m py_compile scripts/generate_simulation_showcase.py scripts/check_stage2_evidence.py
python3 scripts/generate_simulation_showcase.py | tee codex-logs/042-integrate-advanced-visualization-showcase.log
python3 -m compileall src scripts
bash -n run_codex_queue.sh
python3 scripts/check_stage2_evidence.py
```

## Deliverables

- Updated showcase with advanced visualization links.
- Refreshed project audit/status deliverables.
- Evidence check coverage for advanced visualization artifacts.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `showcase path`
- `advanced artifact status`
- `known risks`
