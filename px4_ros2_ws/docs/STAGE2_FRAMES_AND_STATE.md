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

These five frame names are canonical for the stage-2 regression surface:

| Role | Frame |
| --- | --- |
| ROS world frame | `map` |
| UAV base link | `uav/base_link` |
| Arm base link | `uav/arm_base` |
| End-effector link | `uav/ee_link` |
| Camera link | `uav/camera_link` |

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

The lightweight schema regression enforces the conversion with these fixed
cases and the inverse ENU-to-NED round trip:

| NED input | Expected ENU output |
| --- | --- |
| `(0.0, 0.0, 0.0)` | `(0.0, 0.0, 0.0)` |
| `(1.0, 2.0, -3.0)` | `(2.0, 1.0, 3.0)` |
| `(-4.5, 0.25, 2.0)` | `(0.25, -4.5, -2.0)` |

## Arm Schema

The baseline arm schema is a 2-DOF pitch arm. The canonical joint order is:

```text
arm_shoulder_pitch_joint
arm_elbow_pitch_joint
```

For `aerial_manip_msgs/msg/ArmCommand` and `aerial_manip_msgs/msg/ArmState`,
the regression treats `joint_positions`, `joint_velocities`, and
`joint_efforts` as vectors that must match this two-joint order when populated.
The `.msg` definitions remain variable-length ROS arrays so commands can still
be represented normally on the wire, but the stage-2 bridge defaults and dry-run
artifacts are checked against exactly two joints.

## Frame and Schema Regression

Run the deterministic regression without PX4 or Gazebo:

```bash
python3 scripts/check_stage2_schema.py
```

The checker validates:

- canonical frame names and the `map -> uav/base_link -> uav/arm_base ->
  uav/ee_link -> uav/camera_link` chain;
- NED-to-ENU conversion and ENU-to-NED round trip cases used by
  `state_aggregator`;
- canonical 2-DOF joint names, limits, velocity-vector lengths, and source
  alignment with shared constants;
- the arm and observation message fields used for the stage-2 schema.

Each run emits a machine-readable report:

```text
logs/demo_06_state_agg/<timestamp>/tf_report.json
```

## Safety Status

`/system/safety_status` reports:

- `safe=true`, `severity=SEVERITY_OK`, `state=OK` when recent UAV and arm state
  are available and neither bridge reports `INVALID_TARGET`.
- `safe=false`, `severity=SEVERITY_WARN`, `state=DEGRADED` when UAV or arm state
  is missing/stale or a bridge reports `INVALID_TARGET`.

The `state_timeout` parameter controls stale-state detection. The default is
`1.0` second.
