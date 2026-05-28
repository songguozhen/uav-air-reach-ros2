# Stage 2 Control Notes

## Task 025 ros2_control Repair

Task: `025-repair-arm-ros2-control-integration`

The two-joint arm model now declares a minimal `gz_ros2_control` path:

- SDF joints:
  - `arm_shoulder_pitch_joint`
  - `arm_elbow_pitch_joint`
- Controller configuration:
  - `joint_state_broadcaster`
  - `arm_position_controller`
- Controller command topic:
  - `/arm_position_controller/commands`

The controller YAML is:

```text
src/aerial_manip_control/config/arm_controllers.yaml
```

The controller launch entry point is:

```bash
ros2 launch aerial_manip_control arm_control.launch.py
```

The SDF plugin is attached in:

```text
src/aerial_manip_gazebo/models/x500_arm_2dof/model.sdf
```

The model uses `gz_ros2_control/GazeboSimSystem` with position command
interfaces and position/velocity state interfaces for both arm joints. The
plugin loads:

```text
$(find aerial_manip_control)/config/arm_controllers.yaml
```

## Command Scope

This task does not add MoveIt 2 or trajectory planning. It also does not
publish to PX4 `/fmu/in/*` topics. Arm actuation remains isolated to the arm
controller path, and external modules should continue to use the high-level
`/arm/*` bridge by default.

For direct low-level controller smoke tests after Gazebo has loaded the model:

```bash
ros2 topic pub /arm_position_controller/commands std_msgs/msg/Float64MultiArray "{data: [0.2, -0.3]}" -1
```

## Missing Dependency Behavior

The launch file checks for these ROS 2 packages before starting controller
spawners:

```text
gz_ros2_control
controller_manager
joint_state_broadcaster
forward_command_controller
```

If any are missing, the launch file exits without starting spawners and prints a
clear line beginning with:

```text
WARN: arm ros2_control launch skipped
```

This keeps dry-run and non-live environments usable while documenting exactly
which live packages need to be installed.

## Live Verification Status

As of Task 033, the required live `ros2_control` ROS packages are available in
the sourced workspace environment:

```text
gz_ros2_control
controller_manager
joint_state_broadcaster
forward_command_controller
```

Running the controller launch with `source install/setup.bash` starts the
expected two spawners:

```text
joint_state_broadcaster
arm_position_controller
```

The standalone launch check then times out waiting for
`/controller_manager/list_controllers` when Gazebo has not loaded the
`x500_arm_2dof` model. That is expected for this isolated startup check; the
next live controller validation should run with the model loaded so the
`gz_ros2_control` plugin provides `/controller_manager`.
