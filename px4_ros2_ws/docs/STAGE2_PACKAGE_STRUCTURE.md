# Stage 2 Package Structure

This document records the initial package skeleton for stage-2 aerial
manipulation work. The packages are intentionally minimal and do not implement
simulation behavior, controllers, perception, policy execution, or evaluation
logic yet.

## Package Overview

| Package | Build type | Role |
| --- | --- | --- |
| `aerial_manip_msgs` | `ament_cmake` | Shared messages and actions for platform state, arm command/state, system observations, task status, and approach goals. |
| `aerial_manip_gazebo` | `ament_cmake` | Asset-only placeholder for future Gazebo launch files, configs, models, and worlds. |
| `aerial_manip_control` | `ament_python` | Placeholder for future UAV-arm control nodes that use high-level `/uav/*` topics and arm command interfaces. |
| `aerial_manip_vision` | `ament_python` | Placeholder for future target perception and observation nodes. |
| `aerial_manip_policy` | `ament_python` | Placeholder for future scripted or learned policy integration, including LeRobot-facing code. |
| `aerial_manip_eval` | `ament_python` | Placeholder for future task metrics, log parsing, and benchmark summaries. |

## Interfaces

The first interface set is limited to the data needed by later stage-2 tasks:

| Interface | Purpose |
| --- | --- |
| `PlatformState.msg` | UAV local PX4 NED position, velocity, attitude, yaw, armed state, and navigation state. |
| `ArmCommand.msg` | Minimal arm command surface for hold, stow, or joint-position targets. |
| `ArmState.msg` | Joint state arrays, end-effector pose, contact flag, and textual arm state. |
| `SystemObservation.msg` | Combined platform, arm, target, visibility, and phase observation. |
| `TaskStatus.msg` | Generic task status with stable numeric states, message, and progress. |
| `Approach.action` | Minimal action contract for approaching a target pose to a standoff distance. |

`PlatformState.position_ned` follows the existing PX4 local NED convention used
by the UAV bridge. Positive altitude is represented by a negative `z` value.

## Package Boundaries

- External stage-2 modules should use `/uav/*` high-level topics for UAV motion.
- Stage-2 packages must not publish directly to PX4 `/fmu/in/*` topics.
- `aerial_manip_msgs` should stay small and shared; behavior belongs in the
  control, vision, policy, eval, or Gazebo packages.
- `aerial_manip_gazebo` is currently asset-only. Add launch files, models,
  worlds, and configs there before adding simulator-specific runtime nodes.
- The existing `px4_offboard_hover` package remains the owner of current Demo
  01-04 PX4 offboard behavior.

## Current Validation

Task 012 validation commands:

```bash
colcon build --packages-select aerial_manip_msgs
python3 -m compileall src/aerial_manip_control src/aerial_manip_vision src/aerial_manip_policy src/aerial_manip_eval
```
