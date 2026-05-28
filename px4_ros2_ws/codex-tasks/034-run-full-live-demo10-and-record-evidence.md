# Task 034: Run Full Live Demo 10 and Record Evidence

## Task goal

- Run the full Demo 10 live mission after environment, camera, and live-smoke checks pass.
- Generate live task metrics and episode recorder evidence.
- Keep all control traffic on the existing high-level ROS interfaces.

## Allowed changes

- `scripts/run_regression_demo_10.sh`
- `scripts/check_demo_10.py`
- `docs/STAGE2_AIR_REACH_DEMO.md`
- `docs/REGRESSION_CHECKS.md`
- `codex-logs/034-run-full-live-demo10-and-record-evidence.log`

## Implementation requirements

- Use the current high-level interfaces:
  - `/uav/*`
  - `/arm/*`
  - `/system/observation`
  - `/vision/*`
  - `/approach`
- Do not add any external module that publishes directly to PX4 `/fmu/in/*`.
- Run `DEMO10_MODE=live` with `RESET_STACK=1`.
- Preserve these artifacts under the latest `logs/demo10_air_reach/<timestamp>/`:
  - `metrics.json`
  - `result.txt`
  - `sequence_events.jsonl`
  - `runner.log`
  - episode recorder output, when generated
- Always call `scripts/stop_stack.sh` before finishing.

## Required commands

```bash
DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh | tee codex-logs/034-run-full-live-demo10-and-record-evidence.log
python3 scripts/check_demo_10.py logs/demo10_air_reach
scripts/stop_stack.sh
```

## Deliverables

- Full live Demo 10 evidence directory under `logs/demo10_air_reach/<timestamp>/`.
- Updated regression and Demo 10 documentation if thresholds, runtime behavior, or evidence paths changed.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `live Demo 10 output path`
