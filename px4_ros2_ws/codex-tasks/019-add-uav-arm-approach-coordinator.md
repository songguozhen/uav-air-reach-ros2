# Task 019: Add UAV-Arm Approach Coordinator

## Task goal

- Implement a rule-based coordinator for coarse UAV positioning plus local arm adjustment.

## Allowed changes

- `src/aerial_manip_msgs/**`
- `src/aerial_manip_control/**`
- `docs/STAGE2_COORDINATOR.md`
- `codex-logs/019-add-uav-arm-approach-coordinator.log`

## Implementation requirements

- The coordinator may command only high-level `/uav/*` and `/arm/*` interfaces.
- Do not publish directly to PX4 `/fmu/in/*` topics.
- Add workspace thresholds, command rate limits, timeout handling, and a cancel/stop path.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control
colcon build --packages-select aerial_manip_msgs aerial_manip_control
ros2 action list || true
```

## Deliverables

- Coordinator node/action.
- Coordinator documentation with safety limits.
- Validation log.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
