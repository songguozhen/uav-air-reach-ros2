# Task 023: Stage 2 Environment Preflight

## Task goal

- Turn the current Stage 2 dependency warnings into a repeatable preflight check before running aerial manipulation tasks.
- Do not install system packages in this task unless the user explicitly approves it.
- Keep the output focused on whether the existing Task 012-022 stack can run live or only dry-run.

## Allowed changes

- `scripts/check_stage2_environment.sh`
- `docs/STAGE2_ENVIRONMENT_AUDIT.md`
- `docs/STAGE2_RUNBOOK.md`
- `codex-logs/023-stage2-environment-preflight.log`

## Implementation requirements

- Check ROS 2 Jazzy, Gazebo Sim, PX4 SITL binary/model assets, MicroXRCEAgent, `ros_gz_bridge`, `gz_ros2_control`, `controller_manager`, `joint_state_broadcaster`, `forward_command_controller`, and `joint_trajectory_controller`.
- Check LeRobot in both the active Python and `/home/clcwork/miniconda3/envs/lerobot/bin/python`.
- Report `PASS`, `WARN`, or `FAIL` with exact missing package names and commands to recheck.
- Do not change runtime code or package manifests except documentation/runbook references.

## Required commands

```bash
bash -n scripts/check_stage2_environment.sh
bash scripts/check_stage2_environment.sh | tee codex-logs/023-stage2-environment-preflight.log
```

## Deliverables

- A reusable environment preflight script.
- Updated environment audit with current live-readiness status.
- A concise runbook section that explains when Demo 10 must stay in dry-run mode.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

