#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_SEQUENCE = [
    "stable_hover",
    "tag_detection",
    "coordinated_approach",
    "endpoint_hold",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Demo 10 air-reach metrics.")
    parser.add_argument(
        "path",
        nargs="?",
        default="logs/demo10_air_reach",
        help="Demo 10 timestamp directory or logs/demo10_air_reach root.",
    )
    args = parser.parse_args()

    run_dir = _resolve_run_dir(Path(args.path))
    if run_dir is None:
        print(f"CHECK=FAIL path={args.path} reason=no timestamped Demo 10 run found")
        return 1

    metrics_path = run_dir / "metrics.json"
    result_path = run_dir / "result.txt"
    events_path = run_dir / "sequence_events.jsonl"
    failures: List[str] = []
    for path in (metrics_path, result_path, events_path):
        if not path.is_file():
            failures.append(f"missing {path.name}")

    metrics: Dict[str, Any] = {}
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"metrics.json is not valid JSON: {exc}")

    if result_path.is_file() and "RESULT=PASS" not in result_path.read_text(
        encoding="utf-8"
    ):
        failures.append("result.txt does not contain RESULT=PASS")

    if metrics:
        failures.extend(_validate_metrics(metrics))

    if failures:
        print(f"CHECK=FAIL path={run_dir} reason=" + "; ".join(failures))
        return 1

    print(
        "CHECK=PASS "
        f"path={run_dir} "
        f"mode={metrics['mode']} "
        f"max_flight_error_m={metrics['flight_error']['max_m']:.3f} "
        f"final_endpoint_error_m={metrics['final_endpoint_error']['error_m']:.3f} "
        f"target_visible_ratio={metrics['target_visibility']['visible_ratio']:.3f}"
    )
    return 0


def _resolve_run_dir(path: Path) -> Path | None:
    if (path / "metrics.json").is_file():
        return path
    if not path.is_dir():
        return None
    children = sorted(child for child in path.iterdir() if child.is_dir())
    children = [child for child in children if (child / "metrics.json").is_file()]
    return children[-1] if children else None


def _validate_metrics(metrics: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    if metrics.get("schema_version") != "demo10_air_reach_metrics_v1":
        failures.append("unexpected schema_version")
    if metrics.get("demo") != "demo10_air_reach":
        failures.append("unexpected demo name")
    if metrics.get("result") != "PASS":
        failures.append(f"metrics result is {metrics.get('result')}")
    sequence = metrics.get("sequence")
    if sequence != REQUIRED_SEQUENCE:
        failures.append("sequence does not match required Demo 10 phases")

    flight = _dict(metrics, "flight_error", failures)
    joint_limits = _dict(metrics, "joint_limits", failures)
    visibility = _dict(metrics, "target_visibility", failures)
    timeout = _dict(metrics, "task_timeout", failures)
    endpoint = _dict(metrics, "final_endpoint_error", failures)

    if flight and _number(flight, "max_m", failures) > _number(flight, "limit_m", failures):
        failures.append("flight error exceeds limit")
    if joint_limits and int(joint_limits.get("violations", -1)) != 0:
        failures.append("joint limit violations detected")
    if visibility and _number(visibility, "visible_ratio", failures) < _number(
        visibility, "min_visible_ratio", failures
    ):
        failures.append("target visibility below limit")
    if timeout and bool(timeout.get("timed_out", True)):
        failures.append("task timed out")
    if endpoint and _number(endpoint, "error_m", failures) > _number(
        endpoint, "limit_m", failures
    ):
        failures.append("final endpoint error exceeds limit")

    return failures


def _dict(metrics: Dict[str, Any], key: str, failures: List[str]) -> Dict[str, Any]:
    value = metrics.get(key)
    if not isinstance(value, dict):
        failures.append(f"missing {key}")
        return {}
    return value


def _number(metrics: Dict[str, Any], key: str, failures: List[str]) -> float:
    value = metrics.get(key)
    if not isinstance(value, (int, float)):
        failures.append(f"missing numeric {key}")
        return float("inf")
    return float(value)


if __name__ == "__main__":
    sys.exit(main())
