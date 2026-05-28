# Stage 2 Air Reach Demo

Demo 10 is the repeatable stage-2 "air reach" regression. It exercises the
high-level UAV bridge and arm bridge instead of publishing directly to PX4
`/fmu/in/*` topics.

## Sequence

1. Stable hover: command `/uav/target_position` through the UAV bridge and wait
   for a bounded hover error.
2. Tag detection: wait for `/vision/target_pose_in_uav_frame`. The live runner
   starts the tag node with `publish_placeholder:=true` when no camera detector
   is available.
3. Coordinated approach: send an `/approach` action goal so the approach
   coordinator commands `/uav/target_position` and `/arm/target_joints`.
4. Endpoint hold: hold the end-effector near the target. If contact sensing is
   present, `contact_detected` is carried into the metrics; otherwise the
   endpoint-distance criterion is used.

## Commands

Dry-run or automatic development regression:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
bash scripts/run_regression_demo_10.sh
python3 scripts/check_demo_10.py logs/demo10_air_reach
```

Bounded live stack readiness smoke:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
DEMO10_MODE=live-smoke RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

This starts PX4/Gazebo and Micro XRCE-DDS, waits for PX4 to print
`Ready for takeoff`, records the readiness line in
`logs/demo10_air_reach/<timestamp>/stack_readiness.txt`, and then runs
`scripts/stop_stack.sh`.

Live PX4/Gazebo regression:

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
DEMO10_MODE=live RESET_STACK=1 bash scripts/run_regression_demo_10.sh
```

The runner writes timestamped artifacts to:

```text
logs/demo10_air_reach/<timestamp>/
```

`DEMO10_MODE=auto` remains a dry-run path. Use `DEMO10_MODE=live-smoke` before
the full live mode when validating a machine or after a stale Gazebo/PX4
cleanup issue. The live runner syncs the sourced ROS/Gazebo environment into
tmux before starting PX4/Gazebo and waits 12 seconds after launching the bridge
nodes before starting `air_reach_demo`, so the initial hover target can settle
before live flight-error metrics are sampled.

Latest bounded live-smoke result:

```text
timestamp: 20260528_113832
path: logs/demo10_air_reach/20260528_113832
result: RESULT=PASS mode=live-smoke reason=stack_ready
readiness: STACK_READY=YES reason=ready_for_takeoff detail=PX4 reached Ready for takeoff
cleanup: no PX4/Gazebo/MicroXRCEAgent stack process remained after scripts/stop_stack.sh
```

Latest full live result:

```text
timestamp: 20260528_114546
path: logs/demo10_air_reach/20260528_114546
result: RESULT=PASS reason=ok
checker: CHECK=PASS
max_flight_error_m: 0.061
final_endpoint_error_m: 0.262
target_visible_ratio: 1.000
episode: logs/demo10_air_reach/20260528_114546/episodes/20260528_114546
```

## Metrics

`scripts/check_demo_10.py` validates `metrics.json`, `sequence_events.jsonl`,
and `result.txt`. A PASS requires:

| Metric | PASS criterion |
| --- | --- |
| Flight error | `flight_error.max_m <= flight_error.limit_m` |
| Joint limits | `joint_limits.violations == 0` |
| Target visibility | `target_visibility.visible_ratio >= target_visibility.min_visible_ratio` |
| Task timeout | `task_timeout.timed_out == false` |
| Final endpoint error | `final_endpoint_error.error_m <= final_endpoint_error.limit_m` |

## Live Nodes

`DEMO10_MODE=live` starts these nodes around the existing stack scripts:

```text
px4_offboard_hover/uav_control_bridge
aerial_manip_control/arm_control_bridge
aerial_manip_eval/synthetic_arm_controller
aerial_manip_control/state_aggregator
aerial_manip_vision/tag_target_pose_node
aerial_manip_control/approach_coordinator
aerial_manip_eval/episode_recorder
aerial_manip_eval/air_reach_demo
```

The synthetic arm controller is only a lightweight 3-joint plant for regression
closure. It can be replaced by a simulator-backed controller as long as the same
`/arm/controller_state` and `/arm/controller_command` boundary is preserved.
