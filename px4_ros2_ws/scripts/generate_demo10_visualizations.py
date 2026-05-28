#!/usr/bin/env python3
"""Generate presentation plots from Demo 10 air-reach evidence."""

from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
LOG_ROOT = WORKSPACE / "logs" / "demo10_air_reach"
VIS_ROOT = WORKSPACE / "visualizations" / "demo10_air_reach"
REQUIRED_OUTPUTS = [
    "trajectory_3d.png",
    "phase_timeline.png",
    "flight_error.png",
    "target_visibility.png",
    "joint_positions.png",
    "endpoint_error.png",
    "summary.json",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Demo 10 air-reach visualizations from run evidence."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--latest-live",
        action="store_true",
        help="Use the latest successful live run; fall back to dry-run evidence if needed.",
    )
    group.add_argument(
        "--run-dir",
        type=Path,
        help="Explicit logs/demo10_air_reach/<timestamp> directory.",
    )
    args = parser.parse_args()

    try:
        run_dir, fallback = resolve_run_dir(args)
        metrics = read_json(run_dir / "metrics.json")
        events = read_jsonl(run_dir / "sequence_events.jsonl")
        episode_dir = find_episode_dir(run_dir)
        observations = read_jsonl(episode_dir / "observations.jsonl") if episode_dir else []
        actions = read_jsonl(episode_dir / "actions.jsonl") if episode_dir else []
        task_status = read_jsonl(episode_dir / "task_status.jsonl") if episode_dir else []

        timestamp = str(metrics.get("timestamp") or run_dir.name)
        output_dir = VIS_ROOT / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        context = build_context(
            run_dir=run_dir,
            output_dir=output_dir,
            metrics=metrics,
            events=events,
            observations=observations,
            actions=actions,
            task_status=task_status,
            fallback=fallback,
        )
        generate_plots(context)
        write_summary(context)

    except RuntimeError as exc:
        print(f"VISUALIZATION=FAIL reason={exc}")
        return 1

    print(
        "VISUALIZATION=PASS "
        f"run_dir={context['run_dir']} "
        f"output_dir={context['output_dir']} "
        f"mode={context['mode']} "
        f"result={context['metrics'].get('result', 'UNKNOWN')}"
    )
    for name in REQUIRED_OUTPUTS:
        print(f"OUTPUT {context['output_dir'] / name}")
    return 0


def resolve_run_dir(args: argparse.Namespace) -> tuple[Path, bool]:
    if args.run_dir:
        run_dir = args.run_dir
        if not run_dir.is_absolute():
            run_dir = WORKSPACE / run_dir
        if not (run_dir / "metrics.json").is_file():
            raise RuntimeError(f"missing metrics.json under {run_dir}")
        metrics = read_json(run_dir / "metrics.json")
        return run_dir, metrics.get("mode") == "dry-run"

    live = latest_run(mode="live", require_result="PASS", require_episode=True)
    if live:
        return live, False

    dry = latest_run(mode="dry-run", require_result="PASS", require_episode=False)
    if dry:
        return dry, True

    raise RuntimeError("no successful live or dry-run Demo 10 evidence found")


def latest_run(
    mode: str, require_result: str | None, require_episode: bool
) -> Path | None:
    candidates: list[Path] = []
    for run_dir in sorted(LOG_ROOT.glob("*")):
        metrics_path = run_dir / "metrics.json"
        if not metrics_path.is_file():
            continue
        try:
            metrics = read_json(metrics_path)
        except RuntimeError:
            continue
        if metrics.get("mode") != mode:
            continue
        if require_result and metrics.get("result") != require_result:
            continue
        if require_episode and not has_episode_data(run_dir):
            continue
        candidates.append(run_dir)
    return candidates[-1] if candidates else None


def has_episode_data(run_dir: Path) -> bool:
    episode_dir = find_episode_dir(run_dir)
    return bool(
        episode_dir
        and (episode_dir / "observations.jsonl").is_file()
        and (episode_dir / "actions.jsonl").is_file()
    )


def find_episode_dir(run_dir: Path) -> Path | None:
    episodes_root = run_dir / "episodes"
    direct = episodes_root / run_dir.name
    if direct.is_dir():
        return direct
    if not episodes_root.is_dir():
        return None
    children = sorted(child for child in episodes_root.iterdir() if child.is_dir())
    return children[-1] if children else None


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL in {path}:{line_number}: {exc}") from exc
            if isinstance(value, dict):
                rows.append(value)
    return rows


def build_context(
    *,
    run_dir: Path,
    output_dir: Path,
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    task_status: list[dict[str, Any]],
    fallback: bool,
) -> dict[str, Any]:
    warnings: list[str] = []
    if not events:
        warnings.append("sequence_events.jsonl missing or empty")
    if not observations:
        warnings.append("episode observations missing or empty")
    if not actions:
        warnings.append("episode actions missing or empty")
    if not task_status:
        warnings.append("episode task_status missing or empty")

    time_zero = first_time(events, observations, actions, task_status)
    mode = "dry-run fallback" if fallback else str(metrics.get("mode", "unknown"))
    status = "PASS" if metrics.get("result") == "PASS" and not warnings else "WARN"
    return {
        "run_dir": run_dir,
        "output_dir": output_dir,
        "metrics": metrics,
        "events": events,
        "observations": observations,
        "actions": actions,
        "task_status": task_status,
        "time_zero": time_zero,
        "mode": mode,
        "status": status,
        "warnings": warnings,
    }


def first_time(*groups: list[dict[str, Any]]) -> float:
    values: list[float] = []
    for group in groups:
        for row in group:
            t = event_time(row)
            if t is not None:
                values.append(t)
    return min(values) if values else 0.0


def event_time(row: dict[str, Any]) -> float | None:
    for key in ("t_sec", "receipt_time_sec", "stamp_sec"):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def rel_time(row: dict[str, Any], time_zero: float) -> float | None:
    t = event_time(row)
    if t is None:
        return None
    if "t_sec" in row:
        return t
    return t - time_zero


def generate_plots(context: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plot_trajectory_3d(context, plt)
    plot_phase_timeline(context, plt)
    plot_flight_error(context, plt)
    plot_target_visibility(context, plt)
    plot_joint_positions(context, plt)
    plot_endpoint_error(context, plt)


def plot_trajectory_3d(context: dict[str, Any], plt: Any) -> None:
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection="3d")
    obs_points = [
        vector(row, "platform", "position_ned") for row in context["observations"]
    ]
    obs_points = [point for point in obs_points if point is not None]
    target_points = [
        vector(row, "target_position_ned")
        for row in context["actions"]
        if row.get("action_type") == "uav_target_position_ned"
    ]
    target_points = [point for point in target_points if point is not None]

    if obs_points:
        xs, ys, zs = unzip3(obs_points)
        ax.plot(xs, ys, zs, label="UAV position NED", linewidth=2)
        ax.scatter(xs[0], ys[0], zs[0], marker="o", label="start")
        ax.scatter(xs[-1], ys[-1], zs[-1], marker="x", label="end")
    if target_points:
        xs, ys, zs = unzip3(target_points)
        ax.plot(xs, ys, zs, "--", label="Commanded target NED", linewidth=2)
    if not obs_points and not target_points:
        placeholder_3d(ax, "No trajectory samples available")

    ax.set_title(title(context, "Demo 10 Air-Reach Trajectory"))
    ax.set_xlabel("X north (m)")
    ax.set_ylabel("Y east (m)")
    ax.set_zlabel("Z down (m)")
    ax.legend(loc="best")
    savefig(fig, context["output_dir"] / "trajectory_3d.png")


def plot_phase_timeline(context: dict[str, Any], plt: Any) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.8))
    events = sorted(
        [row for row in context["events"] if rel_time(row, context["time_zero"]) is not None],
        key=lambda row: rel_time(row, context["time_zero"]) or 0.0,
    )
    if events:
        end_time = float(context["metrics"].get("task_timeout", {}).get("duration_sec", 0.0))
        if end_time <= 0.0:
            end_time = max(rel_time(row, context["time_zero"]) or 0.0 for row in events) + 1.0
        for idx, row in enumerate(events):
            start = rel_time(row, context["time_zero"]) or 0.0
            next_start = (
                rel_time(events[idx + 1], context["time_zero"])
                if idx + 1 < len(events)
                else end_time
            )
            width = max((next_start or end_time) - start, 0.05)
            label = str(row.get("phase", "unknown"))
            ax.barh([0], [width], left=[start], height=0.45, label=label)
            ax.text(start + width / 2.0, 0, label, ha="center", va="center", fontsize=9)
        ax.set_yticks([])
        ax.set_xlim(left=0)
    else:
        placeholder_2d(ax, "No phase events available")
    ax.set_title(title(context, "Demo 10 Phase Timeline"))
    ax.set_xlabel("Time since sequence start (s)")
    savefig(fig, context["output_dir"] / "phase_timeline.png")


def plot_flight_error(context: dict[str, Any], plt: Any) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    times, errors = flight_errors(context)
    limit = numeric(context["metrics"].get("flight_error", {}).get("limit_m"))
    if times and errors:
        ax.plot(times, errors, label="UAV position to latest target", linewidth=2)
        ax.scatter([times[-1]], [errors[-1]], label="final sample")
    else:
        avg_m = numeric(context["metrics"].get("flight_error", {}).get("avg_m"))
        max_m = numeric(context["metrics"].get("flight_error", {}).get("max_m"))
        labels = []
        values = []
        if avg_m is not None:
            labels.append("average")
            values.append(avg_m)
        if max_m is not None:
            labels.append("maximum")
            values.append(max_m)
        if values:
            ax.bar(labels, values, label="metrics summary")
        else:
            placeholder_2d(ax, "No flight error data available")
    if limit is not None:
        ax.axhline(limit, linestyle="--", color="tab:red", label=f"limit {limit:.2f} m")
    ax.set_title(title(context, "Flight Tracking Error"))
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("3D error (m)")
    ax.legend(loc="best")
    savefig(fig, context["output_dir"] / "flight_error.png")


def plot_target_visibility(context: dict[str, Any], plt: Any) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    times = []
    visible = []
    for row in context["observations"]:
        t = rel_time(row, context["time_zero"])
        if t is None:
            continue
        target = row.get("target")
        if isinstance(target, dict):
            times.append(t)
            visible.append(1.0 if target.get("visible") else 0.0)
    if times:
        ax.step(times, visible, where="post", label="episode target.visible")
        ax.set_ylim(-0.1, 1.1)
    else:
        visibility = context["metrics"].get("target_visibility", {})
        ratio = numeric(visibility.get("visible_ratio"))
        minimum = numeric(visibility.get("min_visible_ratio"))
        if ratio is not None:
            ax.bar(["visible ratio"], [ratio], label="metrics summary")
            if minimum is not None:
                ax.axhline(minimum, linestyle="--", color="tab:red", label="minimum")
            ax.set_ylim(0, 1.05)
        else:
            placeholder_2d(ax, "No target visibility data available")
    ax.set_title(title(context, "Target Visibility"))
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("Visible flag / ratio")
    ax.legend(loc="best")
    savefig(fig, context["output_dir"] / "target_visibility.png")


def plot_joint_positions(context: dict[str, Any], plt: Any) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    series: dict[str, tuple[list[float], list[float]]] = {}
    for row in context["observations"]:
        t = rel_time(row, context["time_zero"])
        arm = row.get("arm")
        if t is None or not isinstance(arm, dict):
            continue
        names = arm.get("joint_names")
        positions = arm.get("joint_positions")
        if not isinstance(names, list) or not isinstance(positions, list):
            continue
        for name, position in zip(names, positions):
            value = numeric(position)
            if value is None:
                continue
            times, values = series.setdefault(str(name), ([], []))
            times.append(t)
            values.append(value)
    if series:
        for name, (times, values) in series.items():
            ax.plot(times, values, label=name, linewidth=2)
        limits = context["metrics"].get("joint_limits", {}).get("limits_rad")
        if isinstance(limits, list):
            for lower, upper in limits:
                if isinstance(lower, (int, float)) and isinstance(upper, (int, float)):
                    ax.axhspan(float(lower), float(upper), alpha=0.06, color="tab:green")
    else:
        placeholder_2d(ax, "No joint position samples available")
    ax.set_title(title(context, "Arm Joint Positions"))
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("Joint position (rad)")
    ax.legend(loc="best")
    savefig(fig, context["output_dir"] / "joint_positions.png")


def plot_endpoint_error(context: dict[str, Any], plt: Any) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.8))
    times: list[float] = []
    errors: list[float] = []
    for row in context["observations"]:
        t = rel_time(row, context["time_zero"])
        end_effector = vector(row, "arm", "end_effector_position")
        target = vector(row, "target", "position")
        visible = nested(row, "target", "visible")
        if t is None or end_effector is None or target is None or not visible:
            continue
        times.append(t)
        errors.append(distance(end_effector, target))
    limit = numeric(context["metrics"].get("final_endpoint_error", {}).get("limit_m"))
    if times and errors:
        ax.plot(times, errors, label="end effector to visible target", linewidth=2)
    else:
        final_error = numeric(context["metrics"].get("final_endpoint_error", {}).get("error_m"))
        if final_error is not None:
            ax.bar(["final"], [final_error], label="metrics final endpoint error")
        else:
            placeholder_2d(ax, "No endpoint error data available")
    if limit is not None:
        ax.axhline(limit, linestyle="--", color="tab:red", label=f"limit {limit:.2f} m")
    ax.set_title(title(context, "Endpoint Error"))
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("Endpoint error (m)")
    ax.legend(loc="best")
    savefig(fig, context["output_dir"] / "endpoint_error.png")


def flight_errors(context: dict[str, Any]) -> tuple[list[float], list[float]]:
    target_times: list[float] = []
    target_points: list[tuple[float, float, float]] = []
    for row in context["actions"]:
        if row.get("action_type") != "uav_target_position_ned":
            continue
        t = rel_time(row, context["time_zero"])
        point = vector(row, "target_position_ned")
        if t is not None and point is not None:
            target_times.append(t)
            target_points.append(point)

    times: list[float] = []
    errors: list[float] = []
    for row in context["observations"]:
        t = rel_time(row, context["time_zero"])
        point = vector(row, "platform", "position_ned")
        if t is None or point is None:
            continue
        idx = bisect.bisect_right(target_times, t) - 1
        if idx < 0:
            continue
        times.append(t)
        errors.append(distance(point, target_points[idx]))
    return times, errors


def write_summary(context: dict[str, Any]) -> None:
    metrics = context["metrics"]
    summary = {
        "demo": "demo10_air_reach",
        "timestamp": metrics.get("timestamp") or context["run_dir"].name,
        "mode": context["mode"],
        "status_label": context["status"],
        "result": metrics.get("result"),
        "reason": metrics.get("reason"),
        "source_run_dir": str(context["run_dir"]),
        "visualization_dir": str(context["output_dir"]),
        "inputs": {
            "metrics_json": str(context["run_dir"] / "metrics.json"),
            "sequence_events_jsonl": str(context["run_dir"] / "sequence_events.jsonl"),
            "episode_observations": len(context["observations"]),
            "episode_actions": len(context["actions"]),
            "episode_task_status": len(context["task_status"]),
        },
        "metrics": metrics,
        "warnings": context["warnings"],
        "generated_files": REQUIRED_OUTPUTS,
    }
    with (context["output_dir"] / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")


def title(context: dict[str, Any], label: str) -> str:
    metrics = context["metrics"]
    result = metrics.get("result", "UNKNOWN")
    return f"{label} | {context['mode']} | {context['status']} ({result})"


def nested(row: dict[str, Any], *keys: str) -> Any:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def vector(row: dict[str, Any], *keys: str) -> tuple[float, float, float] | None:
    value = nested(row, *keys)
    if not isinstance(value, dict):
        return None
    coords = [numeric(value.get(key)) for key in ("x", "y", "z")]
    if any(coord is None for coord in coords):
        return None
    return (coords[0], coords[1], coords[2])  # type: ignore[return-value]


def numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def unzip3(points: list[tuple[float, float, float]]) -> tuple[list[float], list[float], list[float]]:
    return (
        [point[0] for point in points],
        [point[1] for point in points],
        [point[2] for point in points],
    )


def placeholder_2d(ax: Any, message: str) -> None:
    ax.text(0.5, 0.5, f"WARN\n{message}", ha="center", va="center", transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def placeholder_3d(ax: Any, message: str) -> None:
    ax.text2D(0.5, 0.5, f"WARN\n{message}", ha="center", va="center", transform=ax.transAxes)


def savefig(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    fig.clf()


if __name__ == "__main__":
    sys.exit(main())
