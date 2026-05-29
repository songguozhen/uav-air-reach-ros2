# Project Audit Summary

- generated_at: `2026-05-29T01:19:27+08:00`
- workspace: `/home/clcwork/UAV_capture/px4_ros2_ws`
- overall_status: `Warning`
- detected_stack: `ROS 2 Jazzy`, `PX4 SITL`, `Gazebo Sim`, `Micro XRCE-DDS Agent`, `Python/rclpy`, `ament/colcon`, `shell automation`

## Current Simulation Evidence

- Demo 01 Offboard Hover: `PASS` at `visualizations/demo01_hover/20260526_221722`; RESULT=PASS reason=ok
- Demo 02 Waypoint Flight: `PASS` at `visualizations/demo02_waypoint_flight/20260526_222121`; RESULT=PASS reason=ok
- Demo 03 Circle Trajectory: `PASS` at `visualizations/demo03_circle_trajectory/20260526_222313`; RESULT=PASS reason=ok
- Demo 04 External Setpoint / UAV Bridge: `PASS` at `visualizations/demo04_external_setpoint/20260527_085025`; RESULT=PASS reason=ok
- Demo 07 camera: `PASS` at `visualizations/demo_07_camera/20260528_113542`; sample_frame=captured
- Demo 10 full live: `PASS` at `logs/demo10_air_reach/20260528_114546`; RESULT=PASS reason=ok
- Demo 10 visualizations: `PASS` at `visualizations/demo10_air_reach/20260528_114546`; mode `live`
- Demo 10 interactive replay: `PASS` at `visualizations/demo10_air_reach/20260528_114546/trajectory_replay.html`
- Advanced visualization bundle: `WARN`
  - Visualization Manifest: `PASS` at `visualizations/visualization_manifest.json`
  - Demo 10 Advanced 3D Replay: `WARN` at `visualizations/demo10_air_reach/20260528_114546/advanced`
  - Demo 01-04 Flight Comparison: `WARN` at `visualizations/flight_comparison/20260529_010033`
  - 2D Diagnostics Dashboard And Sheets: `WARN` at `visualizations/diagnostics/20260529_010849`
  - Video Packaging Summary: `WARN` at `visualizations/video_packaging_summary.json`

## Live / Dry-run / Fallback Status

- live_ready: `PARTIAL`
- dry_run_ready: `YES`
- fallback_status: `Demo 10 visualization is live; dry-run fallback remains available.`

## Risks

- One or more advanced visualization layers are incomplete or only partially packaged.
- Reproducibility still depends on local ROS/Gazebo bridge and controller packages.
- Timestamped evidence is local to this workspace and should be regenerated after dependency changes.
- LeRobot policy integration remains scaffolded; current Demo 10 evidence validates the scripted/control bridge path.

## Next Actions

- Use deliverables/simulation_showcase.html for presentation review of current simulation effects.
- Review the Advanced Visualization Layers section for 3D comparison, diagnostics, packaging, and manifest status.
- Open the Demo 10 interactive replay from visualizations/demo10_air_reach/<timestamp>/trajectory_replay.html for path playback.
- Rerun python3 scripts/generate_demo10_visualizations.py --latest-live after new Demo 10 live evidence.
- Rerun python3 scripts/generate_demo10_replay.py --latest-live after new Demo 10 live evidence.
- Rerun bash scripts/smoke_vision_bridge.sh after ROS/Gazebo bridge changes to refresh Demo 07 camera evidence.
- Install or verify missing ROS/Gazebo control packages before claiming reproducible full live readiness on a fresh machine.
