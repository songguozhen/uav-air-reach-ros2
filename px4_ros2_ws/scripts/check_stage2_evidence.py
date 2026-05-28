#!/usr/bin/env python3
"""Validate Stage 2 completion evidence from local artifacts."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEMO10_ROOT = WORKSPACE_ROOT / "logs" / "demo10_air_reach"
DELIVERABLES_DIR = WORKSPACE_ROOT / "deliverables"
STATUS_JSON = DELIVERABLES_DIR / "task-status.json"
SUMMARY_MD = DELIVERABLES_DIR / "task-summary.md"

REQUIRED_SEQUENCE = [
    "stable_hover",
    "tag_detection",
    "coordinated_approach",
    "endpoint_hold",
]

REQUIRED_STAGE2_DOCS = {
    "frames": "docs/STAGE2_FRAMES_AND_STATE.md",
    "control": "docs/STAGE2_CONTROL_NOTES.md",
    "vision": "docs/STAGE2_VISION_BRIDGE.md",
    "dataset": "docs/STAGE2_DATASET_SCHEMA.md",
    "policy": "docs/STAGE2_LEROBOT_POLICY.md",
    "coordinator": "docs/STAGE2_COORDINATOR.md",
    "demo10": "docs/STAGE2_AIR_REACH_DEMO.md",
}


def main() -> int:
    report = build_report()
    write_deliverables(report)

    status = report["overall_status"]
    print(
        f"CHECK={status} "
        f"report={relative(STATUS_JSON)} "
        f"dry_run={report['demo10']['dry_run']['status']} "
        f"live={report['demo10']['live']['status']} "
        f"docs={report['stage2_docs']['status']} "
        f"tasks={report['task_evidence']['status']}"
    )
    return 0 if status == "PASS" else 1


def build_report() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    demo10 = validate_demo10()
    docs = validate_stage2_docs()
    tasks = validate_task_evidence(12, 22)

    overall_status = "PASS"
    for section in (demo10["dry_run"], demo10["live"], docs, tasks):
        if section["status"] != "PASS":
            overall_status = "FAIL"
            break

    return {
        "schema_version": "stage2_evidence_validation_v1",
        "generated_at": generated_at,
        "workspace": str(WORKSPACE_ROOT),
        "overall_status": overall_status,
        "demo10": demo10,
        "stage2_docs": docs,
        "task_evidence": tasks,
    }


def validate_demo10() -> dict[str, Any]:
    return {
        "dry_run": validate_demo10_dry_run(),
        "live": validate_demo10_live(),
    }


def validate_demo10_dry_run() -> dict[str, Any]:
    run_dir = latest_demo10_run(lambda path: demo10_metrics(path).get("mode") == "dry-run")
    if run_dir is None:
        return failed_check("no dry-run Demo 10 metrics run found")

    failures: list[str] = []
    files = require_files(run_dir, ["metrics.json", "result.txt", "sequence_events.jsonl"])
    failures.extend(files["missing"])

    metrics = demo10_metrics(run_dir)
    if metrics:
        failures.extend(validate_demo10_metrics(metrics))
    else:
        failures.append("metrics.json is missing or invalid JSON")

    result_text = read_text(run_dir / "result.txt")
    if "RESULT=PASS" not in result_text:
        failures.append("result.txt does not contain RESULT=PASS")

    event_phases = read_demo10_event_phases(run_dir / "sequence_events.jsonl")
    if event_phases != REQUIRED_SEQUENCE:
        failures.append(
            "sequence_events.jsonl phase_start sequence does not match "
            + ",".join(REQUIRED_SEQUENCE)
        )

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "path": relative(run_dir),
        "mode": metrics.get("mode"),
        "result": metrics.get("result"),
        "timestamp": metrics.get("timestamp"),
        "required_files": files["files"],
        "sequence_phases": event_phases,
        "metrics_summary": metric_summary(metrics),
        "failures": failures,
    }


def validate_demo10_live() -> dict[str, Any]:
    run_dir = latest_demo10_run(
        lambda path: (path / "stack_readiness.txt").is_file()
        or "mode=live" in read_text(path / "result.txt")
    )
    if run_dir is None:
        return failed_check("no live or live-smoke Demo 10 evidence found")

    failures: list[str] = []
    result_text = read_text(run_dir / "result.txt")
    if "RESULT=PASS" not in result_text:
        failures.append("result.txt does not contain RESULT=PASS")

    mode = parse_result_mode(result_text)
    stack_readiness = read_text(run_dir / "stack_readiness.txt").strip()
    if mode == "live-smoke" or stack_readiness:
        if not stack_readiness.startswith("STACK_READY=YES "):
            failures.append("stack_readiness.txt does not contain STACK_READY=YES")
    elif mode == "live":
        files = require_files(run_dir, ["metrics.json", "result.txt", "sequence_events.jsonl"])
        failures.extend(files["missing"])
        metrics = demo10_metrics(run_dir)
        failures.extend(validate_demo10_metrics(metrics))
    else:
        failures.append(f"unsupported live result mode: {mode or 'missing'}")

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "path": relative(run_dir),
        "mode": mode,
        "result_line": result_text.strip(),
        "stack_readiness": stack_readiness,
        "failures": failures,
    }


def validate_demo10_metrics(metrics: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if metrics.get("schema_version") != "demo10_air_reach_metrics_v1":
        failures.append("unexpected metrics schema_version")
    if metrics.get("demo") != "demo10_air_reach":
        failures.append("unexpected metrics demo name")
    if metrics.get("result") != "PASS":
        failures.append(f"metrics result is {metrics.get('result')}")
    if metrics.get("sequence") != REQUIRED_SEQUENCE:
        failures.append("metrics sequence does not match required Demo 10 phases")

    flight = require_dict(metrics, "flight_error", failures)
    joint_limits = require_dict(metrics, "joint_limits", failures)
    visibility = require_dict(metrics, "target_visibility", failures)
    timeout = require_dict(metrics, "task_timeout", failures)
    endpoint = require_dict(metrics, "final_endpoint_error", failures)

    if flight and number(flight, "max_m", failures) > number(flight, "limit_m", failures):
        failures.append("flight_error.max_m exceeds flight_error.limit_m")
    if joint_limits and int(joint_limits.get("violations", -1)) != 0:
        failures.append("joint_limits.violations is not zero")
    if visibility and number(visibility, "visible_ratio", failures) < number(
        visibility, "min_visible_ratio", failures
    ):
        failures.append("target_visibility.visible_ratio below minimum")
    if timeout and bool(timeout.get("timed_out", True)):
        failures.append("task_timeout.timed_out is true")
    if endpoint and number(endpoint, "error_m", failures) > number(
        endpoint, "limit_m", failures
    ):
        failures.append("final_endpoint_error.error_m exceeds limit")

    return failures


def validate_stage2_docs() -> dict[str, Any]:
    entries = []
    failures = []
    for name, rel_path in REQUIRED_STAGE2_DOCS.items():
        path = WORKSPACE_ROOT / rel_path
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        if not exists:
            failures.append(f"missing {rel_path}")
        elif size == 0:
            failures.append(f"empty {rel_path}")
        entries.append(
            {
                "name": name,
                "path": rel_path,
                "exists": exists,
                "size_bytes": size,
            }
        )

    return {
        "status": "PASS" if not failures else "FAIL",
        "required": entries,
        "failures": failures,
    }


def validate_task_evidence(first_task: int, last_task: int) -> dict[str, Any]:
    task_entries = []
    mismatches = []

    for task_number in range(first_task, last_task + 1):
        task_file = task_file_for(task_number)
        if task_file is None:
            stem = f"{task_number:03d}-unknown"
            task_file_rel = None
        else:
            stem = task_file.stem
            task_file_rel = relative(task_file)

        done_path = WORKSPACE_ROOT / "codex-logs" / f"{stem}.done"
        log_files = sorted((WORKSPACE_ROOT / "codex-logs").glob(f"{stem}*.log"))
        has_done = done_path.is_file()
        has_log = bool(log_files)

        mismatch = None
        if not has_done and has_log:
            mismatch = "log exists but .done marker is missing"
        elif has_done and not has_log:
            mismatch = ".done marker exists but task log is missing"
        elif not has_done and not has_log:
            mismatch = "both task log and .done marker are missing"

        if mismatch:
            mismatches.append(f"{task_number:03d}: {mismatch}")

        task_entries.append(
            {
                "task": f"{task_number:03d}",
                "stem": stem,
                "task_file": task_file_rel,
                "done_marker": relative(done_path),
                "done_exists": has_done,
                "log_files": [relative(path) for path in log_files],
                "log_count": len(log_files),
                "mismatch": mismatch,
            }
        )

    return {
        "status": "PASS" if not mismatches else "FAIL",
        "task_range": f"{first_task:03d}-{last_task:03d}",
        "tasks": task_entries,
        "mismatches": mismatches,
    }


def latest_demo10_run(predicate: Any) -> Path | None:
    if not DEMO10_ROOT.is_dir():
        return None
    candidates = []
    for path in DEMO10_ROOT.iterdir():
        if path.is_dir() and predicate(path):
            candidates.append(path)
    return sorted(candidates)[-1] if candidates else None


def demo10_metrics(run_dir: Path) -> dict[str, Any]:
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.is_file():
        return {}
    try:
        value = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_demo10_event_phases(path: Path) -> list[str]:
    phases = []
    if not path.is_file():
        return phases
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "phase_start" and isinstance(event.get("phase"), str):
            phases.append(event["phase"])
    return phases


def task_file_for(task_number: int) -> Path | None:
    matches = sorted((WORKSPACE_ROOT / "codex-tasks").glob(f"{task_number:03d}-*.md"))
    return matches[0] if matches else None


def require_files(root: Path, filenames: list[str]) -> dict[str, Any]:
    files = []
    missing = []
    for filename in filenames:
        path = root / filename
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        if not exists:
            missing.append(f"missing {filename}")
        files.append({"path": relative(path), "exists": exists, "size_bytes": size})
    return {"files": files, "missing": missing}


def require_dict(metrics: dict[str, Any], key: str, failures: list[str]) -> dict[str, Any]:
    value = metrics.get(key)
    if not isinstance(value, dict):
        failures.append(f"missing {key}")
        return {}
    return value


def number(values: dict[str, Any], key: str, failures: list[str]) -> float:
    value = values.get(key)
    if not isinstance(value, (int, float)):
        failures.append(f"missing numeric {key}")
        return float("inf")
    return float(value)


def metric_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    if not metrics:
        return {}
    return {
        "max_flight_error_m": metrics.get("flight_error", {}).get("max_m"),
        "flight_error_limit_m": metrics.get("flight_error", {}).get("limit_m"),
        "target_visible_ratio": metrics.get("target_visibility", {}).get("visible_ratio"),
        "target_min_visible_ratio": metrics.get("target_visibility", {}).get(
            "min_visible_ratio"
        ),
        "final_endpoint_error_m": metrics.get("final_endpoint_error", {}).get("error_m"),
        "final_endpoint_limit_m": metrics.get("final_endpoint_error", {}).get("limit_m"),
        "joint_limit_violations": metrics.get("joint_limits", {}).get("violations"),
        "timed_out": metrics.get("task_timeout", {}).get("timed_out"),
    }


def failed_check(reason: str) -> dict[str, Any]:
    return {"status": "FAIL", "failures": [reason]}


def parse_result_mode(result_text: str) -> str | None:
    match = re.search(r"\bmode=([A-Za-z0-9_-]+)", result_text)
    return match.group(1) if match else None


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def write_deliverables(report: dict[str, Any]) -> None:
    DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(render_summary(report), encoding="utf-8")


def render_summary(report: dict[str, Any]) -> str:
    dry_run = report["demo10"]["dry_run"]
    live = report["demo10"]["live"]
    docs = report["stage2_docs"]
    tasks = report["task_evidence"]

    lines = [
        "# Stage 2 Evidence Summary",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- overall_status: `{report['overall_status']}`",
        f"- workspace: `{report['workspace']}`",
        "",
        "## Demo 10 Evidence",
        "",
        f"- dry_run_status: `{dry_run['status']}`",
        f"- dry_run_path: `{dry_run.get('path', 'n/a')}`",
        f"- dry_run_result: `{dry_run.get('result', 'n/a')}`",
        f"- live_status: `{live['status']}`",
        f"- live_path: `{live.get('path', 'n/a')}`",
        f"- live_result: `{live.get('result_line', 'n/a')}`",
        "",
        "## Stage 2 Docs",
        "",
        f"- docs_status: `{docs['status']}`",
    ]
    for entry in docs["required"]:
        state = "present" if entry["exists"] else "missing"
        lines.append(f"- {entry['name']}: `{state}` `{entry['path']}`")

    lines.extend(
        [
            "",
            "## Task 012-022 Evidence",
            "",
            f"- task_evidence_status: `{tasks['status']}`",
            f"- mismatches: `{len(tasks['mismatches'])}`",
        ]
    )
    for mismatch in tasks["mismatches"]:
        lines.append(f"- mismatch: `{mismatch}`")

    lines.extend(
        [
            "",
            "Machine-readable detail is in `task-status.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    sys.exit(main())
