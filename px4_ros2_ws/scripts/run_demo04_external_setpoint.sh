#!/usr/bin/env bash
set -euo pipefail

WS_DIR="${WS_DIR:-/home/clcwork/UAV_capture/px4_ros2_ws}"
DEMO04_MODE="${DEMO04_MODE:-bridge}"
DRY_RUN="${DRY_RUN:-0}"
INITIAL_X="${INITIAL_X:-0.0}"
INITIAL_Y="${INITIAL_Y:-0.0}"
INITIAL_Z="${INITIAL_Z:--2.0}"
VIS_DURATION="${VIS_DURATION:-120.0}"
TARGET_START_DELAY="${TARGET_START_DELAY:-15}"
TARGET_HOLD="${TARGET_HOLD:-18}"
BRIDGE_TARGET_TIMEOUT="${BRIDGE_TARGET_TIMEOUT:-25.0}"
BRIDGE_TARGET_JUMP_LIMIT="${BRIDGE_TARGET_JUMP_LIMIT:-2.5}"
BRIDGE_MAX_ALTITUDE="${BRIDGE_MAX_ALTITUDE:-5.0}"
BRIDGE_MIN_ALTITUDE="${BRIDGE_MIN_ALTITUDE:-0.5}"
BRIDGE_MAX_HORIZONTAL_RANGE="${BRIDGE_MAX_HORIZONTAL_RANGE:-5.0}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$WS_DIR/logs/demo04_external_setpoint/$STAMP"
VIS_DIR="$WS_DIR/visualizations/demo04_external_setpoint/$STAMP"
export RESET_STACK="${RESET_STACK:-1}"

case "$DEMO04_MODE" in
  bridge)
    CONTROL_SESSION="px4_uav_control_bridge"
    CONTROL_LOG="$LOG_DIR/uav_control_bridge.log"
    CONTROL_TITLE="Demo 04 External Setpoint Bridge"
    CONTROL_RUNNER="ros2 run px4_offboard_hover uav_control_bridge --ros-args -p initial_x:=$INITIAL_X -p initial_y:=$INITIAL_Y -p initial_z:=$INITIAL_Z -p target_timeout:=$BRIDGE_TARGET_TIMEOUT -p target_jump_limit:=$BRIDGE_TARGET_JUMP_LIMIT -p max_altitude:=$BRIDGE_MAX_ALTITUDE -p min_altitude:=$BRIDGE_MIN_ALTITUDE -p max_horizontal_range:=$BRIDGE_MAX_HORIZONTAL_RANGE"
    ;;
  legacy)
    CONTROL_SESSION="px4_demo04_external_setpoint"
    CONTROL_LOG="$LOG_DIR/demo04.log"
    CONTROL_TITLE="Demo 04 External Setpoint Interface"
    CONTROL_RUNNER="ros2 run px4_offboard_hover demo04_external_setpoint --ros-args -p initial_x:=$INITIAL_X -p initial_y:=$INITIAL_Y -p initial_z:=$INITIAL_Z"
    ;;
  *)
    echo "Unsupported DEMO04_MODE=$DEMO04_MODE. Use bridge or legacy." >&2
    exit 2
    ;;
esac

TARGET_SEQUENCE_COMMAND="sleep \"$TARGET_START_DELAY\" && \
  ros2 topic pub --times 3 -r 2 /uav/target_position geometry_msgs/msg/Point '{x: 2.0, y: 0.0, z: -2.0}' && sleep \"$TARGET_HOLD\" && \
  ros2 topic pub --times 3 -r 2 /uav/target_position geometry_msgs/msg/Point '{x: 2.0, y: 2.0, z: -2.0}' && sleep \"$TARGET_HOLD\" && \
  ros2 topic pub --times 3 -r 2 /uav/target_position geometry_msgs/msg/Point '{x: 0.0, y: 2.0, z: -2.0}' && sleep \"$TARGET_HOLD\" && \
  ros2 topic pub --times 3 -r 2 /uav/target_position geometry_msgs/msg/Point '{x: 0.0, y: 0.0, z: -2.0}'"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY_RUN=1"
  echo "mode=$DEMO04_MODE"
  echo "start_stack=$WS_DIR/scripts/start_stack.sh"
  echo "trajectory_recorder=VIS_DIR=\"$VIS_DIR\" VIS_DURATION=\"$VIS_DURATION\" VIS_TITLE=\"$CONTROL_TITLE\" VIS_DEMO_ID=\"demo04\" AVG_ERROR_PASS=\"0.9\" FINAL_ERROR_PASS=\"0.6\" MAX_SPEED_PASS=\"3.0\" \"$WS_DIR/scripts/run_trajectory_recorder.sh\""
  echo "control_session=$CONTROL_SESSION"
  echo "control_command=$CONTROL_RUNNER"
  echo "target_topic=/uav/target_position geometry_msgs/msg/Point"
  echo "target_sequence=$TARGET_SEQUENCE_COMMAND"
  echo "logs=$LOG_DIR"
  echo "visuals=$VIS_DIR"
  exit 0
fi

mkdir -p "$LOG_DIR" "$VIS_DIR"
"$WS_DIR/scripts/start_stack.sh"

tmux kill-session -t px4_trajectory_recorder 2>/dev/null || true
tmux new-session -d -s px4_trajectory_recorder \
  "VIS_DIR=\"$VIS_DIR\" VIS_DURATION=\"$VIS_DURATION\" VIS_TITLE=\"$CONTROL_TITLE\" VIS_DEMO_ID=\"demo04\" AVG_ERROR_PASS=\"0.9\" FINAL_ERROR_PASS=\"0.6\" MAX_SPEED_PASS=\"3.0\" \"$WS_DIR/scripts/run_trajectory_recorder.sh\" 2>&1 | tee \"$LOG_DIR/trajectory_recorder.log\""

tmux kill-session -t px4_demo04_external_setpoint 2>/dev/null || true
tmux kill-session -t px4_uav_control_bridge 2>/dev/null || true
tmux new-session -d -s "$CONTROL_SESSION" \
  "cd \"$WS_DIR\" && set +u && source /opt/ros/jazzy/setup.bash && source install/setup.bash && set -u && $CONTROL_RUNNER 2>&1 | tee \"$CONTROL_LOG\""

tmux kill-session -t px4_demo04_target_sequence 2>/dev/null || true
tmux new-session -d -s px4_demo04_target_sequence \
  "cd \"$WS_DIR\" && set +u && source /opt/ros/jazzy/setup.bash && source install/setup.bash && set -u && $TARGET_SEQUENCE_COMMAND 2>&1 | tee \"$LOG_DIR/target_sequence.log\""

echo "demo04 mode=$DEMO04_MODE"
echo "control session=$CONTROL_SESSION"
echo "visualizer session=px4_trajectory_recorder"
echo "target sequence session=px4_demo04_target_sequence"
echo "target topic=/uav/target_position geometry_msgs/msg/Point"
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
