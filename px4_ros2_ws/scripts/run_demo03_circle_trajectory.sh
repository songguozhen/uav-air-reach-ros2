#!/usr/bin/env bash
set -euo pipefail

WS_DIR="${WS_DIR:-/home/clcwork/UAV_capture/px4_ros2_ws}"
RADIUS="${RADIUS:-1.5}"
ALTITUDE="${ALTITUDE:-2.0}"
DURATION="${DURATION:-60.0}"
VIS_DURATION="${VIS_DURATION:-75.0}"
ANGULAR_SPEED="${ANGULAR_SPEED:-0.35}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$WS_DIR/logs/demo03_circle_trajectory/$STAMP"
VIS_DIR="$WS_DIR/visualizations/demo03_circle_trajectory/$STAMP"
export RESET_STACK="${RESET_STACK:-1}"

mkdir -p "$LOG_DIR" "$VIS_DIR"
"$WS_DIR/scripts/start_stack.sh"

tmux kill-session -t px4_trajectory_recorder 2>/dev/null || true
tmux new-session -d -s px4_trajectory_recorder \
  "VIS_DIR=\"$VIS_DIR\" VIS_DURATION=\"$VIS_DURATION\" VIS_TITLE=\"Demo 03 Circle Trajectory\" VIS_DEMO_ID=\"demo03\" AVG_ERROR_PASS=\"0.8\" HEIGHT_ERROR_PASS=\"0.35\" MAX_SPEED_PASS=\"3.0\" \"$WS_DIR/scripts/run_trajectory_recorder.sh\" 2>&1 | tee \"$LOG_DIR/trajectory_recorder.log\""

tmux kill-session -t px4_demo03_circle_trajectory 2>/dev/null || true
tmux new-session -d -s px4_demo03_circle_trajectory \
  "cd \"$WS_DIR\" && set +u && source /opt/ros/jazzy/setup.bash && source install/setup.bash && set -u && ros2 run px4_offboard_hover demo03_circle_trajectory --ros-args -p radius:=$RADIUS -p altitude:=$ALTITUDE -p duration:=$DURATION -p angular_speed:=$ANGULAR_SPEED -p land_on_exit:=true 2>&1 | tee \"$LOG_DIR/demo03.log\""

echo "demo03 session=px4_demo03_circle_trajectory"
echo "visualizer session=px4_trajectory_recorder"
echo "visual outputs will be written after ${VIS_DURATION}s"
echo "logs=$LOG_DIR"
echo "visuals=$VIS_DIR"
while tmux has-session -t px4_trajectory_recorder 2>/dev/null; do
  sleep 2
done
echo "trajectory_csv=$VIS_DIR/trajectory.csv"
echo "trajectory_3d=$VIS_DIR/trajectory_3d.png"
echo "xy_path=$VIS_DIR/xy_path.png"
echo "height_curve=$VIS_DIR/height_curve.png"
echo "speed_curve=$VIS_DIR/speed_curve.png"
echo "tracking_error=$VIS_DIR/tracking_error.png"
echo "video=$VIS_DIR/trajectory.mp4"
echo "summary=$VIS_DIR/summary.md"
echo "result=$VIS_DIR/result.txt"
cat "$VIS_DIR/result.txt" 2>/dev/null || true
