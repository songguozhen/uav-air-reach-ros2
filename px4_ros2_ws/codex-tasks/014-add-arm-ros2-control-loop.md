# Task 014: Add Arm ros2_control Loop

## Task goal

- Wire the two arm joints into `ros2_control` through `gz_ros2_control`.

## Allowed changes

- `src/aerial_manip_gazebo/**`
- `src/aerial_manip_control/config/**`
- `src/aerial_manip_control/launch/**`
- `docs/STAGE2_CONTROL_NOTES.md`
- `codex-logs/014-add-arm-ros2-control-loop.log`

## Implementation requirements

- Start with `joint_state_broadcaster` and a simple forward or position command controller.
- Use controller names and joint names consistently across SDF, YAML, and launch files.
- Keep command limits conservative.

## Required commands

```bash
colcon build --packages-select aerial_manip_control aerial_manip_gazebo
ros2 control list_controllers || true
```

If simulation is available, publish a one-shot small joint command and verify `/joint_states` changes.

## Deliverables

- Controller YAML.
- Control launch entry point.
- Notes explaining the controller and joint naming.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
