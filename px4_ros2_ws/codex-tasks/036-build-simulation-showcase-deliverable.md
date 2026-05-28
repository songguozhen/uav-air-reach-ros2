# Task 036: Build Simulation Showcase Deliverable

## Task goal

- Generate a presentation-oriented HTML page that shows the current simulation effects end to end.
- Keep `deliverables/status.html` as the project status page and create a separate simulation showcase page.
- Refresh project evidence so the showcase links point to the latest verified artifacts.

## Allowed changes

- `scripts/generate_simulation_showcase.py`
- `deliverables/simulation_showcase.html`
- `deliverables/project-audit.json`
- `deliverables/project-summary.md`
- `deliverables/status.html`
- `docs/VISUALIZATION_GUIDE.md`
- `codex-logs/036-build-simulation-showcase-deliverable.log`

## Implementation requirements

- Build `deliverables/simulation_showcase.html` as a self-contained presentation page.
- Include these sections:
  - project simulation status
  - Demo 01-04 trajectory/video artifacts
  - Demo 07 camera sample frame or explicit capture failure
  - Demo 10 phase flow, trajectory, arm joints, flight error, target visibility, endpoint error
  - live/dry-run/fallback status
  - risks and next actions
- Add a clear link from `deliverables/status.html` to `deliverables/simulation_showcase.html`.
- Update audit/summary data so latest live Demo, camera frame, and visualization paths are represented truthfully.
- Do not delete or overwrite timestamped logs or visualization directories.

## Required commands

```bash
python3 -m py_compile scripts/generate_simulation_showcase.py
python3 scripts/generate_simulation_showcase.py | tee codex-logs/036-build-simulation-showcase-deliverable.log
python3 -m compileall src scripts
bash -n run_codex_queue.sh
python3 scripts/check_stage2_evidence.py
```

## Deliverables

- `deliverables/simulation_showcase.html`
- Refreshed project audit/summary files.
- Status page link to the new showcase page.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `showcase path`
