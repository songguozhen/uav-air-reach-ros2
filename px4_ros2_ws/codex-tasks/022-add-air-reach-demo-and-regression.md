# Task 022: Add Air Reach Demo and Regression

## Task goal

- Combine the stage-2 pieces into a repeatable "air reach" demo and PASS/FAIL regression.

## Allowed changes

- `src/aerial_manip_eval/**`
- `scripts/run_regression_demo_10.sh`
- `scripts/check_demo_10.py`
- `docs/REGRESSION_CHECKS.md`
- `docs/STAGE2_AIR_REACH_DEMO.md`
- `codex-logs/022-add-air-reach-demo-and-regression.log`

## Implementation requirements

- Demo sequence: stable hover, tag detection, coordinated approach, near-target endpoint hold or light contact if contact sensing exists.
- PASS/FAIL metrics must include flight error, joint limit violations, target visibility, task timeout, and final endpoint error.
- Preserve existing Demo 01-04 scripts and outputs.

## Required commands

```bash
bash -n scripts/run_regression_demo_10.sh
python3 -m py_compile scripts/check_demo_10.py
bash scripts/run_regression_demo_10.sh || true
```

## Deliverables

- Demo 10 launch/script/checker.
- Regression documentation.
- Timestamped logs and metrics if simulation is available.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `output paths`
