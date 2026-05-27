# Task 017: Add Front Camera and ros_gz_bridge

## Task goal

- Add a front RGB camera to `x500_arm_2dof` and bridge its image stream into ROS 2.

## Allowed changes

- `src/aerial_manip_gazebo/**`
- `src/aerial_manip_vision/**`
- `docs/STAGE2_VISION_BRIDGE.md`
- `codex-logs/017-add-front-camera-and-ros-gz-bridge.log`

## Implementation requirements

- Reuse the local `mono_cam` and `x500_mono_cam` references where practical.
- Configure `ros_gz_bridge` through YAML for the image and camera info topics.
- First version should use one RGB camera only.

## Required commands

```bash
python3 -m compileall src/aerial_manip_vision
colcon build --packages-select aerial_manip_gazebo aerial_manip_vision
ros2 topic hz /vision/front/image_raw || true
```

## Deliverables

- Camera model/launch/bridge config.
- Vision bridge documentation.
- Sample image output if simulation is available.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
