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

Task 027 added a bounded smoke script for the complete front-camera bridge path.
Task 032 verified the same path with `ros_gz_bridge` available and captured a
real sample frame:

```text
visualizations/demo_07_camera/20260528_113542/sample_frame.png
```

Run:

```bash
bash scripts/smoke_vision_bridge.sh
```

The script checks:

- local model, world, bridge config, and ArUco texture assets;
- Gazebo publication of the configured camera image topic;
- `ros_gz_bridge` package availability;
- ROS 2 availability of `/vision/front/image_raw`;
- ROS 2 availability of `/vision/front/camera_info`;
- target pose publication on `/vision/target_pose`.

When `ros_gz_bridge` is available and the image stream produces a frame, the
script writes:

```text
visualizations/demo_07_camera/<timestamp>/sample_frame.png
```

If a live frame cannot be captured, the same output directory contains
`sample_frame_status.txt` with the bounded-check reason.

The lower-level manual sequence is still useful for interactive debugging in a
sourced ROS 2 environment:

```bash
src/aerial_manip_gazebo/scripts/smoke_load_x500_arm_2dof.sh
ros2 launch aerial_manip_gazebo front_camera_bridge.launch.py
ros2 topic hz /vision/front/image_raw
```

If `ros_gz_bridge` is not installed, the package can still build, but runtime
image bridging is unavailable until the ROS/Gazebo bridge package is installed.
The smoke script reports this as `WARN` and does not substitute placeholder
target data for the live image checks.
