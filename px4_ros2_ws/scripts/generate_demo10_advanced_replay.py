#!/usr/bin/env python3
"""Generate an advanced Demo 10 3D replay and optional MP4 clip."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
LOG_ROOT = WORKSPACE / "logs" / "demo10_air_reach"
VIS_ROOT = WORKSPACE / "visualizations" / "demo10_air_reach"
ADVANCED_DIRNAME = "advanced"
HTML_NAME = "advanced_replay.html"
MP4_NAME = "advanced_replay.mp4"
SUMMARY_NAME = "advanced_replay_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained advanced Demo 10 3D replay."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--latest-live",
        action="store_true",
        help="Prefer the latest successful live run and fall back to dry-run evidence.",
    )
    group.add_argument(
        "--run-dir",
        type=Path,
        help="Explicit logs/demo10_air_reach/<timestamp> run directory.",
    )
    args = parser.parse_args()

    run_dir, fallback = resolve_run_dir(args)
    metrics = read_json(run_dir / "metrics.json")
    events = read_jsonl(run_dir / "sequence_events.jsonl")
    result_text = read_text(run_dir / "result.txt")
    episode_dir = find_episode_dir(run_dir)
    observations = read_jsonl(episode_dir / "observations.jsonl") if episode_dir else []
    actions = read_jsonl(episode_dir / "actions.jsonl") if episode_dir else []
    task_status = read_jsonl(episode_dir / "task_status.jsonl") if episode_dir else []
    metadata = read_json(episode_dir / "metadata.json") if episode_dir else {}
    images = read_jsonl(episode_dir / "images.jsonl") if episode_dir else []

    if not observations:
        raise SystemExit(f"ADVANCED_REPLAY=FAIL reason=no observations in {relative(run_dir)}")

    replay = build_replay(
        run_dir=run_dir,
        episode_dir=episode_dir,
        metrics=metrics,
        events=events,
        observations=observations,
        actions=actions,
        task_status=task_status,
        metadata=metadata,
        images=images,
        result_text=result_text,
        fallback=fallback,
    )

    output_root = VIS_ROOT / replay["timestamp"] / ADVANCED_DIRNAME
    output_root.mkdir(parents=True, exist_ok=True)
    html_path = output_root / HTML_NAME
    summary_path = output_root / SUMMARY_NAME

    html_path.write_text(render_html(replay), encoding="utf-8")

    mp4_path, mp4_warning = generate_mp4_if_available(replay, output_root)
    if mp4_warning:
        replay["warnings"].append(mp4_warning)
    replay["outputs"]["html"] = relative(html_path)
    replay["outputs"]["summary"] = relative(summary_path)
    replay["outputs"]["mp4"] = relative(mp4_path) if mp4_path else None
    replay["outputs"]["frames_dir"] = (
        relative(output_root / "frames") if mp4_path else None
    )

    summary = build_summary(replay, html_path, summary_path, mp4_path)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    print(
        "ADVANCED_REPLAY=PASS "
        f"run_dir={relative(run_dir)} "
        f"output_dir={relative(output_root)} "
        f"status={summary['status']} "
        f"badge={summary['badge']['label']}"
    )
    print(f"OUTPUT {relative(html_path)}")
    print(f"OUTPUT {relative(summary_path)}")
    if mp4_path:
        print(f"OUTPUT {relative(mp4_path)}")
    for warning in summary["warnings"]:
        print(f"WARNING={warning}")
    return 0


def resolve_run_dir(args: argparse.Namespace) -> tuple[Path, bool]:
    if args.run_dir:
        run_dir = args.run_dir if args.run_dir.is_absolute() else WORKSPACE / args.run_dir
        if not (run_dir / "metrics.json").is_file():
            raise SystemExit(
                f"ADVANCED_REPLAY=FAIL reason=missing metrics.json under {relative(run_dir)}"
            )
        metrics = read_json(run_dir / "metrics.json")
        return run_dir, metrics.get("mode") == "dry-run"

    live = latest_run(mode="live", require_result="PASS", require_episode=True)
    if live:
        return live, False
    dry = latest_run(mode="dry-run", require_result="PASS", require_episode=False)
    if dry:
        return dry, True
    raise SystemExit("ADVANCED_REPLAY=FAIL reason=no successful Demo 10 run found")


def latest_run(
    *, mode: str, require_result: str | None, require_episode: bool
) -> Path | None:
    candidates: list[Path] = []
    for run_dir in sorted(LOG_ROOT.glob("*")):
        metrics_path = run_dir / "metrics.json"
        if not metrics_path.is_file():
            continue
        metrics = read_json(metrics_path)
        result_text = read_text(run_dir / "result.txt")
        if metrics.get("mode") != mode:
            continue
        if require_result and metrics.get("result") != require_result:
            continue
        if "RESULT=PASS" not in result_text:
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
    children = sorted(path for path in episodes_root.iterdir() if path.is_dir())
    return children[-1] if children else None


def build_replay(
    *,
    run_dir: Path,
    episode_dir: Path | None,
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    task_status: list[dict[str, Any]],
    metadata: dict[str, Any],
    images: list[dict[str, Any]],
    result_text: str,
    fallback: bool,
) -> dict[str, Any]:
    warnings: list[str] = []
    time_zero = reference_time(observations, actions, task_status, images)
    arm_actions = action_series(actions, "arm_command", time_zero)
    uav_targets = action_series(actions, "uav_target_position_ned", time_zero)
    frames: list[dict[str, Any]] = []
    camera_samples = 0
    target_visible_samples = 0

    for row in observations:
        t = rel_time(row, time_zero)
        platform = point_at(row, "platform", "position_ned")
        if t is None or platform is None:
            continue
        arm = nested(row, "arm")
        target = nested(row, "target")
        yaw = numeric(nested(row, "platform", "yaw_rad"), default=0.0)
        nav = str(nested(row, "platform", "nav_state") or "")
        ee_local = point_value(nested(arm, "end_effector_position"))
        endpoint = add_points(platform, ee_local) if ee_local else None
        target_point = point_value(nested(target, "position"))
        target_visible = bool(nested(target, "visible"))
        if target_visible:
            target_visible_samples += 1
        camera = camera_frustum_for_frame(
            origin=platform,
            yaw=yaw,
            image_row=image_row_at_or_before(images, t, time_zero),
        )
        if camera.get("status") == "ready":
            camera_samples += 1
        frames.append(
            {
                "t": round(t, 4),
                "phase": str(row.get("phase") or ""),
                "nav": nav,
                "uav": platform,
                "yaw": round(yaw, 5),
                "endpoint": endpoint,
                "eeLocal": ee_local,
                "target": target_point,
                "targetVisible": target_visible,
                "joints": float_list(nested(arm, "joint_positions")),
                "jointNames": string_list(nested(arm, "joint_names")),
                "armCommand": nearest_payload(arm_actions, t),
                "uavTarget": nearest_payload(uav_targets, t),
                "camera": camera,
            }
        )

    if not frames:
        raise SystemExit("ADVANCED_REPLAY=FAIL reason=no usable frames")

    phase_markers = phase_marker_samples(events, frames, time_zero)
    command_path = unique_points(
        frame["uavTarget"] for frame in frames if isinstance(frame.get("uavTarget"), dict)
    )
    target_path = unique_points(
        frame["target"] for frame in frames if isinstance(frame.get("target"), dict)
    )
    endpoint_path = unique_points(
        frame["endpoint"] for frame in frames if isinstance(frame.get("endpoint"), dict)
    )
    uav_path = unique_points(frame["uav"] for frame in frames if isinstance(frame.get("uav"), dict))
    workspace = build_workspace(frames)
    safety = build_safety_overlay(frames, metrics)

    if not events:
        warnings.append("sequence_events.jsonl missing or empty")
    if not actions:
        warnings.append("actions.jsonl missing or empty; command path may be incomplete")
    if not task_status:
        warnings.append("task_status.jsonl missing or empty")
    if not target_path:
        warnings.append("target pose evidence missing; replay rendered without target path")
    if not images:
        warnings.append("camera frustum evidence missing; rendered nominal frustum from UAV pose only")
    elif camera_samples == 0:
        warnings.append("camera frustum evidence incomplete; no usable image timestamps found")

    badge = build_badge(metrics, fallback, warnings)
    status = "WARN" if warnings else ("PASS" if metrics.get("result") == "PASS" else "WARN")

    return {
        "schema": "demo10_advanced_replay_v1",
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "timestamp": str(metrics.get("timestamp") or run_dir.name),
        "runDir": relative(run_dir),
        "episodeDir": relative(episode_dir) if episode_dir else None,
        "mode": str(metrics.get("mode") or "unknown"),
        "fallback": fallback,
        "result": metrics.get("result") or result_from_text(result_text),
        "reason": metrics.get("reason") or "",
        "status": status,
        "warnings": warnings,
        "badge": badge,
        "duration": round(frames[-1]["t"], 4),
        "frameCount": len(frames),
        "metrics": summarize_metrics(metrics),
        "metadata": {
            "coordinate_frame": str(metadata.get("coordinate_frame") or ""),
            "topics": metadata.get("topics") if isinstance(metadata.get("topics"), dict) else {},
        },
        "counts": {
            "events": len(events),
            "observations": len(observations),
            "actions": len(actions),
            "taskStatus": len(task_status),
            "images": len(images),
            "cameraSamples": camera_samples,
            "targetVisibleSamples": target_visible_samples,
        },
        "workspace": workspace,
        "safety": safety,
        "phaseMarkers": phase_markers,
        "paths": {
            "uav": uav_path,
            "endpoint": endpoint_path,
            "command": command_path,
            "target": target_path,
        },
        "events": [
            {
                "t": round(t, 4),
                "phase": str(row.get("phase") or ""),
                "event": str(row.get("event") or ""),
                "message": str(row.get("message") or ""),
            }
            for row in events
            if (t := rel_time(row, time_zero)) is not None
        ],
        "frames": frames,
        "outputs": {
            "html": None,
            "summary": None,
            "mp4": None,
            "frames_dir": None,
        },
    }


def build_badge(metrics: dict[str, Any], fallback: bool, warnings: list[str]) -> dict[str, str]:
    mode = str(metrics.get("mode") or "unknown")
    result = str(metrics.get("result") or "UNKNOWN")
    if fallback:
        return {"label": "DRY-RUN FALLBACK", "tone": "warn", "detail": f"{mode} / {result}"}
    if warnings:
        return {"label": "LIVE WARN", "tone": "warn", "detail": f"{mode} / {result}"}
    return {"label": "LIVE PASS", "tone": "pass", "detail": f"{mode} / {result}"}


def phase_marker_samples(
    events: list[dict[str, Any]], frames: list[dict[str, Any]], time_zero: float
) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for row in events:
        t = rel_time(row, time_zero)
        if t is None:
            continue
        frame = nearest_frame(frames, t)
        if frame is None:
            continue
        markers.append(
            {
                "t": round(t, 4),
                "phase": str(row.get("phase") or row.get("event") or ""),
                "message": str(row.get("message") or ""),
                "point": frame.get("uav"),
            }
        )
    return markers


def nearest_frame(frames: list[dict[str, Any]], target_t: float) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for frame in frames:
        if float(frame["t"]) > target_t:
            break
        latest = frame
    return latest or (frames[0] if frames else None)


def build_workspace(frames: list[dict[str, Any]]) -> dict[str, Any]:
    points: list[dict[str, float]] = []
    for frame in frames:
        for key in ("uav", "endpoint", "target", "uavTarget"):
            point = frame.get(key)
            if isinstance(point, dict):
                points.append(point)
    bounds = point_bounds(points, margin=0.22)
    return {
        "bounds": bounds,
        "label": "Observed workspace envelope",
        "altitudeBand": {
            "minAltitudeM": round(max(0.0, -bounds["maxZ"]), 3),
            "maxAltitudeM": round(max(0.0, -bounds["minZ"]), 3),
        },
    }


def build_safety_overlay(frames: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    uav_points = [frame["uav"] for frame in frames if isinstance(frame.get("uav"), dict)]
    target_points = [frame["uavTarget"] for frame in frames if isinstance(frame.get("uavTarget"), dict)]
    all_points = uav_points + target_points
    bounds = point_bounds(all_points, margin=0.5)
    hover_alt = -numeric(target_points[0]["z"], default=2.0) if target_points else 2.0
    max_flight_error = nested(metrics, "flight_error", "limit_m")
    return {
        "bounds": bounds,
        "hoverAltitudeM": round(hover_alt, 3),
        "flightErrorLimitM": numeric(max_flight_error, default=0.55),
        "label": "Safety flight box",
    }


def point_bounds(points: list[dict[str, float]], margin: float) -> dict[str, float]:
    if not points:
        points = [{"x": -1.0, "y": -1.0, "z": -2.0}, {"x": 1.0, "y": 1.0, "z": 0.0}]
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    zs = [float(point["z"]) for point in points]
    return {
        "minX": round(min(xs) - margin, 4),
        "maxX": round(max(xs) + margin, 4),
        "minY": round(min(ys) - margin, 4),
        "maxY": round(max(ys) + margin, 4),
        "minZ": round(min(zs) - margin, 4),
        "maxZ": round(max(zs) + margin, 4),
    }


def camera_frustum_for_frame(
    *, origin: dict[str, float], yaw: float, image_row: dict[str, Any] | None
) -> dict[str, Any]:
    depth = 0.85
    width = 0.55
    height = 0.34
    corners = [
        rotate_and_translate(origin, yaw, depth, sx * width, sz * height)
        for sx in (-1.0, 1.0)
        for sz in (-1.0, 1.0)
    ]
    return {
        "status": "ready" if image_row else "estimated",
        "origin": round_point(origin),
        "corners": corners,
        "fovLabel": "approx 66x44 deg",
    }


def rotate_and_translate(
    origin: dict[str, float], yaw: float, forward: float, lateral: float, vertical: float
) -> dict[str, float]:
    dx = math.cos(yaw) * forward - math.sin(yaw) * lateral
    dy = math.sin(yaw) * forward + math.cos(yaw) * lateral
    dz = vertical
    return round_point({"x": origin["x"] + dx, "y": origin["y"] + dy, "z": origin["z"] + dz})


def image_row_at_or_before(
    images: list[dict[str, Any]], target_t: float, time_zero: float
) -> dict[str, Any] | None:
    latest = None
    for row in images:
        t = rel_time(row, time_zero)
        if t is None:
            continue
        if t > target_t:
            break
        latest = row
    return latest


def action_series(
    actions: list[dict[str, Any]], action_type: str, time_zero: float
) -> list[tuple[float, Any]]:
    out: list[tuple[float, Any]] = []
    for row in actions:
        if row.get("action_type") != action_type:
            continue
        t = rel_time(row, time_zero)
        if t is None:
            continue
        if action_type == "arm_command":
            payload = {
                "jointNames": string_list(row.get("joint_names")),
                "jointPositions": float_list(row.get("joint_positions")),
            }
        else:
            payload = point_value(row.get("target_position_ned"))
        out.append((t, payload))
    return out


def nearest_payload(series: list[tuple[float, Any]], t: float) -> Any:
    latest = None
    for sample_t, payload in series:
        if sample_t > t:
            break
        latest = payload
    return latest


def unique_points(points: Any) -> list[dict[str, float]]:
    out: list[dict[str, float]] = []
    previous: tuple[float, float, float] | None = None
    for point in points:
        if not isinstance(point, dict):
            continue
        marker = (
            round(float(point["x"]), 4),
            round(float(point["y"]), 4),
            round(float(point["z"]), 4),
        )
        if marker != previous:
            out.append({"x": marker[0], "y": marker[1], "z": marker[2]})
            previous = marker
    return out


def summarize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "maxFlightErrorM": nested(metrics, "flight_error", "max_m"),
        "avgFlightErrorM": nested(metrics, "flight_error", "avg_m"),
        "flightErrorLimitM": nested(metrics, "flight_error", "limit_m"),
        "finalEndpointErrorM": nested(metrics, "final_endpoint_error", "error_m"),
        "finalEndpointLimitM": nested(metrics, "final_endpoint_error", "limit_m"),
        "targetVisibleRatio": nested(metrics, "target_visibility", "visible_ratio"),
        "targetVisibleSamples": nested(metrics, "target_visibility", "visible_samples"),
        "jointLimitViolations": nested(metrics, "joint_limits", "violations"),
        "timedOut": nested(metrics, "task_timeout", "timed_out"),
        "durationSec": nested(metrics, "task_timeout", "duration_sec"),
        "sequence": metrics.get("sequence") if isinstance(metrics.get("sequence"), list) else [],
    }


def build_summary(
    replay: dict[str, Any], html_path: Path, summary_path: Path, mp4_path: Path | None
) -> dict[str, Any]:
    outputs = [
        output_entry(html_path, required=True),
        output_entry(summary_path, required=True, exists_override=True),
    ]
    if mp4_path:
        outputs.append(output_entry(mp4_path, required=False))
    return {
        "schema_version": "demo10_advanced_replay_summary_v1",
        "generated_at": replay["generatedAt"],
        "status": replay["status"],
        "badge": replay["badge"],
        "demo": "demo10_air_reach",
        "timestamp": replay["timestamp"],
        "mode": replay["mode"],
        "fallback": replay["fallback"],
        "result": replay["result"],
        "reason": replay["reason"],
        "source_run_dir": absolute_from_relative(replay["runDir"]),
        "episode_dir": absolute_from_relative(replay["episodeDir"]),
        "visualization_dir": str(html_path.parent.parent.resolve()),
        "advanced_dir": str(html_path.parent.resolve()),
        "frame_count": replay["frameCount"],
        "duration_sec": replay["duration"],
        "warnings": replay["warnings"],
        "metrics": replay["metrics"],
        "inputs": replay["counts"],
        "outputs": outputs,
        "mp4": {
            "available": mp4_path is not None,
            "path": str(mp4_path.resolve()) if mp4_path else None,
            "size_bytes": mp4_path.stat().st_size if mp4_path and mp4_path.is_file() else 0,
        },
    }


def output_entry(path: Path, required: bool, exists_override: bool | None = None) -> dict[str, Any]:
    exists = path.is_file() if exists_override is None else exists_override
    return {
        "label": path.name,
        "path": str(path.resolve()),
        "exists": exists,
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "required": required,
    }


def absolute_from_relative(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return str((WORKSPACE / value).resolve())


def generate_mp4_if_available(replay: dict[str, Any], output_root: Path) -> tuple[Path | None, str | None]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None, "ffmpeg not installed; skipped advanced_replay.mp4"

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"matplotlib unavailable for mp4 export: {exc}"

    frames_dir = output_root / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    samples = sample_animation_frames(replay["frames"])
    for index, frame in enumerate(samples):
        fig = plt.figure(figsize=(7.2, 4.8), dpi=120)
        ax = fig.add_subplot(111, projection="3d")
        draw_mp4_frame(ax, replay, frame)
        fig.savefig(frames_dir / f"frame_{index:04d}.png", bbox_inches="tight")
        plt.close(fig)

    mp4_path = output_root / MP4_NAME
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        "18",
        "-i",
        str(frames_dir / "frame_%04d.png"),
        "-vf",
        "scale=960:-2",
        "-pix_fmt",
        "yuv420p",
        str(mp4_path),
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0 or not mp4_path.is_file():
        return None, "ffmpeg failed; skipped advanced_replay.mp4"
    return mp4_path, None


def sample_animation_frames(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(frames) <= 120:
        return frames
    step = max(1, len(frames) // 120)
    sampled = frames[::step]
    if sampled[-1] is not frames[-1]:
        sampled.append(frames[-1])
    return sampled


def draw_mp4_frame(ax: Any, replay: dict[str, Any], frame: dict[str, Any]) -> None:
    bounds = replay["workspace"]["bounds"]
    ax.set_xlim(bounds["minX"], bounds["maxX"])
    ax.set_ylim(bounds["minY"], bounds["maxY"])
    ax.set_zlim(bounds["maxZ"], bounds["minZ"])
    ax.set_xlabel("X north (m)")
    ax.set_ylabel("Y east (m)")
    ax.set_zlabel("Z down (m)")
    ax.set_title(
        f"Demo 10 advanced replay | {replay['badge']['label']} | t={frame['t']:.2f}s",
        fontsize=10,
    )

    current_t = float(frame["t"])
    history = [row for row in replay["frames"] if float(row["t"]) <= current_t]
    path_specs = [
        ("uav", "#0d7c86", 2.4),
        ("endpoint", "#cb5a36", 1.7),
        ("uavTarget", "#c79a22", 1.3),
    ]
    for key, color, width in path_specs:
        points = [row[key] for row in history if isinstance(row.get(key), dict)]
        if len(points) < 2:
            continue
        xs, ys, zs = unzip_points(points)
        ax.plot(xs, ys, zs, color=color, linewidth=width)

    if replay["paths"]["target"]:
        xs, ys, zs = unzip_points(replay["paths"]["target"])
        ax.plot(xs, ys, zs, color="#335fb8", linewidth=1.2, linestyle="--", alpha=0.8)

    for marker in replay["phaseMarkers"]:
        point = marker.get("point")
        if not isinstance(point, dict):
            continue
        ax.scatter(point["x"], point["y"], point["z"], color="#20242c", s=18)

    for label, point, color, size in (
        ("UAV", frame.get("uav"), "#0d7c86", 40),
        ("EE", frame.get("endpoint"), "#cb5a36", 28),
        ("Target", frame.get("target"), "#335fb8", 34),
    ):
        if not isinstance(point, dict):
            continue
        ax.scatter(point["x"], point["y"], point["z"], color=color, s=size)
        ax.text(point["x"], point["y"], point["z"], f" {label}", color=color, fontsize=8)

    camera = frame.get("camera")
    if isinstance(camera, dict):
        origin = camera.get("origin")
        corners = camera.get("corners")
        if isinstance(origin, dict) and isinstance(corners, list) and len(corners) == 4:
            for corner in corners:
                ax.plot(
                    [origin["x"], corner["x"]],
                    [origin["y"], corner["y"]],
                    [origin["z"], corner["z"]],
                    color="#7f8fa6",
                    linewidth=0.8,
                )

    ax.view_init(elev=26.0, azim=-58.0)


def unzip_points(points: list[dict[str, float]]) -> tuple[list[float], list[float], list[float]]:
    return (
        [float(point["x"]) for point in points],
        [float(point["y"]) for point in points],
        [float(point["z"]) for point in points],
    )


def render_html(replay: dict[str, Any]) -> str:
    data = json.dumps(replay, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo 10 Advanced 3D Replay</title>
  <style>
    :root {{
      --bg0: #edf2f6;
      --bg1: #f8fbfd;
      --panel: rgba(255,255,255,0.88);
      --line: rgba(28,48,68,0.14);
      --ink: #142031;
      --muted: #5b697a;
      --uav: #0d7c86;
      --endpoint: #cb5a36;
      --target: #335fb8;
      --command: #c79a22;
      --phase: #20242c;
      --warn: #b3541e;
      --pass: #1f7a48;
      --estimated: #7f8fa6;
      --workspace: rgba(78, 140, 176, 0.13);
      --safety: rgba(190, 150, 36, 0.09);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font: 14px/1.45 "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(145,185,206,0.25), transparent 34%),
        linear-gradient(180deg, var(--bg0) 0%, var(--bg1) 100%);
    }}
    header {{
      padding: 18px 22px 14px;
      background: linear-gradient(135deg, #112030 0%, #24374a 100%);
      color: #f7fafc;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    h1 {{ margin: 0; font-size: 24px; }}
    .subhead {{
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px 16px;
      align-items: center;
      color: rgba(247,250,252,0.86);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.15);
      letter-spacing: 0.04em;
      font-size: 12px;
      font-weight: 700;
    }}
    .badge.pass {{ background: rgba(32,122,72,0.28); }}
    .badge.warn {{ background: rgba(179,84,30,0.3); }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 16px;
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      gap: 14px;
    }}
    .panel {{
      background: var(--panel);
      backdrop-filter: blur(8px);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(17,32,48,0.08);
      overflow: hidden;
    }}
    .scene-wrap {{ padding: 14px; }}
    canvas {{
      width: 100%;
      height: min(72vh, 860px);
      min-height: 540px;
      display: block;
      border-radius: 12px;
      background:
        radial-gradient(circle at 20% 12%, rgba(255,255,255,0.7), transparent 20%),
        linear-gradient(180deg, #fcfdff 0%, #eef4f7 100%);
      border: 1px solid rgba(24,41,61,0.08);
    }}
    .controls {{
      padding: 12px 14px 16px;
      display: grid;
      grid-template-columns: auto 1fr auto auto;
      gap: 10px;
      align-items: center;
    }}
    button, input[type="range"] {{ width: 100%; }}
    button {{
      border: 1px solid rgba(20,32,49,0.18);
      background: #fff;
      color: var(--ink);
      border-radius: 999px;
      min-height: 36px;
      padding: 0 13px;
      cursor: pointer;
      font-weight: 600;
    }}
    .sidebar {{
      display: grid;
      gap: 14px;
      align-self: start;
    }}
    .section {{
      padding: 14px 16px;
    }}
    .section h2 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .stat {{
      padding-top: 8px;
      border-top: 1px solid var(--line);
      min-width: 0;
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 2px;
    }}
    .stat strong {{
      display: block;
      overflow-wrap: anywhere;
      font-size: 14px;
    }}
    .legend, .warnings, .events {{
      display: grid;
      gap: 8px;
    }}
    .legend div, .warnings div {{
      display: flex;
      align-items: center;
      gap: 9px;
    }}
    .swatch {{
      width: 26px;
      height: 3px;
      border-radius: 999px;
      display: inline-block;
      flex: 0 0 auto;
    }}
    .events {{
      max-height: 280px;
      overflow: auto;
    }}
    .event {{
      padding: 8px 0;
      border-bottom: 1px solid rgba(20,32,49,0.08);
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    @media (max-width: 980px) {{
      main {{ grid-template-columns: 1fr; }}
      canvas {{ min-height: 580px; }}
      .controls {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Demo 10 Advanced 3D Replay</h1>
    <div class="subhead">
      <span class="badge {escape(replay["badge"]["tone"])}">{escape(replay["badge"]["label"])} | {escape(replay["badge"]["detail"])}</span>
      <span>Run <code>{escape(str(replay["runDir"]))}</code></span>
      <span>Duration <strong>{replay["duration"]:.2f}s</strong></span>
      <span>Frames <strong>{replay["frameCount"]}</strong></span>
    </div>
  </header>
  <main>
    <section class="panel">
      <div class="scene-wrap">
        <canvas id="scene" width="1440" height="920"></canvas>
      </div>
      <div class="controls">
        <button id="play">Pause</button>
        <input id="time" type="range" min="0" max="1000" value="0">
        <button id="speed">1x</button>
        <button id="view">Orbit On</button>
      </div>
    </section>
    <aside class="sidebar">
      <section class="panel section">
        <h2>Replay State</h2>
        <div class="stats">
          <div class="stat"><span>Time</span><strong id="statTime">0.00 s</strong></div>
          <div class="stat"><span>Frame</span><strong id="statFrame">0 / 0</strong></div>
          <div class="stat"><span>Phase</span><strong id="statPhase">-</strong></div>
          <div class="stat"><span>Nav</span><strong id="statNav">-</strong></div>
          <div class="stat"><span>UAV NED</span><strong id="statUav">-</strong></div>
          <div class="stat"><span>Endpoint NED</span><strong id="statEe">-</strong></div>
          <div class="stat"><span>Target NED</span><strong id="statTarget">-</strong></div>
          <div class="stat"><span>Command NED</span><strong id="statCmd">-</strong></div>
          <div class="stat"><span>Joints</span><strong id="statJoints">-</strong></div>
          <div class="stat"><span>Camera</span><strong id="statCamera">-</strong></div>
          <div class="stat"><span>Flight error limit</span><strong>{fmt_metric(replay["metrics"].get("flightErrorLimitM"))} m</strong></div>
          <div class="stat"><span>Endpoint error</span><strong>{fmt_metric(replay["metrics"].get("finalEndpointErrorM"))} m</strong></div>
        </div>
      </section>
      <section class="panel section">
        <h2>Scene Layers</h2>
        <div class="legend">
          <div><span class="swatch" style="background: var(--uav)"></span> UAV path</div>
          <div><span class="swatch" style="background: var(--endpoint)"></span> Arm endpoint path</div>
          <div><span class="swatch" style="background: var(--target)"></span> Target pose trail</div>
          <div><span class="swatch" style="background: var(--command)"></span> Command path</div>
          <div><span class="swatch" style="background: var(--phase)"></span> Phase markers</div>
          <div><span class="swatch" style="background: var(--estimated)"></span> Camera frustum</div>
        </div>
      </section>
      <section class="panel section">
        <h2>Warnings</h2>
        <div class="warnings" id="warnings"></div>
      </section>
      <section class="panel section">
        <h2>Phase Events</h2>
        <div class="events" id="events"></div>
      </section>
    </aside>
  </main>
  <script id="replay-data" type="application/json">{data}</script>
  <script>
    const replay = JSON.parse(document.getElementById('replay-data').textContent);
    const canvas = document.getElementById('scene');
    const ctx = canvas.getContext('2d');
    const timeInput = document.getElementById('time');
    const playButton = document.getElementById('play');
    const speedButton = document.getElementById('speed');
    const viewButton = document.getElementById('view');
    const speeds = [0.5, 1, 2, 4];
    let speedIndex = 1;
    let playing = true;
    let orbit = true;
    let replayTime = 0;
    let lastNow = performance.now();
    const colors = {{
      uav: css('--uav'),
      endpoint: css('--endpoint'),
      target: css('--target'),
      command: css('--command'),
      phase: css('--phase'),
      warn: css('--warn'),
      pass: css('--pass'),
      ink: css('--ink'),
      muted: css('--muted'),
      estimated: css('--estimated'),
      workspace: css('--workspace'),
      safety: css('--safety')
    }};

    function css(name) {{
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }}

    function frameIndexAt(t) {{
      const frames = replay.frames;
      let lo = 0;
      let hi = frames.length - 1;
      while (lo < hi) {{
        const mid = Math.ceil((lo + hi) / 2);
        if (frames[mid].t <= t) lo = mid;
        else hi = mid - 1;
      }}
      return Math.max(0, lo);
    }}

    function mix(a, b, p) {{
      return a + (b - a) * p;
    }}

    function orbitAngle(t) {{
      return orbit ? (-0.95 + 0.18 * Math.sin(t * 0.22)) : -0.95;
    }}

    function project(point, angle, tilt, scale, centerX, centerY) {{
      const ca = Math.cos(angle);
      const sa = Math.sin(angle);
      const ct = Math.cos(tilt);
      const st = Math.sin(tilt);
      const x1 = point.x * ca - point.y * sa;
      const y1 = point.x * sa + point.y * ca;
      const z1 = point.z;
      const y2 = y1 * ct - z1 * st;
      const z2 = y1 * st + z1 * ct;
      return {{
        x: centerX + x1 * scale,
        y: centerY + y2 * scale,
        depth: z2
      }};
    }}

    function currentScale() {{
      const b = replay.workspace.bounds;
      const spanX = b.maxX - b.minX;
      const spanY = b.maxY - b.minY;
      const spanZ = b.maxZ - b.minZ;
      const span = Math.max(spanX, spanY, Math.abs(spanZ), 0.001);
      const rect = canvas.getBoundingClientRect();
      return Math.min(rect.width, rect.height) * 0.24 / span;
    }}

    function drawCube(bounds, fill, stroke, angle, tilt, scale, centerX, centerY) {{
      const corners = [
        {{x: bounds.minX, y: bounds.minY, z: bounds.minZ}},
        {{x: bounds.maxX, y: bounds.minY, z: bounds.minZ}},
        {{x: bounds.maxX, y: bounds.maxY, z: bounds.minZ}},
        {{x: bounds.minX, y: bounds.maxY, z: bounds.minZ}},
        {{x: bounds.minX, y: bounds.minY, z: bounds.maxZ}},
        {{x: bounds.maxX, y: bounds.minY, z: bounds.maxZ}},
        {{x: bounds.maxX, y: bounds.maxY, z: bounds.maxZ}},
        {{x: bounds.minX, y: bounds.maxY, z: bounds.maxZ}}
      ].map((p) => project(p, angle, tilt, scale, centerX, centerY));
      const faces = [
        [0, 1, 2, 3],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7]
      ];
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      for (const face of faces) {{
        ctx.beginPath();
        ctx.moveTo(corners[face[0]].x, corners[face[0]].y);
        for (let i = 1; i < face.length; i++) ctx.lineTo(corners[face[i]].x, corners[face[i]].y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }}
    }}

    function drawPath(points, untilIndex, color, width, angle, tilt, scale, centerX, centerY, dashed) {{
      ctx.beginPath();
      let started = false;
      for (let i = 0; i <= untilIndex; i++) {{
        const point = points[i];
        if (!point) continue;
        const q = project(point, angle, tilt, scale, centerX, centerY);
        if (!started) {{
          ctx.moveTo(q.x, q.y);
          started = true;
        }} else {{
          ctx.lineTo(q.x, q.y);
        }}
      }}
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.setLineDash(dashed ? [8, 6] : []);
      ctx.stroke();
      ctx.setLineDash([]);
    }}

    function drawMarker(point, color, radius, label, angle, tilt, scale, centerX, centerY) {{
      if (!point) return;
      const q = project(point, angle, tilt, scale, centerX, centerY);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(q.x, q.y, radius, 0, Math.PI * 2);
      ctx.fill();
      if (label) {{
        ctx.fillStyle = colors.ink;
        ctx.font = '12px "Segoe UI", sans-serif';
        ctx.fillText(label, q.x + 8, q.y - 8);
      }}
    }}

    function drawPhaseMarkers(angle, tilt, scale, centerX, centerY) {{
      ctx.fillStyle = colors.phase;
      ctx.font = '11px "Segoe UI", sans-serif';
      for (const marker of replay.phaseMarkers) {{
        const point = marker.point;
        if (!point) continue;
        const q = project(point, angle, tilt, scale, centerX, centerY);
        ctx.beginPath();
        ctx.arc(q.x, q.y, 4.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillText(marker.phase, q.x + 8, q.y + 4);
      }}
    }}

    function drawArmLink(frame, angle, tilt, scale, centerX, centerY) {{
      if (!frame.uav || !frame.endpoint || !frame.eeLocal) return;
      const base = frame.uav;
      const mid = {{
        x: base.x + frame.eeLocal.x * 0.55,
        y: base.y + frame.eeLocal.y * 0.55,
        z: base.z + frame.eeLocal.z * 0.55
      }};
      const points = [base, mid, frame.endpoint].map((p) => project(p, angle, tilt, scale, centerX, centerY));
      ctx.strokeStyle = 'rgba(20,32,49,0.72)';
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      ctx.lineTo(points[1].x, points[1].y);
      ctx.lineTo(points[2].x, points[2].y);
      ctx.stroke();
    }}

    function drawCameraFrustum(frame, angle, tilt, scale, centerX, centerY) {{
      const camera = frame.camera;
      if (!camera || !camera.origin || !camera.corners || camera.corners.length !== 4) return;
      const origin = project(camera.origin, angle, tilt, scale, centerX, centerY);
      const corners = camera.corners.map((corner) => project(corner, angle, tilt, scale, centerX, centerY));
      ctx.strokeStyle = camera.status === 'ready' ? colors.estimated : colors.warn;
      ctx.lineWidth = 1.3;
      ctx.setLineDash(camera.status === 'ready' ? [] : [6, 4]);
      ctx.beginPath();
      ctx.moveTo(corners[0].x, corners[0].y);
      for (let i = 1; i < corners.length; i++) ctx.lineTo(corners[i].x, corners[i].y);
      ctx.closePath();
      ctx.stroke();
      for (const corner of corners) {{
        ctx.beginPath();
        ctx.moveTo(origin.x, origin.y);
        ctx.lineTo(corner.x, corner.y);
        ctx.stroke();
      }}
      ctx.setLineDash([]);
      ctx.fillStyle = colors.estimated;
      ctx.font = '12px "Segoe UI", sans-serif';
      ctx.fillText(camera.status === 'ready' ? 'camera frustum' : 'estimated frustum', origin.x + 8, origin.y + 14);
    }}

    function drawGridFloor(bounds, angle, tilt, scale, centerX, centerY) {{
      ctx.strokeStyle = 'rgba(20,32,49,0.12)';
      ctx.lineWidth = 1;
      const lines = 8;
      for (let i = 0; i <= lines; i++) {{
        const x = mix(bounds.minX, bounds.maxX, i / lines);
        const a = project({{x, y: bounds.minY, z: bounds.maxZ}}, angle, tilt, scale, centerX, centerY);
        const b = project({{x, y: bounds.maxY, z: bounds.maxZ}}, angle, tilt, scale, centerX, centerY);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }}
      for (let i = 0; i <= lines; i++) {{
        const y = mix(bounds.minY, bounds.maxY, i / lines);
        const a = project({{x: bounds.minX, y, z: bounds.maxZ}}, angle, tilt, scale, centerX, centerY);
        const b = project({{x: bounds.maxX, y, z: bounds.maxZ}}, angle, tilt, scale, centerX, centerY);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }}
    }}

    function historicalSeries(key, index) {{
      return replay.frames.slice(0, index + 1).map((frame) => frame[key]).filter(Boolean);
    }}

    function drawScene() {{
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(920, Math.floor(rect.width * dpr));
      canvas.height = Math.max(620, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const w = canvas.width / dpr;
      const h = canvas.height / dpr;
      ctx.clearRect(0, 0, w, h);
      const angle = orbitAngle(replayTime);
      const tilt = -0.78;
      const scale = currentScale();
      const centerX = w * 0.50;
      const centerY = h * 0.56;
      const index = frameIndexAt(replayTime);
      const frame = replay.frames[index];
      const workspace = replay.workspace.bounds;
      const safety = replay.safety.bounds;

      drawGridFloor(workspace, angle, tilt, scale, centerX, centerY);
      drawCube(workspace, colors.workspace, 'rgba(78,140,176,0.22)', angle, tilt, scale, centerX, centerY);
      drawCube(safety, colors.safety, 'rgba(190,150,36,0.28)', angle, tilt, scale, centerX, centerY);
      drawPath(historicalSeries('uav', index), historicalSeries('uav', index).length - 1, colors.uav, 3.1, angle, tilt, scale, centerX, centerY, false);
      drawPath(historicalSeries('endpoint', index), historicalSeries('endpoint', index).length - 1, colors.endpoint, 2.2, angle, tilt, scale, centerX, centerY, false);
      drawPath(historicalSeries('uavTarget', index), historicalSeries('uavTarget', index).length - 1, colors.command, 1.8, angle, tilt, scale, centerX, centerY, true);
      if (replay.paths.target.length) {{
        drawPath(replay.paths.target, replay.paths.target.length - 1, colors.target, 1.6, angle, tilt, scale, centerX, centerY, true);
      }}

      drawPhaseMarkers(angle, tilt, scale, centerX, centerY);
      drawArmLink(frame, angle, tilt, scale, centerX, centerY);
      drawCameraFrustum(frame, angle, tilt, scale, centerX, centerY);
      drawMarker(frame.uav, colors.uav, 8, 'UAV', angle, tilt, scale, centerX, centerY);
      drawMarker(frame.endpoint, colors.endpoint, 6, 'EE', angle, tilt, scale, centerX, centerY);
      drawMarker(frame.target, colors.target, 6, frame.targetVisible ? 'target' : 'target ?', angle, tilt, scale, centerX, centerY);
      drawMarker(frame.uavTarget, colors.command, 5, 'cmd', angle, tilt, scale, centerX, centerY);

      ctx.fillStyle = colors.ink;
      ctx.font = '700 18px "Segoe UI", sans-serif';
      ctx.fillText('Observed workspace', 24, 34);
      ctx.font = '13px "Segoe UI", sans-serif';
      ctx.fillStyle = colors.muted;
      ctx.fillText('Blue box: workspace envelope | Gold box: flight safety box | NED z is down', 24, 56);
      updateStats(index, frame);
    }}

    function fmtPoint(point) {{
      if (!point) return '-';
      return `${{point.x.toFixed(2)}}, ${{point.y.toFixed(2)}}, ${{point.z.toFixed(2)}}`;
    }}

    function updateStats(index, frame) {{
      document.getElementById('statTime').textContent = `${{frame.t.toFixed(2)}} s`;
      document.getElementById('statFrame').textContent = `${{index + 1}} / ${{replay.frames.length}}`;
      document.getElementById('statPhase').textContent = frame.phase || '-';
      document.getElementById('statNav').textContent = frame.nav || '-';
      document.getElementById('statUav').textContent = fmtPoint(frame.uav);
      document.getElementById('statEe').textContent = fmtPoint(frame.endpoint);
      document.getElementById('statTarget').textContent = fmtPoint(frame.target);
      document.getElementById('statCmd').textContent = fmtPoint(frame.uavTarget);
      document.getElementById('statJoints').textContent = frame.joints.length ? frame.joints.map((value) => value.toFixed(3)).join(', ') : '-';
      document.getElementById('statCamera').textContent = frame.camera ? frame.camera.status : '-';
      timeInput.value = String(Math.round(frame.t / Math.max(replay.duration, 0.001) * 1000));
    }}

    function animate(now) {{
      const dt = (now - lastNow) / 1000;
      lastNow = now;
      if (playing) {{
        replayTime += dt * speeds[speedIndex];
        if (replayTime > replay.duration) replayTime = 0;
      }}
      drawScene();
      requestAnimationFrame(animate);
    }}

    playButton.addEventListener('click', () => {{
      playing = !playing;
      playButton.textContent = playing ? 'Pause' : 'Play';
    }});
    speedButton.addEventListener('click', () => {{
      speedIndex = (speedIndex + 1) % speeds.length;
      speedButton.textContent = `${{speeds[speedIndex]}}x`;
    }});
    viewButton.addEventListener('click', () => {{
      orbit = !orbit;
      viewButton.textContent = orbit ? 'Orbit On' : 'Orbit Off';
      drawScene();
    }});
    timeInput.addEventListener('input', () => {{
      replayTime = Number(timeInput.value) / 1000 * replay.duration;
      playing = false;
      playButton.textContent = 'Play';
      drawScene();
    }});
    window.addEventListener('resize', drawScene);

    const warnings = replay.warnings.length ? replay.warnings : ['No warnings'];
    document.getElementById('warnings').innerHTML = warnings.map((entry) =>
      `<div><span class="swatch" style="background:${{entry === 'No warnings' ? colors.pass : colors.warn}}"></span><span>${{entry}}</span></div>`
    ).join('');
    document.getElementById('events').innerHTML = replay.events.map((event) =>
      `<div class="event"><strong>${{event.t.toFixed(2)}}s</strong> ${{event.phase || event.event}}<br><span>${{event.message || ''}}</span></div>`
    ).join('');
    requestAnimationFrame(animate);
  </script>
</body>
</html>
"""


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def reference_time(*groups: list[dict[str, Any]]) -> float:
    values: list[float] = []
    for group in groups:
        for row in group:
            t = absolute_event_time(row)
            if t is not None:
                values.append(t)
    return min(values) if values else 0.0


def absolute_event_time(row: dict[str, Any]) -> float | None:
    for key in ("receipt_time_sec", "stamp_sec"):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def rel_time(row: dict[str, Any], time_zero: float) -> float | None:
    absolute = absolute_event_time(row)
    if absolute is not None:
        return absolute - time_zero
    relative = row.get("t_sec")
    if isinstance(relative, (int, float)) and math.isfinite(float(relative)):
        return float(relative)
    return None


def numeric(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return default


def nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def point_at(row: dict[str, Any], *keys: str) -> dict[str, float] | None:
    return point_value(nested(row, *keys))


def point_value(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": float(value["x"]),
            "y": float(value["y"]),
            "z": float(value["z"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def add_points(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return round_point({"x": a["x"] + b["x"], "y": a["y"] + b["y"], "z": a["z"] + b["z"]})


def round_point(point: dict[str, float]) -> dict[str, float]:
    return {
        "x": round(float(point["x"]), 4),
        "y": round(float(point["y"]), 4),
        "z": round(float(point["z"]), 4),
    }


def float_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    out: list[float] = []
    for item in value:
        if isinstance(item, (int, float)) and math.isfinite(float(item)):
            out.append(round(float(item), 6))
    return out


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def result_from_text(value: str) -> str:
    if "RESULT=PASS" in value:
        return "PASS"
    if "RESULT=FAIL" in value:
        return "FAIL"
    return "UNKNOWN"


def fmt_metric(value: Any) -> str:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return f"{float(value):.3f}"
    return "-"


def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
