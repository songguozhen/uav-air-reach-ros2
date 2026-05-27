#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PX4_GZ_MODELS="${PX4_GZ_MODELS:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models}"
PX4_GZ_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH:-/home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins}"
WORLD_FILE="${PACKAGE_DIR}/worlds/x500_arm_2dof_smoke.sdf"

if ! command -v gz >/dev/null 2>&1; then
  echo "ERROR: gz command not found" >&2
  exit 127
fi

if [ ! -d "${PX4_GZ_MODELS}" ]; then
  echo "ERROR: PX4 Gazebo model directory not found: ${PX4_GZ_MODELS}" >&2
  exit 2
fi

if [ ! -s "${WORLD_FILE}" ]; then
  echo "ERROR: smoke-test world not found: ${WORLD_FILE}" >&2
  exit 2
fi

if [ -n "${GZ_SIM_RESOURCE_PATH:-}" ]; then
  export GZ_SIM_RESOURCE_PATH="${PACKAGE_DIR}/models:${PX4_GZ_MODELS}:${GZ_SIM_RESOURCE_PATH}"
else
  export GZ_SIM_RESOURCE_PATH="${PACKAGE_DIR}/models:${PX4_GZ_MODELS}"
fi

if [ -d "${PX4_GZ_PLUGIN_PATH}" ]; then
  if [ -n "${GZ_SIM_SYSTEM_PLUGIN_PATH:-}" ]; then
    export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH}:${GZ_SIM_SYSTEM_PLUGIN_PATH}"
  else
    export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_GZ_PLUGIN_PATH}"
  fi
fi

echo "GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}"
echo "GZ_SIM_SYSTEM_PLUGIN_PATH=${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
echo "Loading ${WORLD_FILE}"

timeout 30s gz sim -s -r --iterations 1 "${WORLD_FILE}"
