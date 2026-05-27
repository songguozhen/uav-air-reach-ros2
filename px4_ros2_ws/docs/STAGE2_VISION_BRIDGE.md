# Stage 2 Vision Bridge

Task: `017-add-front-camera-and-ros-gz-bridge`

## Front RGB Camera

The `x500_arm_2dof` model includes one forward-facing RGB camera by merging the
local PX4 `mono_cam` model into the existing `x500` include-merge pattern used
by `x500_mono_cam`.

Model path:

```text
src/aerial_manip_gazebo/models/x500_arm_2dof/model.sdf
```

Camera placement:

```text
parent: base_link
child: camera_link
pose: 0.12 0 0.242 0 0 0
```

The camera is centered on the vehicle body rather than offset laterally. The
first version intentionally exposes only one RGB stream.

## ROS/Gazebo Bridge

Bridge config:

```text
src/aerial_manip_gazebo/config/front_camera_bridge.yaml
```

Launch entry point:

```bash
ros2 launch aerial_manip_gazebo front_camera_bridge.launch.py
```

Bridged topics:

| ROS 2 topic | ROS 2 type | Gazebo topic | Direction |
| --- | --- | --- | --- |
| `/vision/front/image_raw` | `sensor_msgs/msg/Image` | `/world/x500_arm_2dof_smoke/model/x500_arm_2dof/link/camera_link/sensor/camera/image` | Gazebo to ROS 2 |
| `/vision/front/camera_info` | `sensor_msgs/msg/CameraInfo` | `/world/x500_arm_2dof_smoke/model/x500_arm_2dof/link/camera_link/sensor/camera/camera_info` | Gazebo to ROS 2 |

The bridge is configured through YAML instead of command-line bridge pairs so
future image topics can be added without changing the launch file.

## Smoke Run

Use the existing model smoke world and launch the bridge in a sourced ROS 2
environment:

```bash
src/aerial_manip_gazebo/scripts/smoke_load_x500_arm_2dof.sh
ros2 launch aerial_manip_gazebo front_camera_bridge.launch.py
ros2 topic hz /vision/front/image_raw
```

If `ros_gz_bridge` is not installed, the package can still build, but runtime
image bridging is unavailable until the ROS/Gazebo bridge package is installed.
