# UAV Control API

This document defines the planned high-level ROS 2 control API for the UAV
simulation workspace. The goal is to give vision modules, LeRobot policies, and
task planners one stable interface while keeping direct PX4 topics isolated
inside a safety/bridge node.

Task 004 was an interface design task. The reusable `uav_control_bridge` node
now implements the validated `/uav/target_position` command path. Demo 04 also
keeps its original external setpoint example behavior. The remaining topics
below are recommended contracts for later implementation steps.

## Coordinate Convention

Use the PX4 local NED frame for all `/uav/*` position topics:

| Axis | Meaning | Unit |
| --- | --- | --- |
| `x` | North / forward from local origin | m |
| `y` | East / right from local origin | m |
| `z` | Down from local origin | m |

PX4 local position and `px4_msgs/msg/TrajectorySetpoint` also use NED, so the
bridge can map most position fields directly.

External modules often reason about height as positive altitude above the local
origin. In that case:

```text
z_ned = -altitude
altitude = -z_ned
```

Example: a target 2 m above the local origin is `altitude=2.0` and
`z_ned=-2.0`.

Important command rule: `/uav/target_position.z` is already NED down. Do not
publish positive altitude values on this topic. A safe 2 m altitude command must
be sent as:

```text
x=0.0, y=0.0, z=-2.0
```

## Recommended Topics

| Topic | Type | Direction | Status | Purpose |
| --- | --- | --- | --- | --- |
| `/uav/target_position` | `geometry_msgs/msg/Point` | client -> UAV bridge | Implemented in `uav_control_bridge`; Demo 04 example also subscribes | Position-only target in local NED. |
| `/uav/target_pose` | `geometry_msgs/msg/PoseStamped` | client -> UAV bridge | Future | Position plus desired yaw. Roll and pitch should be ignored by the bridge. |
| `/uav/current_position` | `geometry_msgs/msg/PointStamped` | UAV bridge -> clients | Implemented in `uav_control_bridge` | Current filtered local NED position. |
| `/uav/current_target` | `geometry_msgs/msg/PointStamped` | UAV bridge -> clients | Implemented in `uav_control_bridge` | Sanitized target currently being sent to PX4. |
| `/uav/reached_target` | `std_msgs/msg/Bool` | UAV bridge -> clients | Implemented in `uav_control_bridge` | `true` when the current target is reached within configured tolerances. |
| `/uav/control_state` | `std_msgs/msg/String` | UAV bridge -> clients | Implemented in `uav_control_bridge` | Human-readable control state such as `TRACKING`, `HOLDING`, or `INVALID_TARGET`. |
| `/uav/emergency_stop` | `std_msgs/msg/Bool` | client -> UAV bridge | Future | `true` requests an immediate safety stop action. |

Implemented now:

- `/uav/target_position`
- `/uav/current_position`
- `/uav/current_target`
- `/uav/reached_target`
- `/uav/control_state`

Future work:

- `/uav/target_pose`
- `/uav/emergency_stop`

## Topic Details

### `/uav/target_position`

Type: `geometry_msgs/msg/Point`

Fields:

| Field | Meaning |
| --- | --- |
| `x` | Target north position in local NED, meters. |
| `y` | Target east position in local NED, meters. |
| `z` | Target down position in local NED, meters. Use `z=-altitude` for positive height commands. |

This topic is the minimal high-level command surface. It is suitable for simple
vision trackers, scripted waypoint tests, and LeRobot policies that only need to
move the UAV platform to a local position.

The `uav_control_bridge` node subscribes to this topic, rejects invalid or
unsafe NED points, and forwards only the last safe target as a PX4 position
setpoint through the shared offboard base class. Demo 04 still subscribes to
this topic as a direct external setpoint example.

Manual safe target publish example:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 topic pub --once /uav/target_position geometry_msgs/msg/Point \
  '{x: 0.0, y: 0.0, z: -2.0}'
```

This asks the bridge to hold local NED `(0.0, 0.0, -2.0)`, which is 2 m
positive altitude above the local origin. The point is safe with the default
bridge limits because altitude is between `0.5 m` and `5.0 m`, horizontal range
is `0.0 m`, and the jump from the default initial target is `0.0 m`.

### `/uav/target_pose`

Type: `geometry_msgs/msg/PoseStamped`

Recommended usage:

- `header.frame_id`: `uav_local_ned`
- `pose.position.x/y/z`: local NED target position.
- `pose.orientation`: desired yaw only. The bridge should extract yaw and ignore
  commanded roll/pitch so high-level clients cannot fight the flight controller.

Use this topic when a module needs to control the UAV heading, camera direction,
or approach orientation. If both `/uav/target_pose` and
`/uav/target_position` are active, the bridge should define one priority rule,
for example "latest valid command wins" or "pose has priority".

### `/uav/current_position`

Type: `geometry_msgs/msg/PointStamped`

The bridge publishes the current vehicle local position after checking PX4
validity flags. Source data comes from:

```text
/fmu/out/vehicle_local_position_v1
```

Mapping:

```text
point.x = VehicleLocalPosition.x
point.y = VehicleLocalPosition.y
point.z = VehicleLocalPosition.z
```

The bridge only publishes this topic when both `xy_valid` and `z_valid` are
true. The `header.frame_id` is `uav_local_ned`.

Clients that need positive altitude should compute `altitude=-point.z`.

### `/uav/current_target`

Type: `geometry_msgs/msg/PointStamped`

Publish the target after validation. This may differ from the raw
`/uav/target_position` or `/uav/target_pose` command when a client requests an
unsafe or too-large jump because the bridge keeps holding the last safe target.
The `header.frame_id` is `uav_local_ned`.

### `/uav/reached_target`

Type: `std_msgs/msg/Bool`

Implemented bridge logic:

```text
true when horizontal_error <= 0.30 m
and vertical_error <= 0.20 m
for at least 1.0 s
```

The exact tolerances are parameters on `uav_control_bridge`:

| Parameter | Default |
| --- | --- |
| `reach_xy_tolerance` | `0.30` |
| `reach_z_tolerance` | `0.20` |
| `reach_hold_time` | `1.0` |

### `/uav/control_state`

Type: `std_msgs/msg/String`

Recommended states:

| State | Meaning |
| --- | --- |
| `IDLE` | Bridge is running but no active target is available. |
| `TRACKING` | Bridge is sending sanitized setpoints to PX4. |
| `REACHED` | Current target has been reached within tolerance. |
| `HOLDING` | Bridge is holding the last safe target. |
| `LANDING` | Bridge requested landing. |
| `E_STOP` | Emergency stop is active; normal target commands are ignored. |
| `INVALID_TARGET` | Last command was rejected by validation. |

### `/uav/emergency_stop`

Type: `std_msgs/msg/Bool`

When `data=true`, the bridge should immediately stop accepting new target
commands and execute the configured safety action. In simulation, the default
should be to hold the last safe setpoint or command land. Disarm should be a
separate explicit option because disarming in the air can be destructive.

When `data=false`, the bridge may clear the emergency state only if a configured
operator or test policy allows it.

## Mapping to PX4 TrajectorySetpoint

The bridge node should be the only component that publishes:

```text
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
```

For a valid `/uav/target_position` command:

```text
TrajectorySetpoint.timestamp = current ROS clock in microseconds
TrajectorySetpoint.position = [target.x, target.y, target.z]
TrajectorySetpoint.velocity = [NaN, NaN, NaN]
TrajectorySetpoint.acceleration = [NaN, NaN, NaN]
TrajectorySetpoint.jerk = [NaN, NaN, NaN]
TrajectorySetpoint.yaw = configured yaw or yaw from /uav/target_pose
TrajectorySetpoint.yawspeed = NaN
```

Positive altitude values are not accepted directly on `/uav/target_position`.
Clients must convert to NED before publishing:

```text
TrajectorySetpoint.position = [north_m, east_m, -altitude_m]
```

The bridge must keep publishing `px4_msgs/msg/OffboardControlMode` with
`position=true` at the required offboard rate while streaming trajectory
setpoints.

## Safety Limits

The implemented `uav_control_bridge` exposes these safety parameters:

| Parameter | Default | Behavior |
| --- | --- | --- |
| `target_timeout` | `1.0` s | When no fresh safe target arrives before timeout, keep publishing the last safe target and report `HOLDING`. Set `<=0.0` to disable timeout state changes. |
| `max_altitude` | `5.0` m | Reject commands where positive altitude `-z` is above this value, for example `z < -5.0`. |
| `min_altitude` | `0.5` m | Reject airborne position targets too close to the ground, for example `z > -0.5`. |
| `max_horizontal_range` | `5.0` m | Reject commands where `sqrt(x*x + y*y)` exceeds this radius from the local origin. |
| `target_jump_limit` | `1.5` m | Reject a received target if its 3D distance from the current safe target is larger than this value. |
| `reach_xy_tolerance` | `0.30` m | `/uav/reached_target` XY tolerance around the current safe target. |
| `reach_z_tolerance` | `0.20` m | `/uav/reached_target` vertical NED z tolerance around the current safe target. |
| `reach_hold_time` | `1.0` s | Required continuous time inside the reach tolerances before publishing `reached_target=true`. |

The original design also recommended future slew-rate limits for horizontal and
vertical speed. Those are not implemented in the current bridge; use
`target_jump_limit` and conservative client-side target updates for now.

The current `uav_control_bridge` rejects commands outside these altitude, range,
and target-jump limits. On target timeout it keeps publishing the last safe
target and rate-limits timeout warnings to no more than once per timeout
interval. It publishes the held safe target on `/uav/current_target` and the
state on `/uav/control_state`. It also publishes `/uav/current_position` from
valid PX4 local-position samples and `/uav/reached_target` using the configured
reach tolerances.

Start the bridge manually with explicit defaults:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 run px4_offboard_hover uav_control_bridge --ros-args \
  -p initial_x:=0.0 \
  -p initial_y:=0.0 \
  -p initial_z:=-2.0 \
  -p yaw:=0.0 \
  -p target_timeout:=1.0 \
  -p max_altitude:=5.0 \
  -p min_altitude:=0.5 \
  -p max_horizontal_range:=5.0 \
  -p target_jump_limit:=1.5 \
  -p reach_xy_tolerance:=0.30 \
  -p reach_z_tolerance:=0.20 \
  -p reach_hold_time:=1.0
```

## Bridge-backed Demo 04

Run Demo 04 through `uav_control_bridge` from the workspace root:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo04_external_setpoint.sh
```

`DEMO04_MODE=bridge` is the default. The runner starts PX4/Gazebo and Micro
XRCE-DDS with `scripts/start_stack.sh`, starts the trajectory recorder, runs
`ros2 run px4_offboard_hover uav_control_bridge`, and publishes the square
target sequence to `/uav/target_position`.

For an audit-only command preview without launching the simulator:

```bash
DRY_RUN=1 ./scripts/run_demo04_external_setpoint.sh
```

For legacy comparison only:

```bash
DEMO04_MODE=legacy ./scripts/run_demo04_external_setpoint.sh
```

The bridge-backed runner uses a longer demo timeout and a larger per-command
jump allowance than the bridge defaults:

```text
BRIDGE_TARGET_TIMEOUT=25.0
BRIDGE_TARGET_JUMP_LIMIT=2.5
BRIDGE_MAX_ALTITUDE=5.0
BRIDGE_MIN_ALTITUDE=0.5
BRIDGE_MAX_HORIZONTAL_RANGE=5.0
```

Those runner values keep the existing square sequence valid while preserving
the same altitude and horizontal range limits.

## Why LeRobot Should Not Publish `/fmu/in/*`

LeRobot, vision modules, and task planners should not publish PX4 input topics
directly because those topics are low-level flight-control interfaces:

- `/fmu/in/trajectory_setpoint` expects PX4 NED semantics, valid timestamps,
  feasible setpoints, and continuous streaming.
- `/fmu/in/offboard_control_mode` must be synchronized with setpoint streaming
  for PX4 offboard mode to remain valid.
- `/fmu/in/vehicle_command` can arm, change modes, or land the vehicle.
- Direct publishers can bypass altitude, range, speed, timeout, and emergency
  stop checks.
- Multiple direct publishers can race and send conflicting setpoints.

The high-level `/uav/*` API gives learning and perception modules a small,
auditable command surface. A single bridge node can validate commands, enforce
limits, publish state, and own the PX4-specific details.

## Future Integration

### Vision Module

A visual tracker should publish object-relative or world-local targets through
`/uav/target_position` after transforming detections into the local NED frame.
It should subscribe to `/uav/current_position`, `/uav/current_target`, and
`/uav/control_state` for feedback and should stop commanding motion when the
bridge reports `E_STOP`, `LANDING`, or `INVALID_TARGET`.

### LeRobot Policy

LeRobot should output high-level goals such as "move the UAV platform to this
local target" or "hold while the arm acts". Those goals should be translated to
`/uav/target_position` or `/uav/target_pose`. LeRobot must not control PX4
motors, attitude, arming, or offboard internals directly.

### UAV Arm

For the simplified 2-DOF or 3-DOF arm simulation, keep the flight platform and
arm policies separated:

- PX4/offboard bridge keeps the UAV stable using `/uav/*` targets.
- Arm controller handles local joint or end-effector commands.
- Task planner coordinates phases: fly near target, hold position, move arm,
  then retreat.

The planner can use `/uav/reached_target` and `/uav/control_state` as gates
before enabling arm actions.

## Implementation Notes

Implemented in `uav_control_bridge`:

- Subscribe to `/uav/target_position` as `geometry_msgs/msg/Point` in local NED.
- Subscribe to `/fmu/out/vehicle_local_position_v1` as
  `px4_msgs/msg/VehicleLocalPosition`.
- Publish PX4 offboard mode, trajectory setpoint, and vehicle command messages
  only through `OffboardPositionControl`.
- Publish `/uav/current_position`, `/uav/current_target`,
  `/uav/reached_target`, and `/uav/control_state`.
- Reject non-finite, positive-altitude, out-of-altitude-limit,
  out-of-horizontal-range, and excessive-jump targets.
- Hold the last safe target on timeout.
- Report `TRACKING`, `REACHED`, `HOLDING`, and `INVALID_TARGET` bridge states.

Interfaces still needing implementation:

- Subscribe to `/uav/target_pose`.
- Subscribe to `/uav/emergency_stop`.
- Add validation, clamping, and slew limiting in the future UAV bridge.

Do not implement these by changing PX4-Autopilot. They belong in the custom ROS
2 workspace package, likely as an extension or replacement for the current Demo
04 external setpoint node.
