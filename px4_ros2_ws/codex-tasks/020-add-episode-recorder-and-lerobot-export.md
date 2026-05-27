# Task 020: Add Episode Recorder and LeRobot Export

## Task goal

- Record stage-2 episodes as both ROS evidence and LeRobot-ready learning data.

## Allowed changes

- `src/aerial_manip_policy/**`
- `src/aerial_manip_eval/**`
- `tools/export_to_lerobot.py`
- `docs/STAGE2_DATASET_SCHEMA.md`
- `codex-logs/020-add-episode-recorder-and-lerobot-export.log`

## Implementation requirements

- Record `/system/observation`, image topics, high-level actions, task labels, and result status.
- Keep raw evidence under `logs/<demo>/<timestamp>/`.
- Export learning data under `datasets/air_reach_v1/`.
- Do not require LeRobot import for basic recorder tests; fail gracefully if the package is missing.

## Required commands

```bash
python3 -m compileall src/aerial_manip_policy src/aerial_manip_eval tools
python3 tools/export_to_lerobot.py --help || true
```

## Deliverables

- Episode recorder.
- LeRobot export script.
- Dataset schema documentation.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
