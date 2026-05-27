#!/usr/bin/env bash
set -u

failures=()
checked_files=()

usage() {
  cat <<'EOF'
Usage:
  ./scripts/check_demo_outputs.sh <log-or-visualization-directory>

Examples:
  ./scripts/check_demo_outputs.sh logs/offboard_hover/<timestamp>
  ./scripts/check_demo_outputs.sh visualizations/demo01_hover/<timestamp>
EOF
}

add_failure() {
  failures+=("$1")
}

mark_checked() {
  local existing
  for existing in "${checked_files[@]}"; do
    [[ "$existing" == "$1" ]] && return
  done
  checked_files+=("$1")
}

has_standard_output_marker() {
  local dir="$1"
  [[ -f "$dir/trajectory.csv" || -f "$dir/result.txt" || -f "$dir/verify.log" ]]
}

latest_child_dir() {
  local dir="$1"
  find "$dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1
}

resolve_target_dir() {
  local input_dir="$1"
  local target_dir="$input_dir"

  if ! has_standard_output_marker "$target_dir"; then
    local latest
    latest="$(latest_child_dir "$target_dir")"
    if [[ -n "$latest" ]]; then
      target_dir="$latest"
    fi
  fi

  local parent_dir demo_name timestamp vis_dir
  parent_dir="$(dirname "$target_dir")"
  demo_name="$(basename "$parent_dir")"
  timestamp="$(basename "$target_dir")"
  vis_dir="visualizations/$demo_name/$timestamp"

  if [[ "$target_dir" == logs/* && -d "$vis_dir" ]]; then
    target_dir="$vis_dir"
  fi

  printf '%s\n' "$target_dir"
}

require_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    mark_checked "$file"
  else
    add_failure "missing file: $file"
  fi
}

check_pass_marker() {
  local dir="$1"

  if [[ -f "$dir/result.txt" ]]; then
    mark_checked "$dir/result.txt"
    if ! grep -q 'RESULT=PASS' "$dir/result.txt"; then
      add_failure "missing RESULT=PASS in: $dir/result.txt"
    fi
    return
  fi

  if [[ -f "$dir/verify.log" ]]; then
    mark_checked "$dir/verify.log"
    if ! grep -q 'RESULT=PASS' "$dir/verify.log"; then
      add_failure "missing RESULT=PASS in: $dir/verify.log"
    fi
    return
  fi

  add_failure "missing pass marker file: $dir/result.txt or $dir/verify.log"
}

check_csv_header() {
  local csv_file="$1"
  require_file "$csv_file"
  [[ -f "$csv_file" ]] || return

  local missing
  missing="$(
    awk -F',' '
      NR == 1 {
        saw_header = 1
        for (i = 1; i <= NF; i++) {
          field = $i
          gsub(/\r/, "", field)
          gsub(/^[[:space:]"]+|[[:space:]"]+$/, "", field)
          seen[field] = 1
        }

        if (!seen["timestamp"] && !seen["t"]) {
          print "timestamp-or-t"
        }

        required[1] = "x"
        required[2] = "y"
        required[3] = "z"
        required[4] = "vx"
        required[5] = "vy"
        required[6] = "vz"

        for (i = 1; i <= 6; i++) {
          if (!seen[required[i]]) {
            print required[i]
          }
        }
        exit
      }
      END {
        if (!saw_header) {
          print "header"
        }
      }
    ' "$csv_file"
  )"

  if [[ -n "$missing" ]]; then
    while IFS= read -r field; do
      [[ -n "$field" ]] && add_failure "missing CSV field in $csv_file: $field"
    done <<< "$missing"
  fi
}

check_standard_visualization_dir() {
  local dir="$1"

  check_csv_header "$dir/trajectory.csv"
  require_file "$dir/trajectory_3d.png"
  require_file "$dir/xy_path.png"
  require_file "$dir/height_curve.png"
  require_file "$dir/speed_curve.png"
  require_file "$dir/tracking_error.png"
  require_file "$dir/summary.md"
  require_file "$dir/result.txt"
  check_pass_marker "$dir"
}

check_legacy_log_dir() {
  local dir="$1"
  require_file "$dir/verify.log"
  check_pass_marker "$dir"
}

main() {
  if [[ "$#" -ne 1 ]]; then
    usage
    echo "CHECK=FAIL"
    return 2
  fi

  local input_dir="$1"
  if [[ ! -d "$input_dir" ]]; then
    echo "input directory not found: $input_dir"
    echo "CHECK=FAIL"
    return 2
  fi

  local target_dir
  target_dir="$(resolve_target_dir "$input_dir")"
  echo "checking: $target_dir"

  if [[ -f "$target_dir/trajectory.csv" || -f "$target_dir/result.txt" ]]; then
    check_standard_visualization_dir "$target_dir"
  elif [[ -f "$target_dir/verify.log" ]]; then
    check_legacy_log_dir "$target_dir"
  else
    add_failure "unsupported output directory: $target_dir"
  fi

  if [[ "${#checked_files[@]}" -gt 0 ]]; then
    echo "checked files:"
    printf '  %s\n' "${checked_files[@]}"
  fi

  if [[ "${#failures[@]}" -gt 0 ]]; then
    echo "failures:"
    printf '  %s\n' "${failures[@]}"
    echo "CHECK=FAIL"
    return 1
  fi

  echo "CHECK=PASS"
  return 0
}

main "$@"
