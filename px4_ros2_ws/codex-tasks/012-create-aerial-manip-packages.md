# Task 012: Create Aerial Manipulation Package Skeleton

## Task goal

- Add the ROS 2 package skeleton for stage-2 aerial manipulation without implementing simulation behavior yet.

## Allowed changes

- `src/aerial_manip_msgs/**`
- `src/aerial_manip_gazebo/**`
- `src/aerial_manip_control/**`
- `src/aerial_manip_vision/**`
- `src/aerial_manip_policy/**`
- `src/aerial_manip_eval/**`
- `docs/STAGE2_PACKAGE_STRUCTURE.md`
- `codex-logs/012-create-aerial-manip-packages.log`

## Implementation requirements

- Use `ament_cmake` for `aerial_manip_msgs`.
- Use `ament_python` for Python node packages unless a package only installs launch/config/model assets.
- Define only minimal interfaces needed by later tasks: platform state, arm command/state, system observation, task status, and approach action.
- Keep existing `px4_offboard_hover` untouched except for package dependencies if strictly required.

## Required commands

```bash
colcon build --packages-select aerial_manip_msgs
python3 -m compileall src/aerial_manip_control src/aerial_manip_vision src/aerial_manip_policy src/aerial_manip_eval
```

## Deliverables

- New packages under `src/`.
- Interface package builds successfully.
- Package structure documentation.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
