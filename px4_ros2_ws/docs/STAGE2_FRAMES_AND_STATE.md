# Stage 2 Frames and State

This document defines the stage-2 state aggregation boundary for UAV, arm, and
future vision state.

## State Aggregator

Run:

```bash
ros2 run aerial_manip_control state_aggregator
```

The node consumes only high-level state topics:

| Topic | Direction | Type | Notes |
| --- | --- | --- | --- |
| `/uav/current_position` | subscribe | `geometry_msgs/msg/PointStamped` | Existing UAV bridge output in local PX4 NED. |
| `/uav/control_state` | subscribe | `std_msgs/msg/String` | Existing UAV bridge state. |
| `/arm/current_joint_state` | subscribe | `aerial_manip_msgs/msg/ArmState` | Arm bridge/controller state. |
| `/arm/control_state` | subscribe | `std_msgs/msg/String` | Arm bridge state. |
| `/system/observation` | publish | `aerial_manip_msgs/msg/SystemObservation` | Combined platform and arm observation. |
| `/system/safety_status` | publish | `aerial_manip_msgs/msg/SafetyStatus` | Aggregated freshness and bridge-state health. |

The aggregator does not publish to `/uav/*` and does not change `/uav/*`
topic semantics.

## TF Tree

The intended baseline TF tree is:

```text
map -> uav/base_link -> uav/arm_base -> uav/ee_link -> uav/camera_link
```

`state_aggregator` broadcasts this tree. `map` is the ROS ENU world frame.
`uav/base_link`, `uav/arm_base`, `uav/ee_link`, and `uav/camera_link` are FLU
body/link frames unless a later robot description provides more specific link
conventions.

Default fixed offsets:

| Transform | Default translation |
| --- | --- |
| `uav/base_link -> uav/arm_base` | `[0.0, 0.0, -0.08]` |
| `uav/ee_link -> uav/camera_link` | `[0.12, 0.0, -0.04]` |

These are parameters and should be replaced by URDF-derived transforms when the
stage-2 model package owns a complete robot description.

## Coordinate Boundary

`/uav/current_position` remains local PX4 NED:

```text
x = north, y = east, z = down
```

`/system/observation.platform.position_ned` preserves that NED value exactly so
downstream modules can inspect the original bridge state without ambiguity.

The only baseline conversion performed by `state_aggregator` is for TF:

```text
enu_x = ned_y
enu_y = ned_x
enu_z = -ned_z
```

This keeps NED/ENU conversion centralized at the system observation boundary
while leaving existing UAV bridge topics unchanged. The current baseline does
not yet consume UAV attitude, so `map -> uav/base_link` uses identity rotation.
When attitude is added, FRD-to-FLU conversion should be added in this node or
the existing UAV bridge, not in external vision, policy, or LeRobot modules.

## Safety Status

`/system/safety_status` reports:

- `safe=true`, `severity=SEVERITY_OK`, `state=OK` when recent UAV and arm state
  are available and neither bridge reports `INVALID_TARGET`.
- `safe=false`, `severity=SEVERITY_WARN`, `state=DEGRADED` when UAV or arm state
  is missing/stale or a bridge reports `INVALID_TARGET`.

The `state_timeout` parameter controls stale-state detection. The default is
`1.0` second.
