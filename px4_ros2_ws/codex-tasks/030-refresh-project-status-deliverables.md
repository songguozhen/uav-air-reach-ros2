# Task 030: Refresh Project Status Deliverables

## Task goal

- Refresh the project and task status deliverables after Tasks 023-029.
- Keep the report truthful about dry-run, startup smoke, missing dependencies, and unverified live ros2_control/camera paths.
- Do not implement new runtime features in this task.

## Allowed changes

- `deliverables/project-audit.json`
- `deliverables/project-summary.md`
- `deliverables/task-status.json`
- `deliverables/task-summary.md`
- `deliverables/status.html`
- `codex-logs/030-refresh-project-status-deliverables.log`

## Implementation requirements

- Rebuild the task inventory from `codex-tasks/`, `codex-logs/`, and latest run artifacts.
- Summarize which tasks are completed, pending, blocked, or only dry-run validated.
- Include latest build/check commands and their outcomes.
- Clearly state live validation gaps:
  - missing ROS/Gazebo bridge or ros2_control packages, if still missing
  - live Demo 10 status
  - camera sample-frame status
  - LeRobot active Python vs conda environment status

## Required commands

```bash
python3 -m compileall src scripts
bash -n run_codex_queue.sh
DEMO10_MODE=dry-run bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

## Deliverables

- Fresh project audit JSON/Markdown.
- Fresh task status JSON/Markdown.
- Updated status dashboard if the existing dashboard generator is available.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
