# Task 016: Add State Aggregator and TF Baseline

## Task goal

- Create a single state aggregation boundary for UAV, arm, and later vision state.

## Allowed changes

- `src/aerial_manip_msgs/**`
- `src/aerial_manip_control/**`
- `docs/STAGE2_FRAMES_AND_STATE.md`
- `codex-logs/016-add-state-aggregator-and-tf-baseline.log`

## Implementation requirements

- Publish `/system/observation` and `/system/safety_status`.
- Broadcast or document the intended ROS TF tree: `map -> uav/base_link -> uav/arm_base -> uav/ee_link -> uav/camera_link`.
- Keep NED/ENU and FRD/FLU conversion logic centralized in this boundary or in the existing UAV bridge.
- Do not change `/uav/*` topic semantics.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control
colcon build --packages-select aerial_manip_msgs aerial_manip_control
ros2 run tf2_tools view_frames || true
```

## Deliverables

- State aggregator node or documented stub if runtime dependencies are missing.
- Frame/state documentation.
- Validation log.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
