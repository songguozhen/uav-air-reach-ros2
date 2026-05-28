#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="/home/clcwork/UAV_capture/px4_ros2_ws"
cd "$WORKSPACE_ROOT"

DEMO_NAME="demo10_air_reach"
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
MODE="${DEMO10_MODE:-auto}"
OUTPUT_DIR="logs/${DEMO_NAME}/${TIMESTAMP}"
RUNNER_LOG="${OUTPUT_DIR}/runner.log"
READINESS_FILE="${OUTPUT_DIR}/stack_readiness.txt"
STAGE2_SOURCE_PYTHONPATH="${WORKSPACE_ROOT}/src/aerial_manip_eval:${WORKSPACE_ROOT}/src/aerial_manip_control:${WORKSPACE_ROOT}/src/aerial_manip_vision"

mkdir -p "$OUTPUT_DIR"

log() {
  printf '[demo10] %s\n' "$*" | tee -a "$RUNNER_LOG"
}

run_dry() {
  log "mode=dry-run output_dir=${OUTPUT_DIR}"
  PYTHONPATH="${STAGE2_SOURCE_PYTHONPATH}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m aerial_manip_eval.demo10_dry_run \
      --output-dir "$OUTPUT_DIR" \
      --timestamp "$TIMESTAMP" 2>&1 | tee -a "$RUNNER_LOG"
  python3 scripts/check_demo_10.py "$OUTPUT_DIR" 2>&1 | tee -a "$RUNNER_LOG"
}

check_live_prereqs() {
  local missing=0

  if [ ! -f install/setup.bash ]; then
    log "live prerequisite missing: install/setup.bash; run colcon build first"
    missing=1
  fi
  if [ ! -d /home/clcwork/UAV_capture/px4_ws/PX4-Autopilot ]; then
    log "live prerequisite missing: /home/clcwork/UAV_capture/px4_ws/PX4-Autopilot"
    missing=1
  fi
  if [ ! -x /home/clcwork/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent ]; then
    log "live prerequisite missing: /home/clcwork/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent"
    missing=1
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    log "live prerequisite missing: tmux"
    missing=1
  fi

  if [ "$missing" -ne 0 ]; then
    return 1
  fi

  set +u
  if ! source install/setup.bash; then
    set -u
    log "live prerequisite failed: could not source install/setup.bash"
    return 1
  fi
  set -u

  local pkg
  for pkg in px4_offboard_hover aerial_manip_control aerial_manip_eval aerial_manip_vision; do
    if ! ros2 pkg prefix "$pkg" >/dev/null 2>&1; then
      log "live prerequisite missing: ROS 2 package ${pkg}"
      missing=1
    fi
  done

  [ "$missing" -eq 0 ]
}

cleanup_live() {
  PIDS=""
  LIVE_CLEANED=0
}

sync_tmux_environment() {
  local name

  tmux start-server 2>/dev/null || return 0
  for name in PATH GZ_CONFIG_PATH LD_LIBRARY_PATH CMAKE_PREFIX_PATH AMENT_PREFIX_PATH; do
    if [ "${!name+x}" = "x" ]; then
      tmux set-environment -g "$name" "${!name}" 2>/dev/null || true
    else
      tmux set-environment -gu "$name" 2>/dev/null || true
    fi
  done
}

stop_live_processes() {
  if [ "${LIVE_CLEANED:-0}" = "1" ]; then
    return 0
  fi
  LIVE_CLEANED=1
  for pid in ${PIDS:-}; do
    kill "$pid" 2>/dev/null || true
  done
  if [ -n "${PIDS:-}" ]; then
    wait $PIDS 2>/dev/null || true
  fi
  scripts/stop_stack.sh >>"$RUNNER_LOG" 2>&1 || true
}

run_live_smoke() {
  log "mode=live-smoke output_dir=${OUTPUT_DIR}"
  log "live smoke checks PX4 readiness only, then stops the stack"

  if READINESS_RESULT_FILE="$READINESS_FILE" \
    STACK_SMOKE_ONLY=1 \
    STACK_READY_TIMEOUT="${DEMO10_STACK_READY_TIMEOUT:-75}" \
    RESET_STACK="${RESET_STACK:-1}" \
    scripts/start_stack.sh 2>&1 | tee -a "$RUNNER_LOG"; then
    printf 'RESULT=PASS mode=live-smoke reason=stack_ready\n' >"${OUTPUT_DIR}/result.txt"
    log "live smoke PASS: $(cat "$READINESS_FILE")"
  else
    printf 'RESULT=FAIL mode=live-smoke reason=stack_not_ready\n' >"${OUTPUT_DIR}/result.txt"
    if [ -f "$READINESS_FILE" ]; then
      log "live smoke FAIL: $(cat "$READINESS_FILE")"
    else
      log "live smoke FAIL: no readiness result was written"
    fi
    return 1
  fi

  cp /tmp/px4_gz_x500_tmux.log "${OUTPUT_DIR}/px4_gz_x500_tmux.log" 2>/dev/null || true
  cp /tmp/micro_xrce_agent.log "${OUTPUT_DIR}/micro_xrce_agent.log" 2>/dev/null || true
}

run_live() {
  if ! check_live_prereqs; then
    printf 'RESULT=FAIL mode=live reason=missing_live_prerequisite\n' >"${OUTPUT_DIR}/result.txt"
    return 2
  fi

  cleanup_live
  trap stop_live_processes EXIT INT TERM

  log "mode=live output_dir=${OUTPUT_DIR}"
  sync_tmux_environment
  if ! READINESS_RESULT_FILE="$READINESS_FILE" \
    RESET_STACK="${RESET_STACK:-1}" \
    STACK_READY_TIMEOUT="${DEMO10_STACK_READY_TIMEOUT:-75}" \
    scripts/start_stack.sh 2>&1 | tee -a "$RUNNER_LOG"; then
    log "start_stack.sh failed before live Demo 10 nodes could start"
    return 2
  fi
  if ! grep -q '^STACK_READY=YES ' "$READINESS_FILE" 2>/dev/null; then
    log "stack not ready; aborting live Demo 10 nodes: $(cat "$READINESS_FILE" 2>/dev/null || printf 'missing readiness file')"
    printf 'RESULT=FAIL mode=live reason=stack_not_ready\n' >"${OUTPUT_DIR}/result.txt"
    return 2
  fi

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

  sleep "${DEMO10_NODE_STARTUP_SEC:-12}"
  ros2 run aerial_manip_eval air_reach_demo --output-dir "$OUTPUT_DIR" \
    >>"${OUTPUT_DIR}/air_reach_demo.log" 2>&1
  python3 scripts/check_demo_10.py "$OUTPUT_DIR" 2>&1 | tee -a "$RUNNER_LOG"
  stop_live_processes
  trap - EXIT INT TERM
}

case "$MODE" in
  dry-run)
    run_dry
    ;;
  live-smoke)
    run_live_smoke
    ;;
  live)
    run_live
    ;;
  auto)
    log "mode=auto using dry-run; set DEMO10_MODE=live-smoke for bounded stack readiness or DEMO10_MODE=live for full PX4/Gazebo execution"
    run_dry
    ;;
  *)
    log "unsupported DEMO10_MODE=${MODE}; use auto, dry-run, live-smoke, or live"
    exit 2
    ;;
esac

log "output_dir=${OUTPUT_DIR}"
