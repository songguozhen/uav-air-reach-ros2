#!/usr/bin/env bash
set -euo pipefail

# Codex CLI command. Permission and sandbox defaults are read from Codex config.
# If the local CLI changes flags, override this variable:
#   CODEX_CMD=(codex exec) ./run_codex_queue.sh
# or edit only this line.
CODEX_CMD=(${CODEX_CMD:-codex exec})

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$ROOT_DIR/codex-tasks"
LOG_DIR="$ROOT_DIR/codex-logs"
USER_ENV_FILE="${CODEX_QUEUE_ENV_FILE:-$HOME/.config/uav_capture/codex_queue.env}"
DRY_RUN=0
FROM_PREFIX=""
SINGLE_TASK=""
STARTED_AT="$(date --iso-8601=seconds)"
CURRENT_TASK=""
FAILED_TASK=""
LAST_LOG_FILE=""
RAN_TASKS=0
SKIPPED_TASKS=0

usage() {
  cat <<'EOF'
Usage:
  ./run_codex_queue.sh
  ./run_codex_queue.sh --dry-run
  ./run_codex_queue.sh --from 003
  ./run_codex_queue.sh --from 006
  ./run_codex_queue.sh --task codex-tasks/004-design-uav-control-api.md

Environment:
  CODEX_CMD="codex exec"
    Override if your Codex CLI uses different permission flags.

  CODEX_WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
    Send a batch-end notification through a WeCom/Enterprise WeChat robot.

  SERVERCHAN_SENDKEY="SCT..."
    Send a batch-end notification through ServerChan.

  PUSHPLUS_TOKEN="..."
    Send a batch-end notification through PushPlus.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --from)
      FROM_PREFIX="${2:?--from requires a task prefix, for example 003}"
      shift 2
      ;;
    --task)
      SINGLE_TASK="${2:?--task requires a task file path}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"

if [ -f "$USER_ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$USER_ENV_FILE"
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex CLI not found in PATH" >&2
  exit 127
fi

if [ ! -f "$ROOT_DIR/AGENTS.md" ]; then
  echo "ERROR: AGENTS.md not found" >&2
  exit 1
fi

if [ ! -f "$ROOT_DIR/codex.md" ]; then
  echo "ERROR: codex.md not found" >&2
  exit 1
fi

if [ ! -d "$TASK_DIR" ]; then
  echo "ERROR: codex-tasks/ not found" >&2
  exit 1
fi

mkdir -p "$LOG_DIR"

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])'
}

send_wechat_notification() {
  local status="$1"
  local ended_at
  local title
  local body
  local escaped_body
  local webhook_payload
  local sent=0

  ended_at="$(date --iso-8601=seconds)"
  if [ "$status" -eq 0 ]; then
    title="Codex task queue completed"
  else
    title="Codex task queue failed"
  fi

  body="$(cat <<EOF
${title}
workspace: ${ROOT_DIR}
started_at: ${STARTED_AT}
ended_at: ${ended_at}
from: ${FROM_PREFIX:-all}
single_task: ${SINGLE_TASK:-none}
dry_run: ${DRY_RUN}
ran_tasks: ${RAN_TASKS}
skipped_tasks: ${SKIPPED_TASKS}
failed_task: ${FAILED_TASK:-none}
current_task: ${CURRENT_TASK:-none}
last_log: ${LAST_LOG_FILE:-none}
exit_status: ${status}
EOF
)"

  if ! command -v curl >/dev/null 2>&1; then
    echo "NOTIFY skipped: curl not found"
    return 0
  fi

  if [ -n "${CODEX_WECHAT_WEBHOOK_URL:-}" ]; then
    escaped_body="$(printf '%s' "$body" | json_escape)"
    webhook_payload="{\"msgtype\":\"text\",\"text\":{\"content\":\"${escaped_body}\"}}"
    if curl -fsS -m 10 \
      -H 'Content-Type: application/json' \
      -d "$webhook_payload" \
      "$CODEX_WECHAT_WEBHOOK_URL" >/dev/null; then
      echo "NOTIFY sent: CODEX_WECHAT_WEBHOOK_URL"
      sent=1
    else
      echo "NOTIFY failed: CODEX_WECHAT_WEBHOOK_URL" >&2
    fi
  fi

  if [ -n "${SERVERCHAN_SENDKEY:-}" ]; then
    if curl -fsS -m 10 \
      --data-urlencode "title=${title}" \
      --data-urlencode "desp=${body}" \
      "https://sctapi.ftqq.com/${SERVERCHAN_SENDKEY}.send" >/dev/null; then
      echo "NOTIFY sent: SERVERCHAN_SENDKEY"
      sent=1
    else
      echo "NOTIFY failed: SERVERCHAN_SENDKEY" >&2
    fi
  fi

  if [ -n "${PUSHPLUS_TOKEN:-}" ]; then
    escaped_body="$(printf '%s' "$body" | json_escape)"
    webhook_payload="{\"token\":\"${PUSHPLUS_TOKEN}\",\"title\":\"${title}\",\"content\":\"${escaped_body}\",\"template\":\"txt\"}"
    if curl -fsS -m 10 \
      -H 'Content-Type: application/json' \
      -d "$webhook_payload" \
      "https://www.pushplus.plus/send" >/dev/null; then
      echo "NOTIFY sent: PUSHPLUS_TOKEN"
      sent=1
    else
      echo "NOTIFY failed: PUSHPLUS_TOKEN" >&2
    fi
  fi

  if [ "$sent" -eq 0 ]; then
    echo "NOTIFY skipped: set CODEX_WECHAT_WEBHOOK_URL, SERVERCHAN_SENDKEY, or PUSHPLUS_TOKEN"
  fi
}

on_exit() {
  local status="$?"
  send_wechat_notification "$status" || true
  exit "$status"
}

trap on_exit EXIT

task_stem() {
  basename "$1" .md
}

run_task() {
  local task_file="$1"
  local stem
  local done_file
  local stamp
  local log_file

  stem="$(task_stem "$task_file")"
  done_file="$LOG_DIR/$stem.done"
  stamp="$(date +%Y%m%d_%H%M%S)"
  log_file="$LOG_DIR/${stem}-${stamp}.log"
  CURRENT_TASK="$task_file"
  LAST_LOG_FILE="$log_file"

  if [ -z "$SINGLE_TASK" ] && [ -f "$done_file" ]; then
    echo "SKIP $task_file already done: $done_file"
    SKIPPED_TASKS=$((SKIPPED_TASKS + 1))
    return 0
  fi

  echo "TASK $task_file"
  echo "LOG  $log_file"
  echo "START $(date --iso-8601=seconds)"

  if [ "$DRY_RUN" = "1" ]; then
    echo "DRY-RUN: { codex.md + $task_file } | ${CODEX_CMD[*]} | tee $log_file"
    RAN_TASKS=$((RAN_TASKS + 1))
    return 0
  fi

  set +e
  {
    echo "# Required workspace rules"
    echo
    cat "$ROOT_DIR/codex.md"
    echo
    echo "# Task file"
    echo
    cat "$task_file"
  } | "${CODEX_CMD[@]}" 2>&1 | tee "$log_file"
  local status=${PIPESTATUS[0]}
  set -e

  if [ "$status" -eq 0 ]; then
    touch "$done_file"
    RAN_TASKS=$((RAN_TASKS + 1))
    echo "END   $(date --iso-8601=seconds)"
    echo "DONE $task_file"
  else
    FAILED_TASK="$task_file"
    echo "END   $(date --iso-8601=seconds)"
    echo "FAIL $task_file status=$status" >&2
    echo "See log: $log_file" >&2
    exit "$status"
  fi
}

if [ -n "$SINGLE_TASK" ]; then
  if [ ! -f "$SINGLE_TASK" ]; then
    echo "ERROR: task file not found: $SINGLE_TASK" >&2
    exit 1
  fi
  run_task "$SINGLE_TASK"
  exit 0
fi

mapfile -t TASKS < <(find "$TASK_DIR" -maxdepth 1 -type f -name "*.md" | sort)

if [ "${#TASKS[@]}" -eq 0 ]; then
  echo "No task files found in $TASK_DIR" >&2
  exit 1
fi

for task_file in "${TASKS[@]}"; do
  stem="$(task_stem "$task_file")"
  prefix="${stem%%-*}"
  if [ -n "$FROM_PREFIX" ] && [ "$prefix" \< "$FROM_PREFIX" ]; then
    echo "SKIP $task_file before --from $FROM_PREFIX"
    continue
  fi
  run_task "$task_file"
done
