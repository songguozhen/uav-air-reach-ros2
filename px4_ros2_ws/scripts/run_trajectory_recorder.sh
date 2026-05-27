#!/usr/bin/env bash
set -euo pipefail

WS_DIR="${WS_DIR:-/home/clcwork/UAV_capture/px4_ros2_ws}"
VIS_DIR="${VIS_DIR:?VIS_DIR is required}"
VIS_DURATION="${VIS_DURATION:-90.0}"
VIS_TITLE="${VIS_TITLE:-PX4 Trajectory}"
VIS_DEMO_ID="${VIS_DEMO_ID:-generic}"
VIS_FPS="${VIS_FPS:-12}"
MAKE_VIDEO="${MAKE_VIDEO:-true}"
MAX_SPEED_PASS="${MAX_SPEED_PASS:-3.0}"
AVG_ERROR_PASS="${AVG_ERROR_PASS:-0.9}"
MAX_ERROR_PASS="${MAX_ERROR_PASS:-2.0}"
HEIGHT_ERROR_PASS="${HEIGHT_ERROR_PASS:-0.35}"
FINAL_ERROR_PASS="${FINAL_ERROR_PASS:-0.6}"
MIN_SAMPLES_PASS="${MIN_SAMPLES_PASS:-40}"
CONDA_ENV_DIR="${CONDA_ENV_DIR:-/home/clcwork/miniconda3/envs/lerobot}"

mkdir -p "$VIS_DIR"
cd "$WS_DIR"
export PATH="$CONDA_ENV_DIR/bin:$PATH"
set +u
source /opt/ros/jazzy/setup.bash
source "$WS_DIR/install/setup.bash"
set -u

echo "conda_env_dir=$CONDA_ENV_DIR"
echo "ffmpeg=$(command -v ffmpeg || true)"

ros2 run px4_offboard_hover trajectory_recorder --ros-args \
  -p output_dir:="$VIS_DIR" \
  -p duration:="$VIS_DURATION" \
  -p title:="$VIS_TITLE" \
  -p demo_id:="$VIS_DEMO_ID" \
  -p fps:="$VIS_FPS" \
  -p make_video:="$MAKE_VIDEO" \
  -p max_speed_pass:="$MAX_SPEED_PASS" \
  -p avg_error_pass:="$AVG_ERROR_PASS" \
  -p max_error_pass:="$MAX_ERROR_PASS" \
  -p height_error_pass:="$HEIGHT_ERROR_PASS" \
  -p final_error_pass:="$FINAL_ERROR_PASS" \
  -p min_samples_pass:="$MIN_SAMPLES_PASS"
