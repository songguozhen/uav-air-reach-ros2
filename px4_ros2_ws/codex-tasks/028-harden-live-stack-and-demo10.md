# Task 028: Harden Live Stack and Demo 10

## Task goal

- Make the existing PX4/Gazebo startup and Demo 10 live path safer to rerun.
- Fix stale Gazebo/PX4 cleanup gaps before attempting longer live checks.
- Keep Demo 10 on the current high-level bridge, placeholder target, and synthetic arm path unless Task 025 has completed live ros2_control verification.

## Allowed changes

- `scripts/start_stack.sh`
- `scripts/stop_stack.sh`
- `scripts/run_regression_demo_10.sh`
- `scripts/check_demo_10.py`
- `docs/STAGE2_AIR_REACH_DEMO.md`
- `docs/REGRESSION_CHECKS.md`
- `codex-logs/028-harden-live-stack-and-demo10.log`

## Implementation requirements

- Ensure `stop_stack.sh` kills both known Gazebo command forms:
  - `gz sim ... Tools/simulation/gz/worlds/default.sdf`
  - `gz sim --verbose=1 -r -s ... default.sdf`
- Add a bounded live smoke mode that starts the stack, verifies PX4 reaches `Ready for takeoff` or records the exact preflight failure, then cleans up.
- Ensure every script path leaves no PX4/Gazebo/MicroXRCEAgent process behind except unrelated pre-existing tmux sessions.
- Keep default Demo 10 mode as dry-run or auto-dry-run unless live prerequisites pass.

## Required commands

```bash
bash -n scripts/start_stack.sh
bash -n scripts/stop_stack.sh
bash -n scripts/run_regression_demo_10.sh
DEMO10_MODE=dry-run bash scripts/run_regression_demo_10.sh
RESET_STACK=1 timeout 95s scripts/start_stack.sh || true
scripts/stop_stack.sh
pgrep -af 'gz sim|px4|MicroXRCEAgent' || true
```

## Deliverables

- Hardened startup/cleanup scripts.
- A Demo 10 live-readiness result recorded in logs or docs.
- No leftover PX4/Gazebo/MicroXRCEAgent process after validation.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

