# Task 033: Verify Live Arm Control and Demo 10 Smoke

## Task goal

- Verify live arm control launch behavior after the ros2_control dependencies are available.
- Confirm Demo 10 live-smoke can bring PX4/Gazebo to `Ready for takeoff` and cleanly shut down.
- Do not run the full Demo 10 live mission in this task.

## Allowed changes

- `scripts/run_regression_demo_10.sh`
- `docs/STAGE2_CONTROL_NOTES.md`
- `docs/STAGE2_AIR_REACH_DEMO.md`
- `codex-logs/033-verify-live-arm-control-and-demo10-smoke.log`

## Implementation requirements

- Validate `aerial_manip_control arm_control.launch.py` startup.
- Check that controller-related ROS packages and launch logs are consistent with the expected two-joint arm setup.
- Run Demo 10 in `live-smoke` mode with `RESET_STACK=1`.
- Ensure PX4/Gazebo/MicroXRCEAgent processes from this project are cleaned up before the task exits.
- If live-smoke fails, preserve stack readiness logs and identify the failing preflight or startup stage.

## Required commands

```bash
bash -n scripts/run_regression_demo_10.sh
timeout 60s ros2 launch aerial_manip_control arm_control.launch.py || true
DEMO10_MODE=live-smoke RESET_STACK=1 bash scripts/run_regression_demo_10.sh | tee codex-logs/033-verify-live-arm-control-and-demo10-smoke.log
scripts/stop_stack.sh
pgrep -af 'gz sim|px4|MicroXRCEAgent' || true
```

## Deliverables

- Live-smoke evidence under `logs/demo10_air_reach/<timestamp>/`.
- Updated docs if arm control or live-smoke behavior changed.
- Confirmation that no project PX4/Gazebo/MicroXRCEAgent process was left behind.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `live-smoke output path`
