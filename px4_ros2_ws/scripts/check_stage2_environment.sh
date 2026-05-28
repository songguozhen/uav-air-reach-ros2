#!/usr/bin/env bash
set -uo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/home/clcwork/UAV_capture/px4_ros2_ws}"
PX4_DIR="${PX4_DIR:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot}"
AGENT_DIR="${AGENT_DIR:-/home/clcwork/Micro-XRCE-DDS-Agent/build}"
LEROBOT_PYTHON="${LEROBOT_PYTHON:-/home/clcwork/miniconda3/envs/lerobot/bin/python}"

pass_count=0
warn_count=0
fail_count=0
live_ready=1
dry_run_ready=1

missing_ros_packages=()
missing_debian_packages=()
recheck_commands=()

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

add_recheck() {
  recheck_commands+=("$1")
}

check_file_nonempty() {
  local name="$1"
  local path="$2"
  local effect="${3:-live}"

  if [ -s "$path" ]; then
    report PASS "$name" "path=$path"
  else
    report FAIL "$name" "missing_or_empty=$path recheck=\"test -s $path\""
    add_recheck "test -s $path"
    if [ "$effect" = "live" ]; then
      live_ready=0
    fi
  fi
}

check_executable() {
  local name="$1"
  local path="$2"
  local effect="${3:-live}"

  if [ -x "$path" ]; then
    report PASS "$name" "path=$path"
  else
    report FAIL "$name" "missing_or_not_executable=$path recheck=\"test -x $path\""
    add_recheck "test -x $path"
    if [ "$effect" = "live" ]; then
      live_ready=0
    fi
  fi
}

check_python_lerobot() {
  local name="$1"
  local python_bin="$2"
  local effect="$3"
  local version

  if [ ! -x "$python_bin" ]; then
    report WARN "$name" "missing_python=$python_bin package=lerobot recheck=\"test -x $python_bin\""
    add_recheck "test -x $python_bin"
    if [ "$effect" = "dry-run" ]; then
      dry_run_ready=0
    fi
    return
  fi

  version="$("$python_bin" -c 'import importlib.metadata; print(importlib.metadata.version("lerobot"))' 2>/dev/null)"
  if [ -n "$version" ]; then
    report PASS "$name" "python=$python_bin lerobot_version=$version"
  else
    report WARN "$name" "python=$python_bin missing_package=lerobot recheck=\"$python_bin -c 'import importlib.util; print(importlib.util.find_spec(\"lerobot\"))'\""
    add_recheck "$python_bin -c 'import importlib.util; print(importlib.util.find_spec(\"lerobot\"))'"
    if [ "$effect" = "dry-run" ]; then
      dry_run_ready=0
    fi
  fi
}

check_ros_package() {
  local ros_pkg="$1"
  local deb_pkg="$2"

  if command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix "$ros_pkg" >/dev/null 2>&1; then
    local prefix
    prefix="$(ros2 pkg prefix "$ros_pkg" 2>/dev/null)"
    report PASS "ros2_pkg:$ros_pkg" "prefix=$prefix"
  else
    report WARN "ros2_pkg:$ros_pkg" "missing_package=$ros_pkg likely_debian_package=$deb_pkg recheck=\"ros2 pkg prefix $ros_pkg\""
    missing_ros_packages+=("$ros_pkg")
    missing_debian_packages+=("$deb_pkg")
    add_recheck "ros2 pkg prefix $ros_pkg"
    live_ready=0
  fi
}

timestamp="$(date +%Y-%m-%dT%H:%M:%S%z)"

printf 'Stage 2 Environment Preflight\n'
printf 'timestamp=%s\n' "$timestamp"
printf 'workspace=%s\n' "$WORKSPACE_ROOT"
printf 'px4_dir=%s\n' "$PX4_DIR"
printf 'agent_dir=%s\n' "$AGENT_DIR"
printf '\n'

if [ "$(pwd)" = "$WORKSPACE_ROOT" ]; then
  report PASS "workspace_root" "pwd=$WORKSPACE_ROOT"
else
  report WARN "workspace_root" "pwd=$(pwd) expected=$WORKSPACE_ROOT recheck=\"cd $WORKSPACE_ROOT\""
  add_recheck "cd $WORKSPACE_ROOT"
fi

if command -v ros2 >/dev/null 2>&1; then
  report PASS "ros2_cli" "path=$(command -v ros2)"
else
  report FAIL "ros2_cli" "missing_command=ros2 recheck=\"source /opt/ros/jazzy/setup.bash && command -v ros2\""
  add_recheck "source /opt/ros/jazzy/setup.bash && command -v ros2"
  live_ready=0
fi

if [ "${ROS_DISTRO:-}" = "jazzy" ] && [ -d /opt/ros/jazzy ]; then
  report PASS "ros2_distro" "ROS_DISTRO=jazzy prefix=/opt/ros/jazzy"
elif [ -d /opt/ros/jazzy ]; then
  report WARN "ros2_distro" "ROS_DISTRO=${ROS_DISTRO:-unset} expected=jazzy recheck=\"source /opt/ros/jazzy/setup.bash && echo \\$ROS_DISTRO\""
  add_recheck "source /opt/ros/jazzy/setup.bash && echo \$ROS_DISTRO"
  live_ready=0
else
  report FAIL "ros2_distro" "missing_prefix=/opt/ros/jazzy expected=ROS_DISTRO=jazzy recheck=\"test -d /opt/ros/jazzy\""
  add_recheck "test -d /opt/ros/jazzy"
  live_ready=0
fi

if command -v gz >/dev/null 2>&1; then
  gz_version="$(gz sim --versions 2>/dev/null | head -n 1)"
  report PASS "gazebo_sim" "path=$(command -v gz) version=${gz_version:-unknown}"
else
  report FAIL "gazebo_sim" "missing_command=gz recheck=\"command -v gz && gz sim --versions\""
  add_recheck "command -v gz && gz sim --versions"
  live_ready=0
fi

check_executable "px4_sitl_binary" "$PX4_DIR/build/px4_sitl_default/bin/px4" live
check_file_nonempty "px4_model:x500" "$PX4_DIR/Tools/simulation/gz/models/x500/model.sdf" live
check_file_nonempty "px4_model:x500_mono_cam" "$PX4_DIR/Tools/simulation/gz/models/x500_mono_cam/model.sdf" live
check_file_nonempty "px4_model:mono_cam" "$PX4_DIR/Tools/simulation/gz/models/mono_cam/model.sdf" live
check_file_nonempty "px4_model:arucotag" "$PX4_DIR/Tools/simulation/gz/models/arucotag/model.sdf" live
check_file_nonempty "stage2_model:x500_arm_2dof" "$WORKSPACE_ROOT/src/aerial_manip_gazebo/models/x500_arm_2dof/model.sdf" live
check_file_nonempty "stage2_model:fiducial_target" "$WORKSPACE_ROOT/src/aerial_manip_gazebo/models/fiducial_target_aruco/model.sdf" live
check_file_nonempty "stage2_world:smoke" "$WORKSPACE_ROOT/src/aerial_manip_gazebo/worlds/x500_arm_2dof_smoke.sdf" live

if command -v MicroXRCEAgent >/dev/null 2>&1; then
  report PASS "micro_xrce_agent" "path=$(command -v MicroXRCEAgent)"
else
  check_executable "micro_xrce_agent" "$AGENT_DIR/MicroXRCEAgent" live
fi

check_ros_package "ros_gz_bridge" "ros-jazzy-ros-gz-bridge"
check_ros_package "gz_ros2_control" "ros-jazzy-gz-ros2-control"
check_ros_package "controller_manager" "ros-jazzy-controller-manager"
check_ros_package "joint_state_broadcaster" "ros-jazzy-joint-state-broadcaster"
check_ros_package "forward_command_controller" "ros-jazzy-forward-command-controller"
check_ros_package "joint_trajectory_controller" "ros-jazzy-joint-trajectory-controller"

active_python="$(command -v python3 2>/dev/null || true)"
if [ -n "$active_python" ]; then
  check_python_lerobot "lerobot_active_python" "$active_python" "optional"
else
  report WARN "lerobot_active_python" "missing_command=python3 package=lerobot recheck=\"command -v python3\""
  add_recheck "command -v python3"
fi
check_python_lerobot "lerobot_conda_python" "$LEROBOT_PYTHON" "optional"

printf '\n'
if [ "${#missing_ros_packages[@]}" -gt 0 ]; then
  printf 'MISSING_ROS_PACKAGES=%s\n' "${missing_ros_packages[*]}"
  printf 'LIKELY_DEBIAN_PACKAGES=%s\n' "${missing_debian_packages[*]}"
else
  printf 'MISSING_ROS_PACKAGES=none\n'
fi

if [ "${#recheck_commands[@]}" -gt 0 ]; then
  printf '\nRecheck commands:\n'
  for cmd in "${recheck_commands[@]}"; do
    printf '  %s\n' "$cmd"
  done
fi

printf '\n'
printf 'SUMMARY pass=%d warn=%d fail=%d\n' "$pass_count" "$warn_count" "$fail_count"

if [ "$fail_count" -gt 0 ]; then
  printf 'RESULT=FAIL live_ready=NO dry_run_ready=%s reason=critical_preflight_failure\n' "$([ "$dry_run_ready" -eq 1 ] && printf YES || printf NO)"
  exit 1
elif [ "$live_ready" -eq 0 ]; then
  printf 'RESULT=WARN live_ready=NO dry_run_ready=%s reason=missing_live_prerequisites\n' "$([ "$dry_run_ready" -eq 1 ] && printf YES || printf NO)"
  exit 0
elif [ "$warn_count" -gt 0 ]; then
  printf 'RESULT=WARN live_ready=YES dry_run_ready=%s reason=optional_warnings\n' "$([ "$dry_run_ready" -eq 1 ] && printf YES || printf NO)"
  exit 0
else
  printf 'RESULT=PASS live_ready=YES dry_run_ready=YES reason=all_required_checks_passed\n'
  exit 0
fi
