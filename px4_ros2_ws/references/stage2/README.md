# Stage 2 Reference Materials

This directory stores the source material used by the second-stage aerial
manipulation tasks.

## Layout

- `official/`: official PX4, Gazebo, ROS 2, ros2_control, and LeRobot pages.
- `papers/`: key aerial manipulation papers referenced by the stage-2 plan.
- `local_px4_models/`: local PX4 Gazebo model snapshots used as implementation references.
- `manifest.yaml`: source URL, local path, and intended task usage.
- `scripts/download_stage2_materials.sh`: repeatable downloader and local model copier.

## Refresh

Run from the workspace root:

```bash
bash references/stage2/scripts/download_stage2_materials.sh
```

If a remote page blocks direct download, keep its manifest entry and use the URL
as the source of truth for manual review.
