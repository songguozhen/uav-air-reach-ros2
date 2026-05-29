#!/usr/bin/env python3
"""Package reusable MP4 visualization clips from existing evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
VIS_ROOT = WORKSPACE / "visualizations"
MANIFEST_PATH = VIS_ROOT / "visualization_manifest.json"
SUMMARY_PATH = VIS_ROOT / "video_packaging_summary.json"

STANDARD_DEMOS = [
    ("demo01_hover", "Demo 01 Offboard Hover", "#0b6e4f"),
    ("demo02_waypoint_flight", "Demo 02 Waypoint Flight", "#d17a22"),
    ("demo03_circle_trajectory", "Demo 03 Circle Trajectory", "#6b4eff"),
    ("demo04_external_setpoint", "Demo 04 External Setpoint Bridge", "#a11d33"),
]


def main() -> int:
    args = parse_args()
    selections = resolve_selections(args)
    tools = detect_media_tools()
    warnings = list(tools["warnings"])
    targets: list[dict[str, Any]] = []

    if "latest" in selections:
        for demo_id, title, color in STANDARD_DEMOS:
            targets.append(package_latest_demo(demo_id, title, color, tools, args.dry_run))
    if "flight_comparison" in selections:
        targets.append(package_flight_comparison(tools, args.dry_run))
    if "demo10" in selections:
        targets.append(package_demo10_advanced(tools, args.dry_run))
        diagnostics = package_diagnostics_overview(tools, args.dry_run)
        if diagnostics is not None:
            targets.append(diagnostics)

    summary = {
        "schema_version": "video_packaging_summary_v1",
        "generated_at": iso_now(),
        "workspace_root": WORKSPACE.as_posix(),
        "dry_run": args.dry_run,
        "requested": sorted(selections),
        "ffmpeg": tools["ffmpeg"],
        "ffprobe": tools["ffprobe"],
        "warnings": warnings,
        "targets": targets,
    }

    if not args.dry_run:
        SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        update_manifest(summary)

    print(
        "VIDEO_PACKAGING="
        f"{'DRY_RUN' if args.dry_run else 'PASS'} "
        f"summary={relative(SUMMARY_PATH)} "
        f"targets={len(targets)}"
    )
    print(f"FFMPEG={'available' if tools['ffmpeg']['available'] else 'missing'}")
    print(f"FFPROBE={'available' if tools['ffprobe']['available'] else 'missing'}")
    for warning in warnings:
        print(f"WARN={warning}")
    for target in targets:
        print(
            "TARGET="
            f"{target['id']} action={target['action']} "
            f"output={target['output_path']} "
            f"exists={target['exists']}"
        )
        for warning in target["warnings"]:
            print(f"WARN={target['id']}: {warning}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package reusable visualization MP4 clips.")
    parser.add_argument("--latest", action="store_true", help="Package latest Demo 01-04 trajectory.mp4 clips.")
    parser.add_argument("--demo10", action="store_true", help="Package Demo 10 advanced replay and diagnostics overview clips.")
    parser.add_argument(
        "--flight-comparison",
        action="store_true",
        help="Package the latest Demo 01-04 comparison MP4 clip.",
    )
    parser.add_argument("--all", action="store_true", help="Package all supported MP4 targets.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
    return parser.parse_args()


def resolve_selections(args: argparse.Namespace) -> set[str]:
    selections: set[str] = set()
    if args.all:
        selections.update({"latest", "demo10", "flight_comparison"})
    if args.latest:
        selections.add("latest")
    if args.demo10:
        selections.add("demo10")
    if args.flight_comparison:
        selections.add("flight_comparison")
    if not selections:
        raise SystemExit("Specify at least one of --latest, --demo10, --flight-comparison, or --all.")
    return selections


def detect_media_tools() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    warnings = []
    if not ffmpeg:
        warnings.append("ffmpeg unavailable; generation will be skipped and existing MP4s will only be validated.")
    if not ffprobe:
        warnings.append("ffprobe unavailable; codec and duration metadata will be omitted.")
    return {
        "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg},
        "ffprobe": {"available": bool(ffprobe), "path": ffprobe},
        "warnings": warnings,
    }


def package_latest_demo(
    demo_id: str,
    title: str,
    color: str,
    tools: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    vis_dir = find_latest_verified_dir(VIS_ROOT / demo_id)
    if vis_dir is None:
        return missing_target(
            target_id=demo_id,
            title=title,
            output_path=relative(VIS_ROOT / demo_id / "<timestamp>" / "trajectory.mp4"),
            warnings=[f"no verified visualization directory under {relative(VIS_ROOT / demo_id)}"],
        )

    csv_path = vis_dir / "trajectory.csv"
    output_path = vis_dir / "trajectory.mp4"
    frames_dir = vis_dir / "frames" / "trajectory_mp4_packaging"
    warnings = []
    if not csv_path.is_file():
        warnings.append(f"missing source trajectory.csv in {relative(vis_dir)}")
        return target_entry(
            target_id=demo_id,
            title=title,
            kind="latest_demo",
            action="warn",
            output_path=relative(output_path),
            exists=output_path.is_file(),
            source_paths=[relative(vis_dir)],
            warnings=warnings,
            probe=None,
        )

    action = "validate"
    if tools["ffmpeg"]["available"]:
        action = "generate"
        if not dry_run:
            generate_demo_trajectory_mp4(csv_path, frames_dir, output_path, title, color, tools)
    elif not output_path.is_file():
        warnings.append("ffmpeg unavailable and trajectory.mp4 is missing.")
        action = "warn"

    probe = probe_media(output_path, tools)
    return target_entry(
        target_id=demo_id,
        title=title,
        kind="latest_demo",
        action="would_generate" if dry_run and action == "generate" else action,
        output_path=relative(output_path),
        exists=output_path.is_file(),
        source_paths=[relative(csv_path), relative(vis_dir / "result.txt"), relative(vis_dir / "summary.md")],
        warnings=warnings,
        probe=probe,
        extra={"frames_dir": relative(frames_dir)},
    )


def package_flight_comparison(tools: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    output_dir = latest_timestamp_dir(VIS_ROOT / "flight_comparison")
    if output_dir is None:
        return missing_target(
            target_id="flight_comparison_3d",
            title="Demo 01-04 Flight Comparison",
            output_path="visualizations/flight_comparison/<timestamp>/flight_comparison_3d.mp4",
            warnings=["no flight comparison directory found"],
        )

    png_path = output_dir / "flight_comparison_3d.png"
    output_path = output_dir / "flight_comparison_3d.mp4"
    warnings = []
    action = "validate"
    if not png_path.is_file():
        warnings.append(f"missing source PNG {relative(png_path)}")
        action = "warn"
    elif tools["ffmpeg"]["available"]:
        action = "generate"
        if not dry_run:
            generate_looped_still_mp4(
                input_path=png_path,
                output_path=output_path,
                tools=tools,
                duration_sec=5.0,
                fps=24,
            )
    elif not output_path.is_file():
        warnings.append("ffmpeg unavailable and flight_comparison_3d.mp4 is missing.")
        action = "warn"

    probe = probe_media(output_path, tools)
    summary_path = output_dir / "summary.json"
    return target_entry(
        target_id="flight_comparison_3d",
        title="Demo 01-04 Flight Comparison",
        kind="flight_comparison",
        action="would_generate" if dry_run and action == "generate" else action,
        output_path=relative(output_path),
        exists=output_path.is_file(),
        source_paths=[relative(png_path), relative(summary_path)],
        warnings=warnings,
        probe=probe,
    )


def package_demo10_advanced(tools: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    output_dir = latest_advanced_dir()
    if output_dir is None:
        return missing_target(
            target_id="advanced_replay",
            title="Demo 10 Advanced Replay",
            output_path="visualizations/demo10_air_reach/<timestamp>/advanced/advanced_replay.mp4",
            warnings=["no advanced replay directory found"],
        )

    demo_dir = output_dir.parent
    output_path = output_dir / "advanced_replay.mp4"
    frames_dir = output_dir / "frames" / "video_packaging"
    slide_paths = [
        demo_dir / "trajectory_3d.png",
        demo_dir / "phase_timeline.png",
        demo_dir / "flight_error.png",
        demo_dir / "target_visibility.png",
        demo_dir / "joint_positions.png",
        demo_dir / "endpoint_error.png",
    ]
    warnings = [f"missing slide source {relative(path)}" for path in slide_paths if not path.is_file()]
    action = "validate"
    if not warnings and tools["ffmpeg"]["available"]:
        action = "generate"
        if not dry_run:
            generate_slide_video(
                slide_paths=slide_paths,
                frames_dir=frames_dir,
                output_path=output_path,
                title="Demo 10 Advanced Replay",
                tools=tools,
            )
    elif warnings:
        action = "warn" if not output_path.is_file() else "validate"
    elif not output_path.is_file():
        warnings.append("ffmpeg unavailable and advanced_replay.mp4 is missing.")
        action = "warn"

    probe = probe_media(output_path, tools)
    return target_entry(
        target_id="advanced_replay",
        title="Demo 10 Advanced Replay",
        kind="demo10",
        action="would_generate" if dry_run and action == "generate" else action,
        output_path=relative(output_path),
        exists=output_path.is_file(),
        source_paths=[relative(path) for path in slide_paths] + [relative(output_dir / "advanced_replay_summary.json")],
        warnings=warnings,
        probe=probe,
        extra={"frames_dir": relative(frames_dir)},
    )


def package_diagnostics_overview(tools: dict[str, Any], dry_run: bool) -> dict[str, Any] | None:
    diagnostics_dir = latest_timestamp_dir(VIS_ROOT / "diagnostics")
    if diagnostics_dir is None:
        return None

    overview = diagnostics_dir / "overview_sheet.png"
    metrics = diagnostics_dir / "metrics_sheet.png"
    if not overview.is_file() and not metrics.is_file():
        return None

    output_path = diagnostics_dir / "diagnostics_overview.mp4"
    frames_dir = diagnostics_dir / "frames" / "diagnostics_overview"
    slide_paths = [path for path in (overview, metrics) if path.is_file()]
    warnings = []
    action = "validate"
    if tools["ffmpeg"]["available"]:
        action = "generate"
        if not dry_run:
            generate_slide_video(
                slide_paths=slide_paths,
                frames_dir=frames_dir,
                output_path=output_path,
                title="Diagnostics Overview",
                tools=tools,
            )
    elif not output_path.is_file():
        warnings.append("ffmpeg unavailable and diagnostics_overview.mp4 is missing.")
        action = "warn"

    probe = probe_media(output_path, tools)
    return target_entry(
        target_id="diagnostics_overview",
        title="Diagnostics Overview",
        kind="diagnostics",
        action="would_generate" if dry_run and action == "generate" else action,
        output_path=relative(output_path),
        exists=output_path.is_file(),
        source_paths=[relative(path) for path in slide_paths] + [relative(diagnostics_dir / "diagnostics_summary.json")],
        warnings=warnings,
        probe=probe,
        extra={"frames_dir": relative(frames_dir)},
    )


def generate_demo_trajectory_mp4(
    csv_path: Path,
    frames_dir: Path,
    output_path: Path,
    title: str,
    color: str,
    tools: dict[str, Any],
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"matplotlib is required to package {relative(output_path)}: {exc}") from exc

    rows = load_trajectory_rows(csv_path)
    sampled = sample_rows(rows, max_frames=160)
    xs = [row["x"] for row in rows if math.isfinite(row.get("x", math.nan))]
    ys = [row["y"] for row in rows if math.isfinite(row.get("y", math.nan))]
    target_pairs = [
        (row["target_x"], row["target_y"])
        for row in rows
        if math.isfinite(row.get("target_x", math.nan)) and math.isfinite(row.get("target_y", math.nan))
    ]
    x_min, x_max = padded_limits(xs + [pair[0] for pair in target_pairs])
    y_min, y_max = padded_limits(ys + [pair[1] for pair in target_pairs])

    reset_frames_dir(frames_dir)
    for index, row in enumerate(sampled):
        fig, ax = plt.subplots(figsize=(7.2, 7.2), facecolor="#f7f4ec")
        ax.set_facecolor("#fffaf0")
        current = sampled[: index + 1]
        cx = [item["x"] for item in current if math.isfinite(item.get("x", math.nan))]
        cy = [item["y"] for item in current if math.isfinite(item.get("y", math.nan))]
        ax.plot(cx, cy, color=color, linewidth=2.6)
        if cx and cy:
            ax.scatter(cx[0], cy[0], s=48, color=color, edgecolors="#111111", linewidths=0.6, marker="o")
            ax.scatter(cx[-1], cy[-1], s=64, color=color, edgecolors="#111111", linewidths=0.6, marker="X")
        if len(target_pairs) >= 2:
            tx = [pair[0] for pair in target_pairs]
            ty = [pair[1] for pair in target_pairs]
            ax.plot(tx, ty, color="#4b5563", linewidth=1.2, linestyle="--", alpha=0.85)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_xlabel("X north (m)")
        ax.set_ylabel("Y east (m)")
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.grid(True, alpha=0.22)
        ax.set_aspect("equal", adjustable="box")
        altitude = -row["z"] if math.isfinite(row.get("z", math.nan)) else math.nan
        time_sec = row["t"] if math.isfinite(row.get("t", math.nan)) else math.nan
        text = f"t = {time_sec:0.1f}s\nalt = {altitude:0.2f}m"
        ax.text(
            0.02,
            0.98,
            text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=10,
            bbox={"facecolor": "#fffaf0", "edgecolor": "#d6cfc2", "boxstyle": "round,pad=0.35"},
        )
        frame_path = frames_dir / f"frame_{index:05d}.png"
        fig.savefig(frame_path, dpi=130, bbox_inches="tight")
        plt.close(fig)

    encode_frames_to_mp4(frames_dir, output_path, tools, fps=12)


def generate_slide_video(
    slide_paths: list[Path],
    frames_dir: Path,
    output_path: Path,
    title: str,
    tools: dict[str, Any],
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.image as mpimg
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"matplotlib is required to package {relative(output_path)}: {exc}") from exc

    reset_frames_dir(frames_dir)
    frames_per_slide = 36
    frame_index = 0
    for slide_no, slide_path in enumerate(slide_paths, start=1):
        image = mpimg.imread(slide_path)
        for hold in range(frames_per_slide):
            fig = plt.figure(figsize=(12.8, 7.2), facecolor="#f2eee6")
            ax = fig.add_axes([0.04, 0.1, 0.92, 0.82])
            ax.imshow(image)
            ax.axis("off")
            fig.suptitle(title, fontsize=16, fontweight="bold", y=0.97)
            fig.text(
                0.04,
                0.035,
                f"Slide {slide_no}/{len(slide_paths)}  {slide_path.name}",
                fontsize=10,
                color="#3f3f46",
            )
            if hold == 0:
                fig.text(0.04, 0.94, relative(slide_path), fontsize=9, color="#52525b")
            frame_path = frames_dir / f"frame_{frame_index:05d}.png"
            fig.savefig(frame_path, dpi=140)
            plt.close(fig)
            frame_index += 1

    encode_frames_to_mp4(frames_dir, output_path, tools, fps=12)


def generate_looped_still_mp4(
    *,
    input_path: Path,
    output_path: Path,
    tools: dict[str, Any],
    duration_sec: float,
    fps: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        tools["ffmpeg"]["path"],
        "-y",
        "-loop",
        "1",
        "-i",
        str(input_path),
        "-t",
        f"{duration_sec:.2f}",
        "-r",
        str(fps),
        "-vf",
        "scale=1280:-2,format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    run_subprocess(command, f"failed to create {relative(output_path)}")


def encode_frames_to_mp4(frames_dir: Path, output_path: Path, tools: dict[str, Any], fps: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        tools["ffmpeg"]["path"],
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    run_subprocess(command, f"failed to encode {relative(output_path)}")


def load_trajectory_rows(csv_path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row: dict[str, float] = {}
            for key, value in raw.items():
                if key is not None:
                    row[key] = parse_float(value)
            rows.append(row)
    if not rows:
        raise SystemExit(f"empty trajectory data in {relative(csv_path)}")
    return rows


def sample_rows(rows: list[dict[str, float]], max_frames: int) -> list[dict[str, float]]:
    if len(rows) <= max_frames:
        return rows
    step = max(1, math.ceil(len(rows) / max_frames))
    sampled = rows[::step]
    if sampled[-1] is not rows[-1]:
        sampled.append(rows[-1])
    return sampled


def probe_media(path: Path, tools: dict[str, Any]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    result = {
        "path": relative(path),
        "size_bytes": path.stat().st_size,
        "codec": None,
        "duration_sec": None,
    }
    if not tools["ffprobe"]["available"]:
        return result
    command = [
        tools["ffprobe"]["path"],
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return result
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams") or []
    if streams:
        result["codec"] = streams[0].get("codec_name")
    duration = nested_get(payload, ["format", "duration"])
    if duration is not None:
        try:
            result["duration_sec"] = round(float(duration), 3)
        except (TypeError, ValueError):
            pass
    return result


def update_manifest(summary: dict[str, Any]) -> None:
    manifest: dict[str, Any]
    if MANIFEST_PATH.is_file():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = {}
    packaging_targets = []
    for target in summary["targets"]:
        packaging_targets.append(
            {
                "id": target["id"],
                "title": target["title"],
                "output_path": target["output_path"],
                "exists": target["exists"],
                "action": target["action"],
                "codec": nested_get(target, ["media", "codec"]),
                "duration_sec": nested_get(target, ["media", "duration_sec"]),
                "size_bytes": nested_get(target, ["media", "size_bytes"]),
                "source_paths": target["source_paths"],
                "warnings": target["warnings"],
            }
        )
    manifest["video_packaging"] = {
        "generated_at": summary["generated_at"],
        "summary_path": relative(SUMMARY_PATH),
        "ffmpeg": summary["ffmpeg"],
        "ffprobe": summary["ffprobe"],
        "targets": packaging_targets,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def latest_advanced_dir() -> Path | None:
    candidates = []
    for demo_dir in sorted((VIS_ROOT / "demo10_air_reach").glob("*")):
        advanced_dir = demo_dir / "advanced"
        if advanced_dir.is_dir() and (advanced_dir / "advanced_replay_summary.json").is_file():
            candidates.append(advanced_dir)
    return candidates[-1] if candidates else None


def latest_timestamp_dir(root: Path) -> Path | None:
    candidates = sorted(path for path in root.glob("*") if path.is_dir())
    return candidates[-1] if candidates else None


def find_latest_verified_dir(root: Path) -> Path | None:
    candidates = sorted(path for path in root.glob("*") if path.is_dir())
    for path in reversed(candidates):
        result_path = path / "result.txt"
        if result_path.is_file() and "RESULT=PASS" in result_path.read_text(encoding="utf-8", errors="ignore"):
            return path
    return candidates[-1] if candidates else None


def run_subprocess(command: list[str], error_message: str) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise SystemExit(f"{error_message}: {stderr}")


def reset_frames_dir(frames_dir: Path) -> None:
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)


def padded_limits(values: list[float]) -> tuple[float, float]:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return (-1.0, 1.0)
    lower = min(finite)
    upper = max(finite)
    if math.isclose(lower, upper):
        lower -= 1.0
        upper += 1.0
    pad = max((upper - lower) * 0.08, 0.25)
    return lower - pad, upper + pad


def parse_float(value: str | None) -> float:
    if value is None:
        return math.nan
    stripped = value.strip()
    if not stripped:
        return math.nan
    try:
        return float(stripped)
    except ValueError:
        return math.nan


def target_entry(
    *,
    target_id: str,
    title: str,
    kind: str,
    action: str,
    output_path: str,
    exists: bool,
    source_paths: list[str],
    warnings: list[str],
    probe: dict[str, Any] | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "id": target_id,
        "title": title,
        "kind": kind,
        "action": action,
        "output_path": output_path,
        "exists": exists,
        "source_paths": source_paths,
        "warnings": warnings,
        "media": probe or {"path": output_path, "size_bytes": 0, "codec": None, "duration_sec": None},
    }
    if extra:
        entry.update(extra)
    return entry


def missing_target(target_id: str, title: str, output_path: str, warnings: list[str]) -> dict[str, Any]:
    return target_entry(
        target_id=target_id,
        title=title,
        kind="missing",
        action="warn",
        output_path=output_path,
        exists=False,
        source_paths=[],
        warnings=warnings,
        probe=None,
    )


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def nested_get(payload: dict[str, Any], keys: list[str]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
