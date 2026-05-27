import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


Vector3 = Tuple[float, float, float]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic Demo 10 air-reach regression artifacts."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timestamp", default="")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    timestamp = args.timestamp or time.strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = _build_samples()
    events = _build_events(samples)
    metrics = _compute_metrics(samples, timestamp)

    _write_jsonl(output_dir / "sequence_events.jsonl", events)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "result.txt").write_text(
        f"RESULT={metrics['result']} reason={metrics['reason']}\n", encoding="utf-8"
    )
    (output_dir / "summary.md").write_text(_summary(metrics), encoding="utf-8")

    print(f"DEMO10_DRY_RUN={metrics['result']} output_dir={output_dir}")


def _build_samples() -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    target: Vector3 = (1.20, 0.20, -1.85)
    endpoint_final: Vector3 = (1.15, 0.20, -1.84)
    for index in range(80):
        t = index * 0.2
        if index < 18:
            phase = "stable_hover"
            desired = (0.0, 0.0, -2.0)
            position = (0.02 * math.sin(t), 0.02 * math.cos(t), -2.0 + 0.015 * math.sin(t))
            target_visible = False
            endpoint = (position[0] + 0.25, position[1], position[2] + 0.05)
            joints = [0.0, 0.0, 0.0]
        elif index < 30:
            phase = "tag_detection"
            desired = (0.0, 0.0, -2.0)
            position = (0.02 * math.sin(t), 0.02 * math.cos(t), -2.0 + 0.015 * math.sin(t))
            target_visible = True
            endpoint = (position[0] + 0.25, position[1], position[2] + 0.05)
            joints = [0.0, 0.0, 0.0]
        elif index < 62:
            phase = "coordinated_approach"
            ratio = (index - 30) / 31.0
            desired = (0.70 * ratio, 0.12 * ratio, -1.90)
            position = (
                desired[0] - 0.05 * (1.0 - ratio),
                desired[1] - 0.02 * (1.0 - ratio),
                desired[2] - 0.04 * (1.0 - ratio),
            )
            target_visible = True
            endpoint = (
                position[0] + 0.25 + 0.20 * ratio,
                position[1] + 0.03 + 0.05 * ratio,
                position[2] + 0.04 + 0.02 * ratio,
            )
            joints = [0.08 * ratio, 0.20 * ratio, 0.05 * ratio]
        else:
            phase = "endpoint_hold"
            desired = (0.70, 0.12, -1.90)
            position = (0.70 + 0.01 * math.sin(t), 0.12, -1.90 + 0.01 * math.cos(t))
            target_visible = True
            endpoint = endpoint_final
            joints = [0.08, 0.20, 0.05]

        samples.append(
            {
                "t_sec": round(t, 3),
                "phase": phase,
                "desired_position_ned": _point(desired),
                "platform_position_ned": _point(position),
                "target_position_ned": _point(target),
                "endpoint_position_ned": _point(endpoint),
                "target_visible": target_visible,
                "contact_detected": False,
                "joint_positions": joints,
            }
        )
    return samples


def _build_events(samples: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    previous_phase = ""
    for sample in samples:
        phase = str(sample["phase"])
        if phase != previous_phase:
            events.append(
                {
                    "t_sec": sample["t_sec"],
                    "event": "phase_start",
                    "phase": phase,
                    "message": _phase_message(phase),
                }
            )
            previous_phase = phase
    events.append(
        {
            "t_sec": 15.8,
            "event": "terminal_status",
            "phase": "endpoint_hold",
            "message": "endpoint hold reached without contact sensor input",
        }
    )
    return events


def _compute_metrics(samples: List[Dict[str, Any]], timestamp: str) -> Dict[str, Any]:
    flight_errors = [
        _distance(sample["platform_position_ned"], sample["desired_position_ned"])
        for sample in samples
    ]
    endpoint_errors = [
        _distance(sample["endpoint_position_ned"], sample["target_position_ned"])
        for sample in samples
        if sample["phase"] == "endpoint_hold"
    ]
    joint_limits = [(-1.57, 1.57), (-1.57, 1.57), (-1.57, 1.57)]
    violations = 0
    for sample in samples:
        for value, (lower, upper) in zip(sample["joint_positions"], joint_limits):
            if value < lower or value > upper:
                violations += 1

    visible_samples = sum(1 for sample in samples if sample["target_visible"])
    duration = samples[-1]["t_sec"] - samples[0]["t_sec"]
    metrics: Dict[str, Any] = {
        "schema_version": "demo10_air_reach_metrics_v1",
        "demo": "demo10_air_reach",
        "timestamp": timestamp,
        "mode": "dry-run",
        "sequence": [
            "stable_hover",
            "tag_detection",
            "coordinated_approach",
            "endpoint_hold",
        ],
        "thresholds": {
            "max_flight_error_m": 0.45,
            "min_target_visible_ratio": 0.50,
            "max_final_endpoint_error_m": 0.18,
            "max_duration_sec": 45.0,
        },
        "flight_error": {
            "max_m": max(flight_errors),
            "avg_m": sum(flight_errors) / len(flight_errors),
            "limit_m": 0.45,
        },
        "joint_limits": {
            "violations": violations,
            "limits_rad": joint_limits,
        },
        "target_visibility": {
            "visible_samples": visible_samples,
            "total_samples": len(samples),
            "visible_ratio": visible_samples / len(samples),
            "min_visible_ratio": 0.50,
        },
        "task_timeout": {
            "duration_sec": duration,
            "limit_sec": 45.0,
            "timed_out": duration > 45.0,
        },
        "final_endpoint_error": {
            "error_m": endpoint_errors[-1],
            "limit_m": 0.18,
            "contact_detected": any(sample["contact_detected"] for sample in samples),
        },
    }
    reasons = _failure_reasons(metrics)
    metrics["result"] = "PASS" if not reasons else "FAIL"
    metrics["reason"] = "ok" if not reasons else "; ".join(reasons)
    return metrics


def _failure_reasons(metrics: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if metrics["flight_error"]["max_m"] > metrics["flight_error"]["limit_m"]:
        reasons.append("flight error exceeds limit")
    if metrics["joint_limits"]["violations"] > 0:
        reasons.append("joint limit violation")
    if (
        metrics["target_visibility"]["visible_ratio"]
        < metrics["target_visibility"]["min_visible_ratio"]
    ):
        reasons.append("target visibility below limit")
    if metrics["task_timeout"]["timed_out"]:
        reasons.append("task timeout")
    if (
        metrics["final_endpoint_error"]["error_m"]
        > metrics["final_endpoint_error"]["limit_m"]
    ):
        reasons.append("final endpoint error exceeds limit")
    return reasons


def _summary(metrics: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Demo 10 Air Reach Summary",
            "",
            f"RESULT={metrics['result']} reason={metrics['reason']}",
            f"mode: {metrics['mode']}",
            f"max_flight_error_m: {metrics['flight_error']['max_m']:.3f}",
            f"target_visible_ratio: {metrics['target_visibility']['visible_ratio']:.3f}",
            f"joint_limit_violations: {metrics['joint_limits']['violations']}",
            f"duration_sec: {metrics['task_timeout']['duration_sec']:.3f}",
            f"final_endpoint_error_m: {metrics['final_endpoint_error']['error_m']:.3f}",
            "",
        ]
    )


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def _distance(left: Dict[str, float], right: Dict[str, float]) -> float:
    return math.sqrt(
        (float(left["x"]) - float(right["x"])) ** 2
        + (float(left["y"]) - float(right["y"])) ** 2
        + (float(left["z"]) - float(right["z"])) ** 2
    )


def _point(point: Vector3) -> Dict[str, float]:
    return {"x": point[0], "y": point[1], "z": point[2]}


def _phase_message(phase: str) -> str:
    return {
        "stable_hover": "hold initial UAV bridge target",
        "tag_detection": "wait for front-camera tag pose",
        "coordinated_approach": "send /approach goal for UAV and arm",
        "endpoint_hold": "hold endpoint near target",
    }[phase]


if __name__ == "__main__":
    main()
