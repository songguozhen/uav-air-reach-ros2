#!/usr/bin/env bash
set -euo pipefail

tmux kill-session -t px4_offboard_hover 2>/dev/null || true
tmux kill-session -t px4_demo02_waypoint_flight 2>/dev/null || true
tmux kill-session -t px4_demo03_circle_trajectory 2>/dev/null || true
tmux kill-session -t px4_demo04_external_setpoint 2>/dev/null || true
tmux kill-session -t px4_uav_control_bridge 2>/dev/null || true
tmux kill-session -t px4_demo04_target_sequence 2>/dev/null || true
tmux kill-session -t px4_trajectory_recorder 2>/dev/null || true
tmux kill-session -t micro_xrce_agent 2>/dev/null || true
tmux kill-session -t px4_gz_x500 2>/dev/null || true
pkill -f "gz sim .*/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/worlds/default.sdf" 2>/dev/null || true
