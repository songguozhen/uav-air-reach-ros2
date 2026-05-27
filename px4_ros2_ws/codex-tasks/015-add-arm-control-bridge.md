# Task 015: Add arm_control_bridge

## Task goal

- Add a high-level arm bridge so external modules do not publish directly to low-level controller command topics.

## Allowed changes

- `src/aerial_manip_msgs/**`
- `src/aerial_manip_control/**`
- `docs/ARM_CONTROL_API.md`
- `codex-logs/015-add-arm-control-bridge.log`

## Implementation requirements

- Provide high-level topics for target joints, current joint state, control state, and reached target.
- Add joint limit, velocity limit, command timeout, and target jump checks.
- Match the style and safety posture of `px4_offboard_hover/uav_control_bridge.py`.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control
colcon build --packages-select aerial_manip_msgs aerial_manip_control
```

## Deliverables

- `arm_control_bridge` node.
- API documentation for `/arm/*`.
- Validation log.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
