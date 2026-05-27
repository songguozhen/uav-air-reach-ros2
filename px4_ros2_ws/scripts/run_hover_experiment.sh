#!/usr/bin/env bash
set -euo pipefail

WS_DIR="${WS_DIR:-/home/clcwork/UAV_capture/px4_ros2_ws}"
ALTITUDE="${ALTITUDE:-2.0}"
VERIFY_DURATION="${VERIFY_DURATION:-25}"
HOVER_DURATION="${HOVER_DURATION:-45.0}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$WS_DIR/logs/offboard_hover/$STAMP"
export RESET_STACK="${RESET_STACK:-1}"

mkdir -p "$LOG_DIR"

"$WS_DIR/scripts/start_stack.sh"

cd "$WS_DIR"
set +u
source /opt/ros/jazzy/setup.bash
source "$WS_DIR/install/setup.bash"
set -u

tmux kill-session -t px4_offboard_hover 2>/dev/null || true
tmux new-session -d -s px4_offboard_hover \
  "cd \"$WS_DIR\" && set +u && source /opt/ros/jazzy/setup.bash && source install/setup.bash && set -u && ros2 run px4_offboard_hover hover --ros-args -p altitude:=$ALTITUDE -p hover_duration:=$HOVER_DURATION -p land_on_exit:=true 2>&1 | tee \"$LOG_DIR/hover.log\""

sleep 4
ros2 run px4_offboard_hover verify_hover \
  --duration "$VERIFY_DURATION" \
  --target-z "-$ALTITUDE" \
  | tee "$LOG_DIR/verify.log"

tmux send-keys -t px4_gz_x500 "commander status" C-m || true
tail -80 /tmp/px4_gz_x500_tmux.log > "$LOG_DIR/px4_tail.log" || true
tail -80 /tmp/micro_xrce_agent.log > "$LOG_DIR/agent_tail.log" || true

echo "logs=$LOG_DIR"
