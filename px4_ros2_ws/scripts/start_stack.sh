#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PX4_DIR="${PX4_DIR:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot}"
AGENT_DIR="${AGENT_DIR:-/home/clcwork/Micro-XRCE-DDS-Agent/build}"
RESET_STACK="${RESET_STACK:-0}"
STACK_READY_TIMEOUT="${STACK_READY_TIMEOUT:-60}"
STACK_SMOKE_ONLY="${STACK_SMOKE_ONLY:-0}"
PX4_STACK_LOG="${PX4_STACK_LOG:-/tmp/px4_gz_x500_tmux.log}"
XRCE_AGENT_LOG="${XRCE_AGENT_LOG:-/tmp/micro_xrce_agent.log}"
READINESS_RESULT_FILE="${READINESS_RESULT_FILE:-}"

record_readiness() {
  local status="$1"
  local reason="$2"
  local detail="$3"
  local line

  line="STACK_READY=${status} reason=${reason} detail=${detail}"
  printf '%s\n' "$line"
  if [ -n "$READINESS_RESULT_FILE" ]; then
    printf '%s\n' "$line" >"$READINESS_RESULT_FILE"
  fi
}

latest_preflight_failure() {
  grep -Ei \
    "preflight.*fail|fail.*preflight|health checks failed|takeoff denied|arming denied|commander check.*fail" \
    "$PX4_STACK_LOG" 2>/dev/null | tail -1 || true
}

if [ "$RESET_STACK" = "1" ]; then
  "$SCRIPT_DIR/stop_stack.sh"
  rm -f "$PX4_STACK_LOG" "$XRCE_AGENT_LOG" /tmp/px4_offboard_hover.log
fi

tmux has-session -t px4_gz_x500 2>/dev/null || \
  tmux new-session -d -s px4_gz_x500 \
    "cd \"$PX4_DIR\" && HEADLESS=1 make px4_sitl gz_x500 2>&1 | tee \"$PX4_STACK_LOG\""

tmux has-session -t micro_xrce_agent 2>/dev/null || \
  tmux new-session -d -s micro_xrce_agent \
    "cd \"$AGENT_DIR\" && ./MicroXRCEAgent udp4 -p 8888 2>&1 | tee \"$XRCE_AGENT_LOG\""

ready=0
failure_detail=""
for _ in $(seq 1 "$STACK_READY_TIMEOUT"); do
  if grep -q "Ready for takeoff" "$PX4_STACK_LOG" 2>/dev/null; then
    record_readiness YES ready_for_takeoff "PX4 reached Ready for takeoff"
    ready=1
    break
  fi
  failure_detail="$(latest_preflight_failure)"
  if [ "$STACK_SMOKE_ONLY" != "1" ] && grep -q "Preflight check: OK" "$PX4_STACK_LOG" 2>/dev/null; then
    record_readiness YES preflight_check_ok "PX4 reported Preflight check: OK"
    ready=1
    break
  fi
  if grep -q "pxh>" "$PX4_STACK_LOG" 2>/dev/null; then
    tmux send-keys -t px4_gz_x500 "param set NAV_DLL_ACT 0" C-m
    tmux send-keys -t px4_gz_x500 "commander check" C-m
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  if [ -z "$failure_detail" ]; then
    failure_detail="$(latest_preflight_failure)"
  fi
  if [ -n "$failure_detail" ]; then
    record_readiness NO preflight_failure "$failure_detail"
  else
    record_readiness NO timeout "no Ready for takeoff or preflight failure within ${STACK_READY_TIMEOUT}s"
  fi
fi

tmux ls

if [ "$STACK_SMOKE_ONLY" = "1" ]; then
  "$SCRIPT_DIR/stop_stack.sh"
  [ "$ready" -eq 1 ]
fi
