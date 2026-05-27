#!/usr/bin/env bash
set -euo pipefail

export http_proxy="${http_proxy:-http://127.0.0.1:7893}"
export https_proxy="${https_proxy:-http://127.0.0.1:7893}"
export HTTP_PROXY="${HTTP_PROXY:-$http_proxy}"
export HTTPS_PROXY="${HTTPS_PROXY:-$https_proxy}"
export all_proxy="${all_proxy:-socks5://127.0.0.1:7893}"
export ALL_PROXY="${ALL_PROXY:-$all_proxy}"

CODEX_BIN="${CODEX_BIN:-$HOME/.codex/packages/standalone/current/bin/codex}"
WORKDIR="${CODEX_WORKDIR:-$HOME/UAV_capture/px4_ws/PX4-Autopilot}"

if ! systemctl is-active --quiet mihomo; then
  echo "[error] mihomo is not running"
  exit 1
fi

if [ ! -x "$CODEX_BIN" ]; then
  echo "[error] standalone Codex not found at $CODEX_BIN"
  echo "Run: curl -fsSL https://chatgpt.com/codex/install.sh | sh"
  exit 1
fi

cd "$WORKDIR"
tmp_log="$(mktemp)"
if "$CODEX_BIN" remote-control start >"$tmp_log" 2>&1; then
  cat "$tmp_log"
  rm -f "$tmp_log"
  exit 0
fi

status="$("$CODEX_BIN" doctor 2>/dev/null | sed -n '/Background Server/,$p' || true)"
cat "$tmp_log"
rm -f "$tmp_log"

if printf '%s\n' "$status" | grep -q 'app-server   running'; then
  echo "[warn] remote-control reported a relay connection error, but local app-server is running."
  echo "[warn] Check ChatGPT app/account Remote Control availability if the host is not visible."
  exit 0
fi

exit 1
