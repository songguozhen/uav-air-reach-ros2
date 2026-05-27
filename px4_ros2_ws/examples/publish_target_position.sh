#!/usr/bin/env bash
set -euo pipefail

WS_DIR="${WS_DIR:-/home/clcwork/UAV_capture/px4_ros2_ws}"
X_NORTH="${1:-${X_NORTH:-2.0}}"
Y_EAST="${2:-${Y_EAST:-0.0}}"
ALTITUDE="${3:-${ALTITUDE:-2.0}}"
RATE_HZ="${RATE_HZ:-2}"
TIMES="${TIMES:-3}"

if [ -f /opt/ros/jazzy/setup.bash ]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

if [ -f "$WS_DIR/install/setup.bash" ]; then
  # shellcheck disable=SC1091
  source "$WS_DIR/install/setup.bash"
fi

Z_NED="$(awk "BEGIN { printf \"%.6f\", -1.0 * ($ALTITUDE) }")"

ros2 topic pub --times "$TIMES" -r "$RATE_HZ" \
  /uav/target_position geometry_msgs/msg/Point \
  "{x: $X_NORTH, y: $Y_EAST, z: $Z_NED}"
