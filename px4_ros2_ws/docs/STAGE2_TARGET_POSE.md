# Stage 2 Target Pose

Task: `018-add-tag-target-pose-estimation`

## Simulation Target

The stage-2 smoke world now includes a local ArUco target model:

```text
src/aerial_manip_gazebo/models/fiducial_target_aruco
```

World include:

```text
src/aerial_manip_gazebo/worlds/x500_arm_2dof_smoke.sdf
```

The marker is `DICT_4X4_50`, id `23`, with a physical marker size of `0.50 m`.
It is placed at:

```text
pose: 2.0 0 0.5 0 -1.57079632679 0
```

This puts the target in front of the x500 smoke model and rotates the marker
plane to face the forward camera.

## Pose Node

Run:

```bash
ros2 launch aerial_manip_vision tag_target_pose.launch.py
```

The node subscribes to:

| Topic | Type | Notes |
| --- | --- | --- |
| `/vision/front/image_raw` | `sensor_msgs/msg/Image` | Front camera image from the ROS/Gazebo bridge. |
| `/vision/front/camera_info` | `sensor_msgs/msg/CameraInfo` | Camera intrinsics used by OpenCV pose estimation. |

The node publishes:

| Topic | Type | Frame |
| --- | --- | --- |
| `/vision/target_pose` | `geometry_msgs/msg/PoseStamped` | `uav/camera_link` using OpenCV camera optical axes. |
| `/vision/target_pose_in_uav_frame` | `geometry_msgs/msg/PoseStamped` | `uav/base_link` using FLU axes. |

The camera optical to UAV FLU conversion is:

```text
uav_x = camera_z
uav_y = -camera_x
uav_z = -camera_y
```

Then the configured camera offset is added. The default
`camera_xyz_in_uav_frame` is `[0.12, 0.0, 0.242]`, matching the SDF camera
mount on `x500_arm_2dof`.

## Detector and Placeholder Modes

The active Python environment exposes OpenCV ArUco support, so the default node
uses `cv2.aruco.detectMarkers` and `cv2.aruco.estimatePoseSingleMarkers`.

If camera bridging or detector support is unavailable, run:

```bash
ros2 launch aerial_manip_vision tag_target_pose.launch.py publish_placeholder:=true
```

Placeholder mode publishes the documented static target pose at
`[2.0, 0.0, 0.5]` in `uav/base_link` and the corresponding relative pose in
`uav/camera_link`. This is a wiring smoke test only; it is not a visual
detection result.

## Smoke Checks

Build and compile:

```bash
python3 -m compileall src/aerial_manip_vision
colcon build --packages-select aerial_manip_vision aerial_manip_gazebo
```

With a sourced workspace, verify placeholder topic wiring without starting
Gazebo:

```bash
ros2 launch aerial_manip_vision tag_target_pose.launch.py publish_placeholder:=true
ros2 topic echo /vision/target_pose --once
ros2 topic echo /vision/target_pose_in_uav_frame --once
```

For visual detection, also start the smoke world and front camera bridge:

```bash
src/aerial_manip_gazebo/scripts/smoke_load_x500_arm_2dof.sh
ros2 launch aerial_manip_gazebo front_camera_bridge.launch.py
ros2 launch aerial_manip_vision tag_target_pose.launch.py
```

Current warning: `ros_gz_bridge` was previously recorded as missing in the
stage-2 environment audit, so live image detection depends on installing or
exposing the ROS/Gazebo bridge package.
