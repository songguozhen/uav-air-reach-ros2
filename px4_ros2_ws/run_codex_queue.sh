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
DRY_RUN=0
FROM_PREFIX=""
SINGLE_TASK=""

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

  if [ -z "$SINGLE_TASK" ] && [ -f "$done_file" ]; then
    echo "SKIP $task_file already done: $done_file"
    return 0
  fi

  echo "TASK $task_file"
  echo "LOG  $log_file"
  echo "START $(date --iso-8601=seconds)"

  if [ "$DRY_RUN" = "1" ]; then
    echo "DRY-RUN: { codex.md + $task_file } | ${CODEX_CMD[*]} | tee $log_file"
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
    echo "END   $(date --iso-8601=seconds)"
    echo "DONE $task_file"
  else
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
