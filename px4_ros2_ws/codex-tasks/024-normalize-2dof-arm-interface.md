# Task 024: Normalize 2-DOF Arm Interface

## Task goal

- Align all Stage 2 arm defaults with the actual `x500_arm_2dof` SDF model.
- Remove the current mismatch where the model exposes two joints but several high-level nodes default to three generic joints.
- Preserve the high-level `/arm/*` API and do not add new manipulation behavior.

## Allowed changes

- `src/aerial_manip_control/**`
- `src/aerial_manip_eval/**`
- `src/aerial_manip_policy/**`
- `docs/ARM_CONTROL_API.md`
- `docs/STAGE2_COORDINATOR.md`
- `docs/STAGE2_DATASET_SCHEMA.md`
- `docs/STAGE2_LEROBOT_POLICY.md`
- `codex-logs/024-normalize-2dof-arm-interface.log`

## Implementation requirements

- Use the canonical joint names from the SDF:
  - `arm_shoulder_pitch_joint`
  - `arm_elbow_pitch_joint`
- Update default joint vectors, limits, command validation, synthetic controller, coordinator, policy bridge schema, and docs to two joints.
- Keep compatibility with explicitly supplied `joint_names` parameters where practical.
- Update Demo 10 dry-run metrics/checks if they currently assume three joints.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control src/aerial_manip_eval src/aerial_manip_policy scripts/check_demo_10.py
colcon build --packages-select aerial_manip_msgs aerial_manip_control aerial_manip_eval aerial_manip_policy
DEMO10_MODE=dry-run bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

## Deliverables

- Consistent 2-DOF defaults across control, eval, policy, and documentation.
- A passing Demo 10 dry-run after the schema change.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

