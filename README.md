# uav-air-reach-ros2

PX4 + ROS2 UAV-air-reach research workspace for offboard flight control, a lightweight UAV-arm simulation stack, high-level UAV/arm command bridges, target-pose perception baselines, LeRobot-style data export, and repeatable regression demos.

This repository records the stage-2 implementation state of `/home/clcwork/UAV_capture`: 22 queued Codex tasks have been completed, with project reports and task logs preserved for review.

## Highlights

- PX4 Offboard demos for hover, waypoint flight, circle trajectory, and external setpoint control.
- High-level `/uav/*` bridge that keeps external modules away from raw PX4 `/fmu/in/*` topics.
- High-level `/arm/*` bridge with joint limits, velocity limits, target-jump checks, and command timeout handling.
- `aerial_manip_*` ROS2 packages for messages, control, Gazebo assets, target-pose vision, evaluation, and policy baselines.
- UAV-arm approach coordinator using a ROS2 action interface.
- Episode recorder and LeRobot-style dataset/policy bridge scaffolding.
- Demo 10 air-reach dry-run regression with deterministic metrics and PASS/FAIL checks.
- Self-contained project status dashboard in `deliverables/status.html`.

## Repository Layout

```text
.
├── deliverables/                  # Status dashboard, task summaries, audit JSON
├── px4_ros2_ws/                   # Primary ROS2 workspace
│   ├── codex-tasks/               # Numbered implementation tasks 001-022
│   ├── codex-logs/                # Task logs and .done markers
│   ├── docs/                      # API, modeling, regression, vision, policy docs
│   ├── scripts/                   # Demo runners, checks, stack control
│   ├── src/
│   │   ├── aerial_manip_control/  # Arm bridge, state aggregator, approach coordinator
│   │   ├── aerial_manip_eval/     # Demo 10, recorder, synthetic controller
│   │   ├── aerial_manip_gazebo/   # Gazebo models, worlds, camera bridge launch
│   │   ├── aerial_manip_msgs/     # Custom ROS2 messages and Approach action
│   │   ├── aerial_manip_policy/   # LeRobot baseline training and policy bridge
│   │   ├── aerial_manip_vision/   # Tag target pose node and launch
│   │   ├── px4_msgs/              # PX4 ROS2 messages, tracked as submodule
│   │   └── px4_offboard_hover/    # PX4 Offboard demos and UAV bridge
│   └── run_codex_queue.sh         # Queue runner used for staged implementation
├── px4_ws/PX4-Autopilot/          # PX4 upstream dependency, tracked as submodule
└── scripts/                       # Host-level helper scripts
```

## Current Status

The Codex task queue has completed tasks `001` through `022`.

Latest dashboard:

```text
deliverables/status.html
```

Latest task inventory:

```text
deliverables/task-summary.md
deliverables/task-status.json
```

Latest Demo 10 dry-run regression passed:

```text
CHECK=PASS
max_flight_error_m=0.067
final_endpoint_error_m=0.051
target_visible_ratio=0.775
```

Known validation gap: live PX4/Gazebo Demo 10 has not been run yet. The dry-run regression is deterministic and suitable for fast CI-style checks, but simulator timing, camera bridge behavior, and live stack startup still need live validation.

## Clone And Restore

This repository uses Git submodules for large upstream dependencies.

```bash
git clone --recursive git@github.com:songguozhen/uav-air-reach-ros2.git
cd uav-air-reach-ros2
git submodule update --init --recursive
```

If the repository was cloned without `--recursive`, run:

```bash
git submodule update --init --recursive
```

## Build

```bash
cd px4_ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select \
  aerial_manip_msgs \
  aerial_manip_control \
  aerial_manip_gazebo \
  aerial_manip_vision \
  aerial_manip_eval \
  aerial_manip_policy \
  px4_offboard_hover
```

## Checks

Fast syntax and package checks:

```bash
cd px4_ros2_ws
python3 -m compileall src scripts
bash -n run_codex_queue.sh
bash -n scripts/check_demo_outputs.sh
bash -n scripts/run_regression_demo_10.sh
```

Demo 10 dry-run result check:

```bash
cd px4_ros2_ws
python3 scripts/check_demo_10.py logs/demo10_air_reach/20260527_191707
```

Live Demo 10 follow-up:

```bash
cd px4_ros2_ws
DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

## Important Docs

- `px4_ros2_ws/docs/UAV_CONTROL_API.md`
- `px4_ros2_ws/docs/ARM_CONTROL_API.md`
- `px4_ros2_ws/docs/STAGE2_FRAMES_AND_STATE.md`
- `px4_ros2_ws/docs/STAGE2_COORDINATOR.md`
- `px4_ros2_ws/docs/STAGE2_TARGET_POSE.md`
- `px4_ros2_ws/docs/STAGE2_DATASET_SCHEMA.md`
- `px4_ros2_ws/docs/STAGE2_LEROBOT_POLICY.md`
- `px4_ros2_ws/docs/STAGE2_AIR_REACH_DEMO.md`
- `px4_ros2_ws/docs/REGRESSION_CHECKS.md`

## Notes

- Generated ROS2 build/install/log directories are intentionally ignored.
- PX4 SITL logs, visualization outputs, rosbags, model checkpoints, and cache files are intentionally ignored.
- `px4_ws/PX4-Autopilot` and `px4_ros2_ws/src/px4_msgs` are stored as submodule references to keep this project repository small and reproducible.
