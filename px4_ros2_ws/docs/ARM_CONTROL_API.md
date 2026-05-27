# Arm Control API

`arm_control_bridge` is the high-level joint command gate for the simplified
UAV arm. External modules should publish desired joint targets to `/arm/*`
topics and must not publish directly to low-level controller command topics.

## Node

```bash
ros2 run aerial_manip_control arm_control_bridge
```

## High-level topics

| Topic | Direction | Type | Purpose |
| --- | --- | --- | --- |
| `/arm/target_joints` | subscribe | `aerial_manip_msgs/msg/ArmCommand` | Validated high-level joint target input. |
| `/arm/current_joint_state` | publish | `aerial_manip_msgs/msg/ArmState` | Current joint state normalized to configured joint order. |
| `/arm/current_target` | publish | `aerial_manip_msgs/msg/ArmState` | Last accepted safe joint target. |
| `/arm/reached_target` | publish | `std_msgs/msg/Bool` | True after the arm remains within tolerance for `reach_hold_time`. |
| `/arm/control_state` | publish | `std_msgs/msg/String` | Bridge state: `TRACKING`, `REACHED`, `HOLDING`, or `INVALID_TARGET`. |

## Low-level bridge topics

Only the bridge should publish `/arm/controller_command`.

| Topic | Direction | Type | Purpose |
| --- | --- | --- | --- |
| `/arm/controller_command` | publish | `aerial_manip_msgs/msg/ArmCommand` | Safe command forwarded to the low-level arm controller. |
| `/arm/controller_state` | subscribe | `aerial_manip_msgs/msg/ArmState` | Low-level controller feedback consumed by the bridge. |

## Command modes

`/arm/target_joints.command_mode` supports:

- `joint_position`: use `joint_positions` as the new target.
- `hold`: keep the last accepted safe target.
- `stow`: move to the configured `stow_joint_positions`.

If `joint_names` is empty, joint arrays are interpreted in configured
`joint_names` order. If `joint_names` is set, it must match the configured
joint set; the bridge reorders values before publishing status and controller
commands.

## Safety parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `joint_names` | `["joint1", "joint2", "joint3"]` | Controlled joint names and canonical order. |
| `initial_joint_positions` | `[0.0, 0.0, 0.0]` | Safe target used on startup. |
| `stow_joint_positions` | `[0.0, 0.0, 0.0]` | Target used for `stow` commands. |
| `min_joint_positions` | `[-1.57, -1.57, -1.57]` | Per-joint lower position limits in radians. |
| `max_joint_positions` | `[1.57, 1.57, 1.57]` | Per-joint upper position limits in radians. |
| `max_joint_velocities` | `[0.6, 0.6, 0.6]` | Per-joint velocity limits in radians per second. |
| `target_jump_limit` | `0.35` | Maximum allowed per-command joint position jump in radians. |
| `command_timeout` | `1.0` | Seconds before the bridge reports `HOLDING` while keeping the last safe target. |
| `reach_tolerance` | `0.03` | Per-joint position tolerance for reached-target detection in radians. |
| `reach_hold_time` | `0.5` | Seconds within tolerance before `/arm/reached_target` becomes true. |
| `command_period` | `0.05` | Low-level command publish period in seconds. |

The bridge rejects targets that contain non-finite values, violate joint
limits, exceed `target_jump_limit`, include velocity values above
`max_joint_velocities`, or use mismatched joint names.
