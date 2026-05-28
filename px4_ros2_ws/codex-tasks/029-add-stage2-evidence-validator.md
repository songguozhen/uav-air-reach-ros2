# Task 029: Add Stage 2 Evidence Validator

## Task goal

- Add one validator for Stage 2 run evidence so completed tasks are judged by artifacts, not only by `.done` markers.
- Keep validation focused on the current Task 010-020 layout.
- Do not add new demos or policy training behavior.

## Allowed changes

- `scripts/check_stage2_evidence.py`
- `docs/REGRESSION_CHECKS.md`
- `docs/STAGE2_DATASET_SCHEMA.md`
- `deliverables/task-status.json`
- `deliverables/task-summary.md`
- `codex-logs/029-add-stage2-evidence-validator.log`

## Implementation requirements

- Check for the latest Demo 10 `metrics.json`, `result.txt`, `sequence_events.jsonl`, and PASS result.
- Check required Stage 2 docs exist for frames, control, vision, dataset, policy, coordinator, and Demo 10.
- Check task logs and `.done` markers for Task 012-022 and report any mismatch.
- Report dry-run vs live validation separately.
- Write a machine-readable JSON result under `deliverables/`.

## Required commands

```bash
python3 -m py_compile scripts/check_stage2_evidence.py
python3 scripts/check_stage2_evidence.py
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

## Deliverables

- Evidence validator script.
- Updated regression/data docs.
- Updated task status artifacts based on evidence.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

