# Task 026: Add Frame and Schema Regression

## Task goal

- Add deterministic checks for the two highest-risk foundations: frame conversion and message/schema consistency.
- Keep the checks lightweight and runnable without PX4/Gazebo.
- Do not change UAV `/uav/*` semantics.

## Allowed changes

- `src/aerial_manip_control/**`
- `src/aerial_manip_eval/**`
- `scripts/check_stage2_schema.py`
- `docs/STAGE2_FRAMES_AND_STATE.md`
- `docs/REGRESSION_CHECKS.md`
- `codex-logs/026-add-frame-and-schema-regression.log`

## Implementation requirements

- Validate known NED to ENU conversions and round-trip assumptions documented for `state_aggregator`.
- Validate canonical frame names:
  - `map`
  - `uav/base_link`
  - `uav/arm_base`
  - `uav/ee_link`
  - `uav/camera_link`
- Validate canonical arm joint names and vector lengths against the 2-DOF schema.
- Emit a machine-readable report such as `logs/demo_06_state_agg/<timestamp>/tf_report.json` or a clearly documented equivalent.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control src/aerial_manip_eval scripts/check_stage2_schema.py
python3 scripts/check_stage2_schema.py
colcon build --packages-select aerial_manip_msgs aerial_manip_control aerial_manip_eval
```

## Deliverables

- A frame/schema regression checker.
- Updated docs explaining exactly which conversions and names are enforced.
- A generated JSON report from the checker.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

