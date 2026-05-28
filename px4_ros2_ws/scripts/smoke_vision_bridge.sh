#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/home/clcwork/UAV_capture/px4_ros2_ws}"
PX4_GZ_MODELS="${PX4_GZ_MODELS:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models}"
PX4_GZ_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins}"
TIMESTAMP="${TIMESTAMP:-$(date +%Y%m%d_%H%M%S)}"
OUTPUT_DIR="${OUTPUT_DIR:-${WORKSPACE_ROOT}/visualizations/demo_07_camera/${TIMESTAMP}}"

GAZEBO_PACKAGE_DIR="${WORKSPACE_ROOT}/src/aerial_manip_gazebo"
VISION_PACKAGE_DIR="${WORKSPACE_ROOT}/src/aerial_manip_vision"
WORLD_FILE="${GAZEBO_PACKAGE_DIR}/worlds/x500_arm_2dof_smoke.sdf"
MODEL_FILE="${GAZEBO_PACKAGE_DIR}/models/x500_arm_2dof/model.sdf"
TARGET_MODEL_FILE="${GAZEBO_PACKAGE_DIR}/models/fiducial_target_aruco/model.sdf"
TARGET_TEXTURE_FILE="${GAZEBO_PACKAGE_DIR}/models/fiducial_target_aruco/materials/textures/aruco_4x4_23.png"
BRIDGE_CONFIG="${GAZEBO_PACKAGE_DIR}/config/front_camera_bridge.yaml"

GZ_IMAGE_TOPIC="/world/x500_arm_2dof_smoke/model/x500_arm_2dof/link/camera_link/sensor/camera/image"
ROS_IMAGE_TOPIC="/vision/front/image_raw"
ROS_CAMERA_INFO_TOPIC="/vision/front/camera_info"
ROS_TARGET_POSE_TOPIC="/vision/target_pose"

GZ_STARTUP_TIMEOUT="${GZ_STARTUP_TIMEOUT:-20}"
ROS_TOPIC_TIMEOUT="${ROS_TOPIC_TIMEOUT:-15}"
IMAGE_CAPTURE_TIMEOUT="${IMAGE_CAPTURE_TIMEOUT:-20}"
TARGET_POSE_TIMEOUT="${TARGET_POSE_TIMEOUT:-15}"

pass_count=0
warn_count=0
fail_count=0
pids=()

cd "$WORKSPACE_ROOT"
mkdir -p "$OUTPUT_DIR"

cleanup() {
  local pid
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  wait "${pids[@]}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

report() {
  local status="$1"
  local name="$2"
  local detail="$3"

  printf '%-4s %-34s %s\n' "$status" "$name" "$detail"
  case "$status" in
    PASS) pass_count=$((pass_count + 1)) ;;
    WARN) warn_count=$((warn_count + 1)) ;;
    FAIL) fail_count=$((fail_count + 1)) ;;
  esac
}

check_file() {
  local name="$1"
  local path="$2"

  if [ -s "$path" ]; then
    report PASS "$name" "path=$path"
  else
    report FAIL "$name" "missing_or_empty=$path"
  fi
}

check_contains() {
  local name="$1"
  local path="$2"
  local pattern="$3"

  if [ -s "$path" ] && grep -Fq "$pattern" "$path"; then
    report PASS "$name" "pattern=$pattern"
  else
    report FAIL "$name" "missing_pattern=$pattern path=$path"
  fi
}

source_ros_environment() {
  local restore_nounset=0
  case "$-" in
    *u*)
      restore_nounset=1
      set +u
      ;;
  esac

  if [ -f /opt/ros/jazzy/setup.bash ]; then
    # shellcheck disable=SC1091
    source /opt/ros/jazzy/setup.bash
  fi

  if [ -f "${WORKSPACE_ROOT}/install/setup.bash" ]; then
    # shellcheck disable=SC1091
    source "${WORKSPACE_ROOT}/install/setup.bash"
  fi

  if [ "$restore_nounset" -eq 1 ]; then
    set -u
  fi
}

configure_gazebo_environment() {
  if [ -n "${GZ_SIM_RESOURCE_PATH:-}" ]; then
    export GZ_SIM_RESOURCE_PATH="${GAZEBO_PACKAGE_DIR}/models:${PX4_GZ_MODELS}:${GZ_SIM_RESOURCE_PATH}"
  else
    export GZ_SIM_RESOURCE_PATH="${GAZEBO_PACKAGE_DIR}/models:${PX4_GZ_MODELS}"
  fi

  if [ -d "$PX4_GZ_PLUGIN_PATH" ]; then
    if [ -n "${GZ_SIM_SYSTEM_PLUGIN_PATH:-}" ]; then
      export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH}:${GZ_SIM_SYSTEM_PLUGIN_PATH}"
    else
      export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH}"
    fi
  fi
}

wait_for_gz_topic() {
  local topic="$1"
  local timeout_sec="$2"
  local deadline=$((SECONDS + timeout_sec))

  while [ "$SECONDS" -lt "$deadline" ]; do
    if gz topic -l 2>/dev/null | grep -Fxq "$topic"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_ros_topic() {
  local topic="$1"
  local timeout_sec="$2"
  local deadline=$((SECONDS + timeout_sec))

  while [ "$SECONDS" -lt "$deadline" ]; do
    if ros2 topic list 2>/dev/null | grep -Fxq "$topic"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_gazebo_server() {
  configure_gazebo_environment
  timeout 60s gz sim -s -r "$WORLD_FILE" >"${OUTPUT_DIR}/gz_sim.log" 2>&1 &
  local pid=$!
  pids+=("$pid")
  sleep 2
  if kill -0 "$pid" >/dev/null 2>&1; then
    report PASS "gazebo_server" "pid=$pid log=${OUTPUT_DIR}/gz_sim.log"
    return 0
  fi

  report FAIL "gazebo_server" "failed_to_start log=${OUTPUT_DIR}/gz_sim.log"
  return 1
}

start_camera_bridge() {
  ros2 launch aerial_manip_gazebo front_camera_bridge.launch.py >"${OUTPUT_DIR}/front_camera_bridge.log" 2>&1 &
  local pid=$!
  pids+=("$pid")
  sleep 2
  if kill -0 "$pid" >/dev/null 2>&1; then
    report PASS "ros_gz_bridge_process" "pid=$pid log=${OUTPUT_DIR}/front_camera_bridge.log"
    return 0
  fi

  report WARN "ros_gz_bridge_process" "failed_to_start log=${OUTPUT_DIR}/front_camera_bridge.log"
  return 1
}

capture_sample_frame() {
  local output_png="${OUTPUT_DIR}/sample_frame.png"
  local capture_log="${OUTPUT_DIR}/sample_frame_capture.log"

  if SMOKE_IMAGE_TOPIC="$ROS_IMAGE_TOPIC" SMOKE_IMAGE_OUT="$output_png" \
    timeout "${IMAGE_CAPTURE_TIMEOUT}s" python3 - <<'PY' >"$capture_log" 2>&1
import os
import sys

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class FrameGrabber(Node):
    def __init__(self, topic: str, output_path: str) -> None:
        super().__init__("vision_smoke_frame_grabber")
        self.bridge = CvBridge()
        self.output_path = output_path
        self.saved = False
        self.create_subscription(Image, topic, self.image_callback, 10)

    def image_callback(self, msg: Image) -> None:
        if self.saved:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        if not cv2.imwrite(self.output_path, frame):
            raise RuntimeError(f"cv2.imwrite failed for {self.output_path}")
        self.saved = True


def main() -> int:
    topic = os.environ["SMOKE_IMAGE_TOPIC"]
    output_path = os.environ["SMOKE_IMAGE_OUT"]
    rclpy.init()
    node = FrameGrabber(topic, output_path)
    try:
        while rclpy.ok() and not node.saved:
            rclpy.spin_once(node, timeout_sec=0.25)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0 if os.path.exists(output_path) else 1


sys.exit(main())
PY
  then
    report PASS "sample_frame" "path=$output_png"
    return 0
  fi

  printf 'sample_frame=not_captured\nreason=no image message was converted before timeout\nlog=%s\n' "$capture_log" >"${OUTPUT_DIR}/sample_frame_status.txt"
  report WARN "sample_frame" "not_captured status=${OUTPUT_DIR}/sample_frame_status.txt"
  return 1
}

verify_placeholder_target_pose() {
  ros2 launch aerial_manip_vision tag_target_pose.launch.py publish_placeholder:=true >"${OUTPUT_DIR}/placeholder_target_pose.log" 2>&1 &
  local pid=$!
  pids+=("$pid")
  sleep 2

  if timeout "${TARGET_POSE_TIMEOUT}s" ros2 topic echo "$ROS_TARGET_POSE_TOPIC" --once >"${OUTPUT_DIR}/placeholder_target_pose.yaml" 2>"${OUTPUT_DIR}/placeholder_target_pose.err"; then
    report PASS "placeholder_target_pose" "topic=$ROS_TARGET_POSE_TOPIC output=${OUTPUT_DIR}/placeholder_target_pose.yaml"
  else
    report FAIL "placeholder_target_pose" "no_message topic=$ROS_TARGET_POSE_TOPIC log=${OUTPUT_DIR}/placeholder_target_pose.log"
  fi

  kill "$pid" >/dev/null 2>&1 || true
  wait "$pid" >/dev/null 2>&1 || true
}

verify_live_target_pose() {
  ros2 launch aerial_manip_vision tag_target_pose.launch.py publish_placeholder:=false >"${OUTPUT_DIR}/live_target_pose.log" 2>&1 &
  local pid=$!
  pids+=("$pid")
  sleep 2

  if timeout "${TARGET_POSE_TIMEOUT}s" ros2 topic echo "$ROS_TARGET_POSE_TOPIC" --once >"${OUTPUT_DIR}/live_target_pose.yaml" 2>"${OUTPUT_DIR}/live_target_pose.err"; then
    report PASS "live_target_pose" "topic=$ROS_TARGET_POSE_TOPIC output=${OUTPUT_DIR}/live_target_pose.yaml"
  else
    printf 'live_target_pose=not_observed\nreason=no detected target pose before timeout; placeholder mode was not enabled for this live check\nlog=%s\n' "${OUTPUT_DIR}/live_target_pose.log" >"${OUTPUT_DIR}/live_target_pose_status.txt"
    report WARN "live_target_pose" "not_observed status=${OUTPUT_DIR}/live_target_pose_status.txt"
  fi

  kill "$pid" >/dev/null 2>&1 || true
  wait "$pid" >/dev/null 2>&1 || true
}

printf 'Vision Bridge Smoke\n'
printf 'timestamp=%s\n' "$TIMESTAMP"
printf 'workspace=%s\n' "$WORKSPACE_ROOT"
printf 'output_dir=%s\n\n' "$OUTPUT_DIR"

check_file "model:x500_arm_2dof" "$MODEL_FILE"
check_file "model:fiducial_target" "$TARGET_MODEL_FILE"
check_file "texture:aruco_4x4_23" "$TARGET_TEXTURE_FILE"
check_file "world:x500_arm_2dof_smoke" "$WORLD_FILE"
check_file "bridge_config" "$BRIDGE_CONFIG"
check_contains "model:camera_link" "$MODEL_FILE" "<child>camera_link</child>"
check_contains "world:fiducial_include" "$WORLD_FILE" "model://fiducial_target_aruco"
check_contains "bridge:image_topic" "$BRIDGE_CONFIG" "$ROS_IMAGE_TOPIC"
check_contains "bridge:camera_info_topic" "$BRIDGE_CONFIG" "$ROS_CAMERA_INFO_TOPIC"

source_ros_environment

if command -v ros2 >/dev/null 2>&1; then
  report PASS "ros2_cli" "path=$(command -v ros2)"
else
  report FAIL "ros2_cli" "missing; source /opt/ros/jazzy/setup.bash and install/setup.bash"
fi

if command -v gz >/dev/null 2>&1; then
  report PASS "gz_cli" "path=$(command -v gz)"
else
  report FAIL "gz_cli" "missing command=gz"
fi

if [ -d "$PX4_GZ_MODELS" ]; then
  report PASS "px4_gz_models" "path=$PX4_GZ_MODELS"
else
  report FAIL "px4_gz_models" "missing=$PX4_GZ_MODELS"
fi

if [ "$fail_count" -eq 0 ] && command -v gz >/dev/null 2>&1; then
  if start_gazebo_server && wait_for_gz_topic "$GZ_IMAGE_TOPIC" "$GZ_STARTUP_TIMEOUT"; then
    report PASS "gazebo_camera_topic" "topic=$GZ_IMAGE_TOPIC"
  else
    report FAIL "gazebo_camera_topic" "missing topic=$GZ_IMAGE_TOPIC log=${OUTPUT_DIR}/gz_sim.log"
  fi
fi

if command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix aerial_manip_vision >/dev/null 2>&1; then
  report PASS "ros_pkg:aerial_manip_vision" "prefix=$(ros2 pkg prefix aerial_manip_vision)"
  verify_placeholder_target_pose
else
  report FAIL "ros_pkg:aerial_manip_vision" "missing; run colcon build --packages-select aerial_manip_vision"
fi

if command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix ros_gz_bridge >/dev/null 2>&1; then
  report PASS "ros_pkg:ros_gz_bridge" "prefix=$(ros2 pkg prefix ros_gz_bridge)"
  if [ "$fail_count" -eq 0 ] && start_camera_bridge; then
    if wait_for_ros_topic "$ROS_IMAGE_TOPIC" "$ROS_TOPIC_TIMEOUT"; then
      report PASS "ros_image_topic" "topic=$ROS_IMAGE_TOPIC"
    else
      printf 'sample_frame=not_captured\nreason=%s did not appear before timeout\n' "$ROS_IMAGE_TOPIC" >"${OUTPUT_DIR}/sample_frame_status.txt"
      report WARN "ros_image_topic" "missing topic=$ROS_IMAGE_TOPIC status=${OUTPUT_DIR}/sample_frame_status.txt"
    fi

    if wait_for_ros_topic "$ROS_CAMERA_INFO_TOPIC" "$ROS_TOPIC_TIMEOUT"; then
      report PASS "ros_camera_info_topic" "topic=$ROS_CAMERA_INFO_TOPIC"
    else
      printf 'sample_frame=not_captured\nreason=%s did not appear before timeout\n' "$ROS_CAMERA_INFO_TOPIC" >"${OUTPUT_DIR}/sample_frame_status.txt"
      report WARN "ros_camera_info_topic" "missing topic=$ROS_CAMERA_INFO_TOPIC status=${OUTPUT_DIR}/sample_frame_status.txt"
    fi

    if wait_for_ros_topic "$ROS_IMAGE_TOPIC" 1 && wait_for_ros_topic "$ROS_CAMERA_INFO_TOPIC" 1; then
      capture_sample_frame || true
      verify_live_target_pose
    fi
  fi
else
  printf 'front_camera_bridge=not_started\nreason=ros_gz_bridge package is not available\n' >"${OUTPUT_DIR}/front_camera_bridge.log"
  printf 'sample_frame=not_captured\nreason=ros_gz_bridge package is not available; live image bridge skipped\n' >"${OUTPUT_DIR}/sample_frame_status.txt"
  report WARN "ros_pkg:ros_gz_bridge" "missing; skipped live bridge and sample capture"
fi

printf '\nSUMMARY pass=%d warn=%d fail=%d\n' "$pass_count" "$warn_count" "$fail_count"
printf 'output_dir=%s\n' "$OUTPUT_DIR"

if [ "$fail_count" -gt 0 ]; then
  printf 'RESULT=FAIL reason=critical_vision_smoke_check_failed\n'
  exit 1
fi

if [ "$warn_count" -gt 0 ]; then
  printf 'RESULT=WARN reason=vision_smoke_completed_with_warnings\n'
else
  printf 'RESULT=PASS reason=vision_smoke_verified\n'
fi
