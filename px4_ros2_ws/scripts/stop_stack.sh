#!/usr/bin/env bash
set -euo pipefail

PX4_DIR="${PX4_DIR:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot}"

kill_tmux_session() {
  tmux kill-session -t "$1" 2>/dev/null || true
}

terminate_matching() {
  local pattern="$1"
  local label="$2"

  if ! pgrep -f "$pattern" >/dev/null 2>&1; then
    return 0
  fi

  printf '[stop_stack] stopping %s\n' "$label"
  pkill -TERM -f "$pattern" 2>/dev/null || true
  sleep 2

  if pgrep -f "$pattern" >/dev/null 2>&1; then
    printf '[stop_stack] force stopping %s\n' "$label"
    pkill -KILL -f "$pattern" 2>/dev/null || true
  fi
}

wait_until_clear() {
  local pattern="$1"
  local label="$2"

  for _ in $(seq 1 10); do
    if ! pgrep -f "$pattern" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  printf '[stop_stack] warning: process still matched after cleanup: %s\n' "$label" >&2
  pgrep -af "$pattern" >&2 || true
}

kill_tmux_session px4_offboard_hover
kill_tmux_session px4_demo02_waypoint_flight
kill_tmux_session px4_demo03_circle_trajectory
kill_tmux_session px4_demo04_external_setpoint
kill_tmux_session px4_uav_control_bridge
kill_tmux_session px4_demo04_target_sequence
kill_tmux_session px4_trajectory_recorder
kill_tmux_session micro_xrce_agent
kill_tmux_session px4_gz_x500

terminate_matching "gz sim .*${PX4_DIR}/Tools/simulation/gz/worlds/default\\.sdf" \
  "Gazebo default.sdf with PX4 world path"
terminate_matching "gz sim --verbose=1 -r -s .*default\\.sdf" \
  "Gazebo server default.sdf"
terminate_matching "px4_sitl_default/bin/px4" "PX4 SITL"
terminate_matching "MicroXRCEAgent .*udp4 .*8888" "Micro XRCE-DDS Agent"

wait_until_clear "gz sim .*${PX4_DIR}/Tools/simulation/gz/worlds/default\\.sdf" \
  "Gazebo default.sdf with PX4 world path"
wait_until_clear "gz sim --verbose=1 -r -s .*default\\.sdf" \
  "Gazebo server default.sdf"
wait_until_clear "px4_sitl_default/bin/px4" "PX4 SITL"
wait_until_clear "MicroXRCEAgent .*udp4 .*8888" "Micro XRCE-DDS Agent"
