#!/usr/bin/env bash
set -euo pipefail

PX4_DIR="${PX4_DIR:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot}"
AGENT_DIR="${AGENT_DIR:-/home/clcwork/Micro-XRCE-DDS-Agent/build}"
RESET_STACK="${RESET_STACK:-0}"

if [ "$RESET_STACK" = "1" ]; then
  tmux kill-session -t px4_offboard_hover 2>/dev/null || true
  tmux kill-session -t px4_demo02_waypoint_flight 2>/dev/null || true
  tmux kill-session -t px4_demo03_circle_trajectory 2>/dev/null || true
  tmux kill-session -t px4_demo04_external_setpoint 2>/dev/null || true
  tmux kill-session -t px4_uav_control_bridge 2>/dev/null || true
  tmux kill-session -t px4_demo04_target_sequence 2>/dev/null || true
  tmux kill-session -t px4_trajectory_recorder 2>/dev/null || true
  tmux kill-session -t micro_xrce_agent 2>/dev/null || true
  tmux kill-session -t px4_gz_x500 2>/dev/null || true
  pkill -f "gz sim .*${PX4_DIR}/Tools/simulation/gz/worlds/default.sdf" 2>/dev/null || true
  rm -f /tmp/px4_gz_x500_tmux.log /tmp/micro_xrce_agent.log /tmp/px4_offboard_hover.log
fi

tmux has-session -t px4_gz_x500 2>/dev/null || \
  tmux new-session -d -s px4_gz_x500 \
    "cd \"$PX4_DIR\" && HEADLESS=1 make px4_sitl gz_x500 2>&1 | tee /tmp/px4_gz_x500_tmux.log"

tmux has-session -t micro_xrce_agent 2>/dev/null || \
  tmux new-session -d -s micro_xrce_agent \
    "cd \"$AGENT_DIR\" && ./MicroXRCEAgent udp4 -p 8888 2>&1 | tee /tmp/micro_xrce_agent.log"

for _ in $(seq 1 60); do
  if grep -q "Preflight check: OK\\|Ready for takeoff" /tmp/px4_gz_x500_tmux.log 2>/dev/null; then
    break
  fi
  if grep -q "pxh>" /tmp/px4_gz_x500_tmux.log 2>/dev/null; then
    tmux send-keys -t px4_gz_x500 "param set NAV_DLL_ACT 0" C-m
    tmux send-keys -t px4_gz_x500 "commander check" C-m
  fi
  sleep 1
done

tmux ls
