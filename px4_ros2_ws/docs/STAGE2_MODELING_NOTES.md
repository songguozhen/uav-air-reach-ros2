# Stage 2 Modeling Notes

## x500_arm_2dof

Task: `013-add-x500-arm-2dof-model`

Model path:

```text
src/aerial_manip_gazebo/models/x500_arm_2dof
```

Smoke-test entry point:

```bash
src/aerial_manip_gazebo/scripts/smoke_load_x500_arm_2dof.sh
```

The model follows the local PX4 `x500_mono_cam` include-merge pattern: it
includes the existing `x500` model with `merge="true"` and adds only the arm
links and joints in this workspace. PX4-Autopilot model files are not modified.

### Geometry and Placement

- `arm_link_1`: 0.20 m x 0.035 m x 0.035 m box, centered at
  `0.20 0 -0.08` relative to `base_link`.
- `arm_link_2`: 0.16 m x 0.03 m x 0.03 m box, centered at
  `0.38 0 -0.08` relative to `base_link`.
- `arm_shoulder_pitch_joint`: revolute joint at `0.10 0 -0.08` relative to
  `base_link`, pitch axis `0 1 0`.
- `arm_elbow_pitch_joint`: revolute joint at `0.30 0 -0.08` relative to
  `base_link`, pitch axis `0 1 0`.

The arm is kept short and nearly centered under the forward body so the first
smoke tests avoid propeller and landing gear interference.

### Mass and Inertia Assumptions

The arm is intentionally lightweight compared with the 2.0 kg x500 base:

| Link | Mass | Box dimensions | Inertia assumption |
| --- | ---: | --- | --- |
| `arm_link_1` | 0.08 kg | 0.20 m x 0.035 m x 0.035 m | Uniform solid box |
| `arm_link_2` | 0.06 kg | 0.16 m x 0.03 m x 0.03 m | Uniform solid box |

The SDF inertias use the rectangular prism formulas:

```text
Ixx = m / 12 * (y^2 + z^2)
Iyy = m / 12 * (x^2 + z^2)
Izz = m / 12 * (x^2 + y^2)
```

Joint limits and damping are conservative starting values:

| Joint | Limits | Effort | Velocity | Damping |
| --- | --- | ---: | ---: | ---: |
| `arm_shoulder_pitch_joint` | -0.7 rad to 0.7 rad | 1.0 N m | 1.5 rad/s | 0.20 |
| `arm_elbow_pitch_joint` | -1.2 rad to 1.2 rad | 0.8 N m | 1.5 rad/s | 0.18 |

### Current Limitations

- No ROS 2 control plugin is attached yet; later control tasks should add that
  through the `aerial_manip_control` scope.
- The smoke test only checks that Gazebo can load the model and run one server
  iteration. It does not validate flight stability or arm actuation.
