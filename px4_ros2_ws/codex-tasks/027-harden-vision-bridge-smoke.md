# Task 027: Harden Vision Bridge Smoke

## Task goal

- Make the current front-camera and tag-pose path verifiable instead of only documented.
- Keep the first target perception baseline AprilTag/ArUco-style and geometry-only.
- Do not add semantic vision, VLMs, or new camera types.

## Allowed changes

- `src/aerial_manip_gazebo/**`
- `src/aerial_manip_vision/**`
- `scripts/smoke_vision_bridge.sh`
- `docs/STAGE2_VISION_BRIDGE.md`
- `docs/STAGE2_TARGET_POSE.md`
- `codex-logs/027-harden-vision-bridge-smoke.log`

## Implementation requirements

- Add a bounded smoke script that checks model assets, Gazebo camera topic availability, ROS bridge availability, `/vision/front/image_raw`, and `/vision/target_pose`.
- If `ros_gz_bridge` is missing, report `WARN` and still verify the placeholder target-pose path.
- If the bridge is available, save one sample frame under `visualizations/demo_07_camera/<timestamp>/sample_frame.png` or document why it could not be captured.
- Keep placeholder target publishing explicit; do not silently substitute placeholder data in live checks.

## Required commands

```bash
bash -n scripts/smoke_vision_bridge.sh
python3 -m compileall src/aerial_manip_vision
colcon build --packages-select aerial_manip_gazebo aerial_manip_vision
bash scripts/smoke_vision_bridge.sh | tee codex-logs/027-harden-vision-bridge-smoke.log
```

## Deliverables

- Vision bridge smoke script.
- Updated live/WARN behavior documentation.
- Sample image artifact when the bridge is available.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

