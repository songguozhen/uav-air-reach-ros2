#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="/home/clcwork/UAV_capture/px4_ros2_ws"
cd "$WORKSPACE_ROOT"

DEMO_NAME="demo10_air_reach"
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
MODE="${DEMO10_MODE:-auto}"
OUTPUT_DIR="logs/${DEMO_NAME}/${TIMESTAMP}"
RUNNER_LOG="${OUTPUT_DIR}/runner.log"

mkdir -p "$OUTPUT_DIR"

log() {
  printf '[demo10] %s\n' "$*" | tee -a "$RUNNER_LOG"
}

run_dry() {
  log "mode=dry-run output_dir=${OUTPUT_DIR}"
  PYTHONPATH="${WORKSPACE_ROOT}/src/aerial_manip_eval${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m aerial_manip_eval.demo10_dry_run \
      --output-dir "$OUTPUT_DIR" \
      --timestamp "$TIMESTAMP" 2>&1 | tee -a "$RUNNER_LOG"
  python3 scripts/check_demo_10.py "$OUTPUT_DIR" 2>&1 | tee -a "$RUNNER_LOG"
}

run_live() {
  if [ ! -f install/setup.bash ]; then
    log "install/setup.bash is missing; run colcon build before DEMO10_MODE=live"
    return 2
  fi

  # shellcheck disable=SC1091
  source install/setup.bash

  log "mode=live output_dir=${OUTPUT_DIR}"
  RESET_STACK="${RESET_STACK:-1}" scripts/start_stack.sh 2>&1 | tee -a "$RUNNER_LOG"

  PIDS=""
  cleanup() {
    for pid in $PIDS; do
      kill "$pid" 2>/dev/null || true
    done
    wait $PIDS 2>/dev/null || true
    scripts/stop_stack.sh >>"$RUNNER_LOG" 2>&1 || true
  }
  trap cleanup EXIT

  ros2 run px4_offboard_hover uav_control_bridge >>"${OUTPUT_DIR}/uav_control_bridge.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_control arm_control_bridge >>"${OUTPUT_DIR}/arm_control_bridge.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_eval synthetic_arm_controller >>"${OUTPUT_DIR}/synthetic_arm_controller.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_control state_aggregator >>"${OUTPUT_DIR}/state_aggregator.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_vision tag_target_pose_node \
    --ros-args -p publish_placeholder:=true \
    >>"${OUTPUT_DIR}/tag_target_pose_node.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_control approach_coordinator >>"${OUTPUT_DIR}/approach_coordinator.log" 2>&1 &
  PIDS="${PIDS} $!"
  ros2 run aerial_manip_eval episode_recorder \
    --ros-args \
    -p demo_name:="$DEMO_NAME" \
    -p timestamp:="$TIMESTAMP" \
    -p task_label:=air_reach \
    -p task_id:=demo10_air_reach \
    >>"${OUTPUT_DIR}/episode_recorder.log" 2>&1 &
  PIDS="${PIDS} $!"

  sleep "${DEMO10_NODE_STARTUP_SEC:-5}"
  ros2 run aerial_manip_eval air_reach_demo --output-dir "$OUTPUT_DIR" \
    >>"${OUTPUT_DIR}/air_reach_demo.log" 2>&1
  python3 scripts/check_demo_10.py "$OUTPUT_DIR" 2>&1 | tee -a "$RUNNER_LOG"
}

case "$MODE" in
  dry-run)
    run_dry
    ;;
  live)
    run_live
    ;;
  auto)
    log "mode=auto using dry-run; set DEMO10_MODE=live for PX4/Gazebo execution"
    run_dry
    ;;
  *)
    log "unsupported DEMO10_MODE=${MODE}; use auto, dry-run, or live"
    exit 2
    ;;
esac

log "output_dir=${OUTPUT_DIR}"
