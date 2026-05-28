# Task 032: Verify Camera Bridge and Sample Frame

## Task goal

- Verify the Gazebo front-camera to ROS image bridge path.
- Capture one real sample frame from the Stage 2 camera smoke world.
- Keep the perception baseline geometry-only; do not add semantic vision or new camera models.

## Allowed changes

- `scripts/smoke_vision_bridge.sh`
- `docs/STAGE2_VISION_BRIDGE.md`
- `docs/STAGE2_TARGET_POSE.md`
- `codex-logs/032-verify-camera-bridge-and-sample-frame.log`

## Implementation requirements

- Use the existing `smoke_vision_bridge.sh` as the main entry point.
- Verify model assets, Gazebo camera topic availability, `ros_gz_bridge`, `/vision/front/image_raw`, `/vision/front/camera_info`, and target pose publishing.
- If the bridge is available, save one frame under `visualizations/demo_07_camera/<timestamp>/sample_frame.png`.
- If capture fails, keep `sample_frame_status.txt`, `front_camera_bridge.log`, `gz_sim.log`, and the exact failure reason.
- Keep placeholder target publishing explicit; do not silently replace live image evidence with placeholder-only evidence.

## Required commands

```bash
bash -n scripts/smoke_vision_bridge.sh
bash scripts/smoke_vision_bridge.sh | tee codex-logs/032-verify-camera-bridge-and-sample-frame.log
```

## Deliverables

- A timestamped `visualizations/demo_07_camera/<timestamp>/` directory.
- `sample_frame.png` when the image bridge works, or a precise status file when it does not.
- Updated vision docs if runtime behavior or limitations changed.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
- `sample frame path or failure status path`
