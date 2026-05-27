# Task 013: Add x500_arm_2dof Model

## Task goal

- Create a minimal `x500_arm_2dof` Gazebo model that reuses the official PX4 `x500` base and adds a lightweight two-joint arm.

## Allowed changes

- `src/aerial_manip_gazebo/**`
- `docs/STAGE2_MODELING_NOTES.md`
- `codex-logs/013-add-x500-arm-2dof-model.log`

## Implementation requirements

- Follow the local `x500_mono_cam` include-merge pattern from `references/stage2/local_px4_models/x500_mono_cam/model.sdf`.
- Add conservative link mass, inertia, collision geometry, joint limits, and damping.
- Do not edit PX4-Autopilot model files.
- Provide a launch or script entry point that attempts to load the model in Gazebo.

## Required commands

```bash
test -s src/aerial_manip_gazebo/models/x500_arm_2dof/model.sdf
test -s src/aerial_manip_gazebo/models/x500_arm_2dof/model.config
python3 -m compileall src/aerial_manip_gazebo || true
```

Run a Gazebo load smoke test if the environment audit shows Gazebo is usable.

## Deliverables

- `x500_arm_2dof` model.
- Modeling notes with mass/inertia assumptions.
- Smoke-test log.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
