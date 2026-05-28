# Stage 2 Approach Coordinator

Task: `019-add-uav-arm-approach-coordinator`

## Node

Run after the UAV bridge, arm bridge, and state aggregator are publishing:

```bash
ros2 run aerial_manip_control approach_coordinator
```

The coordinator is a rule-based action server for coarse UAV positioning plus
local arm adjustment. It does not publish to PX4 `/fmu/in/*` topics.

## Interfaces

| Interface | Direction | Type | Purpose |
| --- | --- | --- | --- |
| `/approach` | action server | `aerial_manip_msgs/action/Approach` | Approach a target pose with a coarse UAV standoff and local arm trim. |
| `/system/observation` | subscribe | `aerial_manip_msgs/msg/SystemObservation` | Combined UAV and arm state from `state_aggregator`. |
| `/approach_coordinator/stop` | subscribe | `std_msgs/msg/Bool` | `true` cancels active work and commands a safe hold/stow path. |
| `/uav/target_position` | publish | `geometry_msgs/msg/Point` | High-level UAV target in local PX4 NED. |
| `/arm/target_joints` | publish | `aerial_manip_msgs/msg/ArmCommand` | High-level arm joint target, hold, or stow command. |

Only `/uav/target_position` and `/arm/target_joints` are command outputs. The
coordinator must remain above the UAV and arm bridge safety boundaries.

## Goal Semantics

`Approach.Goal.target_pose.pose.position` is interpreted in the same local NED
workspace as `/uav/current_position`:

```text
x = north, y = east, z = down
```

Positive altitude is therefore represented by negative `z`. A target at 2 m
altitude uses `z = -2.0`.

`standoff_distance_m` is the horizontal UAV standoff from the target. If it is
`0` or negative, `default_standoff_distance_m` is used. `timeout_sec` behaves
the same way with `default_timeout`.

## Rule-Based Behavior

1. Wait for a fresh `/system/observation`.
2. Validate the target against workspace and standoff limits.
3. Command `/uav/target_position` toward a standoff point near the target,
   limiting each target jump by `max_uav_target_step`.
4. When the UAV is within coarse tolerances, keep the UAV at the standoff and
   command `/arm/target_joints` using the remaining local target residual.
5. Succeed after the residual remains within `arm_reach_tolerance` for
   `arm_hold_time`.
6. On timeout, cancel, or `/approach_coordinator/stop=true`, command the UAV to
   hold its current high-level target and command the arm to `stow` or `hold`.

The arm trim is deliberately simple. The default `x500_arm_2dof` mapping applies
vertical residual to `arm_shoulder_pitch_joint` and forward residual to
`arm_elbow_pitch_joint`, then clamps by joint limits and `max_arm_joint_step`.
If a custom three-or-more joint configuration is supplied, the coordinator
keeps the earlier generic mapping: lateral residual to joint 1, forward
residual to joint 2, and vertical residual to joint 3.

## Safety Parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| `control_period` | `0.1` | Coordinator loop period in seconds. |
| `uav_command_min_interval` | `0.2` | Minimum seconds between `/uav/target_position` commands. |
| `arm_command_min_interval` | `0.2` | Minimum seconds between `/arm/target_joints` commands. |
| `observation_timeout` | `1.0` | Maximum age for `/system/observation`. |
| `default_timeout` | `20.0` | Goal timeout when the action goal does not set one. |
| `default_standoff_distance_m` | `0.7` | Default horizontal UAV standoff. |
| `min_standoff_distance_m` | `0.25` | Minimum accepted standoff. |
| `max_standoff_distance_m` | `3.0` | Maximum accepted standoff. |
| `max_horizontal_range` | `8.0` | Maximum NED horizontal range from local origin. |
| `min_altitude` | `0.4` | Minimum altitude in meters; enforced as `z <= -0.4`. |
| `max_altitude` | `5.0` | Maximum altitude in meters; enforced as `z >= -5.0`. |
| `max_uav_target_step` | `0.5` | Maximum 3D jump per generated UAV target. |
| `coarse_xy_tolerance` | `0.25` | Horizontal tolerance for switching to arm trim. |
| `coarse_z_tolerance` | `0.20` | Vertical NED tolerance for switching to arm trim. |
| `arm_reach_tolerance` | `0.18` | Local residual tolerance for action success. |
| `arm_hold_time` | `0.5` | Time inside arm residual tolerance before success. |
| `joint_names` | `["arm_shoulder_pitch_joint", "arm_elbow_pitch_joint"]` | Joint order used for `/arm/target_joints`. |
| `arm_stow_on_cancel` | `true` | Send `stow` instead of `hold` on cancel/stop/timeout. |
| `arm_home_positions` | `[0.0, 0.0]` | Fallback joint state if observation lacks arm joints. |
| `min_joint_positions` | `[-0.7, -1.2]` | Coordinator-side joint lower limits. |
| `max_joint_positions` | `[0.7, 1.2]` | Coordinator-side joint upper limits. |
| `max_arm_joint_step` | `0.20` | Maximum per-command joint change. |
| `arm_forward_gain` | `0.35` | Residual-x to elbow pitch gain for the default arm. |
| `arm_lateral_gain` | `0.45` | Residual-y gain used only by custom generic joint mappings. |
| `arm_vertical_gain` | `-0.35` | Residual-z to shoulder pitch gain for the default arm. |

The UAV bridge and arm bridge still apply their own safety checks. Coordinator
limits are an earlier high-level guard, not a replacement for bridge limits.
