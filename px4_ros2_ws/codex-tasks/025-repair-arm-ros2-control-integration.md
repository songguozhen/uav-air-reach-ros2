# Task 025: Repair Arm ros2_control Integration

## Task goal

- Complete the standard `ros2_control`/`gz_ros2_control` path promised by Task 014.
- Keep the first controller setup minimal: joint state broadcaster plus a simple forward/position command controller.
- Do not introduce MoveIt 2 or trajectory planning in this task.

## Allowed changes

- `src/aerial_manip_gazebo/models/x500_arm_2dof/**`
- `src/aerial_manip_control/config/**`
- `src/aerial_manip_control/launch/**`
- `src/aerial_manip_control/package.xml`
- `src/aerial_manip_gazebo/package.xml`
- `docs/STAGE2_CONTROL_NOTES.md`
- `codex-logs/025-repair-arm-ros2-control-integration.log`

## Implementation requirements

- Add controller YAML for:
  - `joint_state_broadcaster`
  - `arm_position_controller` or equivalent `forward_command_controller`
- Add a launch entry point that starts controller manager/spawners when the required packages are available.
- Add or document the `gz_ros2_control` SDF plugin block for the two SDF joints.
- Fail gracefully with a clear `WARN` if required ROS 2 control packages are missing.
- Do not publish directly to PX4 `/fmu/in/*`.

## Required commands

```bash
python3 -m compileall src/aerial_manip_control
colcon build --packages-select aerial_manip_control aerial_manip_gazebo
ros2 pkg list | grep -E 'gz_ros2_control|controller_manager|joint_state_broadcaster|forward_command_controller' || true
ros2 control list_controllers || true
```

If the required packages are installed:

```bash
ros2 launch aerial_manip_control arm_control.launch.py
ros2 topic pub /arm_position_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.2, -0.3]}" -1
```

## Deliverables

- Controller configuration.
- Controller launch file.
- Documentation of live verification status and missing dependency behavior.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

