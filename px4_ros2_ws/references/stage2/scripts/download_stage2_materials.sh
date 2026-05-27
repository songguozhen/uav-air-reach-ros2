#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REF_DIR="$ROOT_DIR/references/stage2"
PX4_MODELS="/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models"
LOG_DIR="$ROOT_DIR/codex-logs"
LOG_FILE="$LOG_DIR/010-download-stage2-materials.log"

mkdir -p "$REF_DIR/official" "$REF_DIR/papers" "$REF_DIR/local_px4_models" "$LOG_DIR"

download() {
  local url="$1"
  local output="$2"
  echo "DOWNLOAD $url -> $output"
  curl -L --fail --retry 2 --connect-timeout 20 --max-time 120 \
    -A "Mozilla/5.0 Codex stage2 material downloader" \
    "$url" -o "$output"
}

copy_model() {
  local model="$1"
  local src="$PX4_MODELS/$model"
  local dst="$REF_DIR/local_px4_models/$model"
  echo "COPY $src -> $dst"
  mkdir -p "$dst"
  cp -f "$src/model.sdf" "$dst/model.sdf"
  if [ -f "$src/model.config" ]; then
    cp -f "$src/model.config" "$dst/model.config"
  fi
}

{
  echo "# Stage 2 material download"
  echo "START $(date --iso-8601=seconds)"

  download "https://docs.px4.io/main/en/ros2/user_guide" "$REF_DIR/official/px4_ros2_user_guide.html"
  download "https://docs.px4.io/main/en/middleware/uxrce_dds.html" "$REF_DIR/official/px4_uxrce_dds.html"
  download "https://docs.px4.io/main/en/flight_modes/offboard" "$REF_DIR/official/px4_offboard_mode.html"
  download "https://gazebosim.org/docs/harmonic/ros2_overview/" "$REF_DIR/official/gazebo_harmonic_ros2_overview.html"
  download "https://gazebosim.org/docs/harmonic/sensors/" "$REF_DIR/official/gazebo_harmonic_sensors.html"
  download "https://gazebosim.org/libs/sdformat" "$REF_DIR/official/sdformat.html"
  download "https://docs.ros.org/en/ros2_packages/jazzy/api/ros_gz_bridge/" "$REF_DIR/official/ros_gz_bridge_jazzy.html"
  download "https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html" "$REF_DIR/official/gz_ros2_control_jazzy.html"
  download "https://huggingface.co/docs/lerobot/lerobot-dataset-v3" "$REF_DIR/official/lerobot_dataset_v3.html"
  download "https://huggingface.co/docs/lerobot/main/en/async" "$REF_DIR/official/lerobot_async_inference.html"
  download "https://huggingface.co/docs/lerobot/main/en/smolvla" "$REF_DIR/official/lerobot_smolvla.html"

  download "https://arxiv.org/pdf/2504.10334" "$REF_DIR/papers/flying_hand_2504.10334.pdf"
  download "https://arxiv.org/pdf/2601.21602" "$REF_DIR/papers/air_vla_2601.21602.pdf"
  download "https://www.sciencedirect.com/science/article/pii/S0921889017305535" "$REF_DIR/papers/aerial_manipulation_survey.html" || true

  copy_model x500
  copy_model x500_mono_cam
  copy_model mono_cam
  copy_model arucotag

  echo "FILES"
  find "$REF_DIR" -type f | sort
  echo "END $(date --iso-8601=seconds)"
} | tee "$LOG_FILE"
