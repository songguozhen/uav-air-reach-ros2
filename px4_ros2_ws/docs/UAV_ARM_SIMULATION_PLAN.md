# UAV Arm Simulation Plan

This document defines the planned direction for adding a lightweight UAV arm
simulation to the existing PX4 ROS 2 workspace. This is a planning document
only. It does not add URDF/SDF models, ROS 2 nodes, Gazebo plugins, launch
files, or LeRobot integration.

The starting platform should be the existing PX4 x500 simulation with a
simplified 2-DOF or 3-DOF arm. The first goal is to prove stable aerial contact
tasks without breaking Demo 01-04 behavior.

## Why Start with a 2-DOF or 3-DOF Arm

Aerial manipulation adds coupled dynamics between the multirotor and the arm.
Starting with a full 6-DOF manipulator would combine too many unvalidated
problems at once: mass distribution, inertia, joint control, contact modeling,
end-effector planning, collision geometry, and flight-controller disturbance
rejection.

A 2-DOF or 3-DOF arm is the right first step because:

| Benefit | Reason |
| --- | --- |
| Lower dynamics risk | Fewer links and lighter mass reduce center-of-mass shifts and torque disturbances on the x500 body. |
| Easier debugging | Joint commands, transforms, collision geometry, and contact behavior can be inspected link by link. |
| Smaller control surface | Early demos only need reach, extend, and touch motions, not full dexterous manipulation. |
| Faster simulation iteration | Simple inertial properties and collision meshes are easier to tune in Gazebo. |
| Cleaner LeRobot boundary | The learning problem can focus on end-effector operation before adding redundant arm kinematics. |

Recommended initial arm shapes:

- 2-DOF planar arm: shoulder pitch plus elbow pitch, with a small passive or
  fixed end-effector pad.
- 3-DOF lightweight arm: shoulder yaw, shoulder pitch, and elbow pitch, with the
  same simple end-effector pad.

The 2-DOF version should be attempted first unless the fixed target geometry
requires lateral reach that cannot be provided by UAV yaw and position control.

## Mounting Location

The arm should mount near the underside of the x500 center body, close to the
vehicle center of mass and away from the propeller disk.

Recommended mount:

```text
x500 base_link
  |
  +-- arm_mount_link: underside center or slightly forward underside
        |
        +-- shoulder_link
```

Use an underside mount for the first model:

- It keeps the arm clear of the propellers during extension.
- It makes downward or forward-downward target contact easier to observe.
- It reduces large roll or pitch moments compared with a side-mounted arm.
- It leaves the top of the vehicle free for existing sensors or future payloads.

If button-press tasks require a forward-facing end effector, the mount can be
slightly forward of the x500 center body, but the offset should remain small.
Any offset must be represented in the inertial model and documented as a
parameter.

Avoid side mounting in the first phase because it creates asymmetric inertia and
a constant lateral disturbance that will make PX4 Offboard validation harder.

## URDF and SDF Modeling Route

The modeling route should keep the ROS description, Gazebo simulation, and PX4
vehicle model boundaries clear.

Recommended route:

| Step | Output | Notes |
| --- | --- | --- |
| 1 | `x500_arm_description` package | New ROS 2 package for arm URDF/Xacro, meshes, and frame docs. |
| 2 | Arm-only URDF/Xacro | Define links, joints, inertial values, visual geometry, and collision geometry without PX4 coupling. |
| 3 | x500 attachment Xacro | Add an `arm_mount_link` and fixed joint from the x500 base frame to the arm base. |
| 4 | Gazebo SDF export or include | Use SDF-compatible tags for joint dynamics, collision, and contact surfaces. |
| 5 | World assets | Add fixed target and button models as separate Gazebo models, not embedded in the UAV model. |
| 6 | TF validation | Verify `base_link -> arm_mount_link -> shoulder -> elbow -> ee_link` transforms before running contact demos. |

The first arm model should use primitive shapes:

- Cylinders or boxes for links.
- Simple revolute joints with position limits.
- A small rounded or box end-effector pad.
- Conservative mass and inertia values.
- Simple collision geometry that is close to, but slightly simpler than, the
  visual geometry.

Avoid high-detail meshes in the first iteration. They make contacts harder to
debug and do not help validate the control architecture.

## Joint Control Options

Three joint-control approaches are viable. The recommended sequence is to start
simple, then move toward `ros2_control` once the model and contact tasks are
stable.

| Option | Use When | Pros | Cons |
| --- | --- | --- | --- |
| Simple joint command node | First arm extension tests | Smallest implementation, easy scripted trajectories, low dependency cost. | Not a standard hardware/control abstraction. |
| Gazebo joint control plugin | Early Gazebo-only demos | Direct simulation control, useful for fast contact experiments. | Can become simulator-specific and less reusable. |
| `ros2_control` | Stable Demo 05 and future LeRobot policy work | Standard ROS 2 control path, controller switching, trajectory controllers. | More setup: controllers, transmissions, plugin config, launch wiring. |

Recommended first implementation path:

1. Use a simple ROS 2 joint command interface for the first no-contact extension
   test.
2. Add a Gazebo-compatible joint control path for repeatable simulation.
3. Promote to `ros2_control` with a `joint_trajectory_controller` before using
   learned policies or comparing multiple control strategies.

The high-level arm command surface should be separate from PX4 topics. Candidate
topics for later implementation:

| Topic | Type | Purpose |
| --- | --- | --- |
| `/arm/joint_targets` | `sensor_msgs/msg/JointState` or trajectory message | Command shoulder/elbow target positions. |
| `/arm/end_effector_target` | `geometry_msgs/msg/PoseStamped` | Optional Cartesian target for an IK or scripted controller. |
| `/arm/contact_state` | `std_msgs/msg/Bool` or custom message | Report target or button contact. |

## Stage 1: Hover with Arm Extension

Goal: prove that the x500 can hold a stable Offboard hover while the arm moves
through a conservative extension trajectory.

Scenario:

- Start the existing PX4/Gazebo/Micro XRCE-DDS stack.
- Use the Demo 01-style Offboard hover behavior.
- Keep the UAV at a fixed local NED target.
- Command the arm from stowed pose to extended pose and back.
- Do not include target contact in this stage.

Success criteria:

- Vehicle remains in Offboard mode during the arm motion.
- Position tracking remains within an agreed hover tolerance.
- Arm joints reach target positions without oscillation.
- No collision occurs with the x500 body or propeller area.

Primary data to record:

- UAV local position and velocity.
- Arm joint positions and commanded targets.
- End-effector pose relative to `base_link`.
- PX4 failsafe or mode changes, if any.

## Stage 2: End-Effector Touches a Fixed Target

Goal: validate controlled aerial contact with a passive fixed target.

Scenario:

- Place a fixed target pad in the Gazebo world.
- Use PX4 Offboard to position the UAV near the target.
- Keep the platform stable while the arm performs the final reach.
- Detect contact through Gazebo contact reporting or end-effector proximity.

Success criteria:

- The end effector touches the target without destabilizing the vehicle.
- The target touch is detected and logged.
- Contact force or penetration remains bounded.
- The UAV can return to a safe hover after contact.

This stage should use a fixed target before a button because a passive target
removes button travel, spring stiffness, and state-change logic from the first
contact experiment.

## Stage 3: Aerial Button Press

Goal: extend fixed-target touch into a stateful operation where the arm presses
a simulated button while the UAV remains stable.

Scenario:

- Add a button model with a simple prismatic axis or contact-triggered state.
- Position the UAV near the button using PX4 Offboard.
- Command the arm to press along the button normal.
- Confirm press completion through button displacement, contact state, or a
  Gazebo plugin event.

Success criteria:

- Button state changes from unpressed to pressed.
- The press completes without PX4 failsafe, excessive vehicle drift, or arm
  collision.
- The system logs approach, contact, press, release, and retreat phases.

This stage should become the first version of the aerial manipulation benchmark
only after Stage 1 and Stage 2 are repeatable.

## Relationship with PX4 Offboard

PX4 Offboard should remain responsible for stabilizing and positioning the UAV
platform. The arm should execute local manipulation commands only.

Control boundary:

| Component | Responsibility |
| --- | --- |
| PX4 | Attitude stabilization, motor control, estimator, failsafe behavior. |
| Offboard bridge | High-level UAV position/yaw setpoints, target validation, emergency behavior. |
| Arm controller | Joint targets, end-effector motion, contact sequence, arm limits. |
| Task planner | Sequence such as hover, approach, extend, touch, retract, retreat. |

The arm controller must not publish low-level PX4 actuator, motor, attitude, or
rate commands. It may request UAV pose changes only through high-level topics
such as `/uav/target_position` or the future `/uav/target_pose` interface
defined for the workspace.

PX4 should hold the platform stable while the arm executes local operations. If
the arm motion causes excessive tracking error, the task should abort or retract
the arm rather than trying to override PX4 internals.

## Relationship with LeRobot

LeRobot should be introduced after the scripted arm tasks are stable. Its role
should be limited to learning or executing the local manipulation policy.

Allowed future LeRobot control scope:

- End-effector target selection.
- Arm joint trajectory policy.
- Contact timing and press depth policy.
- Visual or state-based manipulation decisions.

Disallowed LeRobot control scope:

- Direct motor control.
- PX4 attitude, rate, or actuator commands.
- Bypassing the Offboard bridge safety checks.
- Mixing flight-control stabilization with arm manipulation policy.

The intended future architecture is:

```text
LeRobot policy
  -> arm command topic or end-effector target
  -> arm controller
  -> simulated arm joints

Task planner or safety bridge
  -> /uav/target_position or /uav/target_pose
  -> PX4 Offboard
  -> stable x500 platform
```

This keeps the learning problem focused on manipulation and preserves PX4 as
the flight-control authority.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Center-of-mass change | Hover trim and tracking can degrade when the arm extends. | Start with a light underside arm, document mass properties, and compare hover error with stowed vs extended poses. |
| Inertia disturbance | Fast joint motion can induce roll, pitch, or yaw disturbance. | Limit joint speed and acceleration; begin with slow scripted trajectories. |
| Coordinate frames | NED, ENU, Gazebo, base link, and end-effector frames can be mixed incorrectly. | Define explicit frame names and validate TF before contact tests. |
| Contact instability | Contact with the target or button can create bouncing, penetration, or solver instability. | Use simple collision shapes, conservative stiffness/damping, and bounded approach speeds. |
| Simulation accuracy | Gazebo contact and lightweight arm dynamics may not match real hardware. | Treat Demo 05 as a simulation benchmark, not proof of real-world readiness. |
| PX4 failsafe interaction | Contact disturbances or simulation pauses may trigger failsafe behavior. | Keep Offboard setpoints continuous and log mode/failsafe state during tests. |
| Propeller/body collision | Bad joint limits or mount offsets can intersect the x500 model. | Add conservative joint limits and collision checks before enabling contact tasks. |

## Minimum Demo 05 Definition

Recommended Demo 05 target: **Aerial Target Touch**.

Aerial Target Touch is the better minimum demo because it validates the core
aerial manipulation stack before introducing button mechanics. It should prove:

- x500 Offboard hover remains stable.
- A 2-DOF or 3-DOF arm can extend from a safe stowed pose.
- The end effector can touch a fixed target.
- The system can log UAV trajectory, arm joints, end-effector pose, and contact
  result.

Demo 05 can later be upgraded to **Aerial Button Press** after the fixed-target
touch is repeatable.

Recommended Demo 05 output names should follow the existing stable naming
pattern where applicable:

- `trajectory.csv`
- `trajectory_3d.png`
- `xy_path.png`
- `height_curve.png`
- `speed_curve.png`
- `tracking_error.png`
- `trajectory.mp4`
- `summary.md`
- `result.txt`

Additional Demo 05-specific outputs may include:

- `arm_joints.csv`
- `end_effector_pose.csv`
- `contact_events.csv`
- `contact_result.txt`

## Current Missing Dependencies

The current workspace does not yet contain the pieces required to run the arm
simulation. The expected future additions are:

- A new arm description package with URDF/Xacro and optional Gazebo SDF assets.
- A combined x500 plus arm model or model include path.
- Joint controller configuration, either simple command node, Gazebo plugin, or
  `ros2_control`.
- Gazebo target and button models.
- Contact detection and logging.
- Arm trajectory scripts or a task sequencer for Demo 05.
- Optional IK or end-effector control utilities.
- Future LeRobot environment wrappers and policy interfaces.

None of these dependencies are implemented by this planning task.
