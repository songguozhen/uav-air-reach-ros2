#!/usr/bin/env python3
"""Generate Demo 01-04 comparative 3D trajectory visuals."""

from __future__ import annotations

import base64
import csv
import io
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[1]
VIS_ROOT = WORKSPACE / "visualizations"
OUTPUT_ROOT = VIS_ROOT / "flight_comparison"
MANIFEST_PATH = VIS_ROOT / "visualization_manifest.json"
MP4_NAME = "flight_comparison_3d.mp4"
PNG_NAME = "flight_comparison_3d.png"
HTML_NAME = "flight_comparison_3d.html"
SUMMARY_NAME = "summary.json"

DEMOS = [
    ("demo01_hover", "Demo 01 Hover", "#0b6e4f"),
    ("demo02_waypoint_flight", "Demo 02 Waypoint Flight", "#d17a22"),
    ("demo03_circle_trajectory", "Demo 03 Circle Trajectory", "#6b4eff"),
    ("demo04_external_setpoint", "Demo 04 External Setpoint Bridge", "#a11d33"),
]


@dataclass
class DemoData:
    demo_id: str
    title: str
    color: str
    timestamp: str
    vis_dir: Path
    trajectory_path: Path
    summary_path: Path
    result_path: Path
    result: str
    reason: str
    metrics: dict[str, str]
    rows: list[dict[str, float]]
    warnings: list[str]


def main() -> int:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"matplotlib is required: {exc}") from exc

    output_dir = OUTPUT_ROOT / timestamp_now()
    output_dir.mkdir(parents=True, exist_ok=True)

    demos = [load_latest_demo(demo_id, title, color) for demo_id, title, color in DEMOS]
    warnings = [warning for demo in demos for warning in demo.warnings]

    fig = build_figure(demos, plt)
    png_path = output_dir / PNG_NAME
    fig.savefig(png_path, dpi=170, bbox_inches="tight", facecolor="#f7f4ec")
    plt.close(fig)

    html_path = output_dir / HTML_NAME
    write_html(html_path, demos, png_path, warnings)

    mp4_path, mp4_warning = generate_mp4_if_available(demos, output_dir, plt)
    if mp4_warning:
        warnings.append(mp4_warning)

    summary = build_summary(demos, output_dir, png_path, html_path, mp4_path, warnings)
    summary_path = output_dir / SUMMARY_NAME
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    update_manifest(output_dir, png_path, html_path, mp4_path, warnings, summary)

    print(f"COMPARISON_DIR={relative(output_dir)}")
    print(f"HTML={relative(html_path)}")
    print(f"PNG={relative(png_path)}")
    print(f"MP4={relative(mp4_path) if mp4_path else 'SKIPPED'}")
    for demo in demos:
        mp4_file = demo.vis_dir / "trajectory.mp4"
        print(
            "DEMO="
            f"{demo.demo_id} latest={relative(demo.vis_dir)} "
            f"result={demo.result} mp4={'present' if mp4_file.is_file() else 'missing'}"
        )
    for warning in warnings:
        print(f"WARNING={warning}")
    return 0


def load_latest_demo(demo_id: str, title: str, color: str) -> DemoData:
    vis_root = VIS_ROOT / demo_id
    candidates = sorted(path for path in vis_root.iterdir() if path.is_dir()) if vis_root.is_dir() else []
    if not candidates:
        raise SystemExit(f"missing visualization directories for {demo_id}")
    vis_dir = candidates[-1]
    trajectory_path = vis_dir / "trajectory.csv"
    summary_path = vis_dir / "summary.md"
    result_path = vis_dir / "result.txt"
    rows = load_rows(trajectory_path)
    metrics = parse_summary(summary_path)
    result_text = result_path.read_text(encoding="utf-8").strip() if result_path.is_file() else ""
    result = "PASS" if "RESULT=PASS" in result_text else "WARN"
    reason = parse_reason(result_text)
    warnings = []
    if not (vis_dir / "trajectory.mp4").is_file():
        warnings.append(f"{demo_id} latest output lacks trajectory.mp4.")
    if not has_target_path(rows):
        warnings.append(f"{demo_id} trajectory.csv has no target path columns with usable samples.")
    return DemoData(
        demo_id=demo_id,
        title=title,
        color=color,
        timestamp=vis_dir.name,
        vis_dir=vis_dir,
        trajectory_path=trajectory_path,
        summary_path=summary_path,
        result_path=result_path,
        result=result,
        reason=reason,
        metrics=metrics,
        rows=rows,
        warnings=warnings,
    )


def load_rows(path: Path) -> list[dict[str, float]]:
    if not path.is_file():
        raise SystemExit(f"missing trajectory file: {path}")
    rows: list[dict[str, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            row: dict[str, float] = {}
            for key, value in raw.items():
                if key is None:
                    continue
                row[key] = parse_float(value)
            rows.append(row)
    if not rows:
        raise SystemExit(f"empty trajectory file: {path}")
    return rows


def parse_summary(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    if not path.is_file():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and ": " in stripped:
            key, value = stripped[2:].split(": ", 1)
            metrics[key.strip()] = value.strip()
    return metrics


def parse_reason(result_text: str) -> str:
    for token in result_text.split():
        if token.startswith("reason="):
            return token.split("=", 1)[1]
    return "unknown"


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


def has_target_path(rows: list[dict[str, float]]) -> bool:
    count = 0
    for row in rows:
        if all(math.isfinite(row.get(key, math.nan)) for key in ("target_x", "target_y", "target_z")):
            count += 1
        if count >= 2:
            return True
    return False


def build_figure(demos: list[DemoData], plt: Any) -> Any:
    fig = plt.figure(figsize=(14, 9), facecolor="#f7f4ec")
    grid = fig.add_gridspec(2, 2, height_ratios=[2.35, 1.0], width_ratios=[1.8, 1.0])
    ax3d = fig.add_subplot(grid[:, 0], projection="3d")
    ax_alt = fig.add_subplot(grid[0, 1])
    ax_text = fig.add_subplot(grid[1, 1])

    all_x: list[float] = []
    all_y: list[float] = []
    all_z: list[float] = []
    all_alt: list[float] = []

    for demo in demos:
        xs = [row["x"] for row in demo.rows]
        ys = [row["y"] for row in demo.rows]
        zs = [row["z"] for row in demo.rows]
        ts = [row["t"] for row in demo.rows]
        altitudes = [-value for value in zs]
        all_x.extend(xs)
        all_y.extend(ys)
        all_z.extend(zs)
        all_alt.extend(altitudes)

        ax3d.plot(xs, ys, zs, color=demo.color, linewidth=2.4, label=label_for_demo(demo))
        ax3d.scatter(xs[0], ys[0], zs[0], color=demo.color, marker="o", s=42, edgecolors="#111111", linewidths=0.6)
        ax3d.scatter(xs[-1], ys[-1], zs[-1], color=demo.color, marker="X", s=64, edgecolors="#111111", linewidths=0.6)

        target_points = [
            (row["target_x"], row["target_y"], row["target_z"])
            for row in demo.rows
            if all(math.isfinite(row.get(key, math.nan)) for key in ("target_x", "target_y", "target_z"))
        ]
        if len(target_points) >= 2:
            tx = [point[0] for point in target_points]
            ty = [point[1] for point in target_points]
            tz = [point[2] for point in target_points]
            ax3d.plot(tx, ty, tz, color=demo.color, linestyle="--", linewidth=1.3, alpha=0.6)

        ax_alt.plot(ts, altitudes, color=demo.color, linewidth=2.0)
        target_altitudes = [-row["target_z"] for row in demo.rows if math.isfinite(row.get("target_z", math.nan))]
        target_times = [row["t"] for row in demo.rows if math.isfinite(row.get("target_z", math.nan))]
        if len(target_altitudes) >= 2:
            ax_alt.plot(target_times, target_altitudes, color=demo.color, linestyle="--", linewidth=1.0, alpha=0.6)

    x_min, x_max = pad_limits(all_x)
    y_min, y_max = pad_limits(all_y)
    z_min, z_max = pad_limits(all_z)
    alt_min, alt_max = pad_limits(all_alt)

    ax3d.set_xlim(x_min, x_max)
    ax3d.set_ylim(y_min, y_max)
    ax3d.set_zlim(z_max, z_min)
    ax3d.set_xlabel("X north (m)")
    ax3d.set_ylabel("Y east (m)")
    ax3d.set_zlabel("Z down (m)")
    ax3d.set_title("Demo 01-04 Comparative 3D Flight Paths", pad=18, fontsize=14, fontweight="bold")
    ax3d.view_init(elev=24, azim=-58)
    ax3d.grid(True, alpha=0.25)
    ax3d.legend(loc="upper left", fontsize=8, frameon=True)

    ax_alt.set_title("Altitude Profile (-z in NED)", fontsize=12, fontweight="bold")
    ax_alt.set_xlabel("Time (s)")
    ax_alt.set_ylabel("Altitude (m)")
    ax_alt.set_ylim(alt_min, alt_max)
    ax_alt.grid(True, alpha=0.28)

    ax_text.axis("off")
    fig.text(
        0.055,
        0.963,
        "Actual paths use solid lines. Target paths use dashed lines. Circle markers show start; X markers show end.",
        fontsize=10,
        color="#2a2a2a",
    )
    ax_text.text(
        0.0,
        1.02,
        "Latest Run Summary",
        fontsize=12,
        fontweight="bold",
        transform=ax_text.transAxes,
    )
    y = 0.92
    for demo in demos:
        lines = [
            f"{demo.title} [{demo.result}]",
            f"timestamp={demo.timestamp}",
            f"path_length_m={demo.metrics.get('path_length_m', 'n/a')}",
            f"avg_error_3d_m={demo.metrics.get('avg_error_3d_m', 'n/a')}",
            f"final_error_3d_m={demo.metrics.get('final_error_3d_m', 'n/a')}",
        ]
        ax_text.text(
            0.0,
            y,
            "\n".join(lines),
            color=demo.color,
            fontsize=9.4,
            va="top",
            transform=ax_text.transAxes,
        )
        y -= 0.23

    fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.95))
    return fig


def label_for_demo(demo: DemoData) -> str:
    return f"{demo.title} [{demo.result}]"


def pad_limits(values: list[float]) -> tuple[float, float]:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return -1.0, 1.0
    low = min(finite)
    high = max(finite)
    span = max(high - low, 0.5)
    pad = max(0.15 * span, 0.2)
    return low - pad, high + pad


def write_html(path: Path, demos: list[DemoData], png_path: Path, warnings: list[str]) -> None:
    encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
    cards = "\n".join(build_card_html(demo) for demo in demos)
    warning_items = "\n".join(f"<li>{escape_html(item)}</li>" for item in warnings) or "<li>None</li>"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Flight Comparison 3D</title>
  <style>
    :root {{
      --bg: #f7f4ec;
      --ink: #1f1f1f;
      --panel: #fffdf8;
      --line: #d9d1c1;
      --muted: #5a554d;
      --pass: #0b6e4f;
      --warn: #a11d33;
    }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top right, rgba(209,122,34,0.10), transparent 28%),
        radial-gradient(circle at left 20%, rgba(11,110,79,0.10), transparent 24%),
        var(--bg);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 24px 40px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
      letter-spacing: 0.01em;
    }}
    p {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .hero, .panel {{
      background: rgba(255,253,248,0.92);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 36px rgba(51,38,20,0.08);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 22px;
    }}
    .hero img {{
      width: 100%;
      display: block;
      border-radius: 16px;
      border: 1px solid var(--line);
      margin-top: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin-bottom: 22px;
    }}
    .card {{
      padding: 18px;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #fff;
    }}
    .badge.pass {{ background: var(--pass); }}
    .badge.warn {{ background: var(--warn); }}
    dl {{
      margin: 14px 0 0;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 6px 10px;
      font-size: 14px;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; }}
    .panel {{
      padding: 20px 22px;
    }}
    ul {{
      margin: 10px 0 0;
      padding-left: 20px;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>Demo 01-04 Comparative 3D Flight Board</h1>
      <p>Latest timestamped runs from the workspace. Solid lines show actual NED trajectories, dashed lines show target paths when present, and the altitude profile is embedded in the rendered board.</p>
      <img src="data:image/png;base64,{encoded}" alt="3D comparison board">
    </section>
    <section class="grid">
      {cards}
    </section>
    <section class="panel">
      <h2>Warnings</h2>
      <ul>
        {warning_items}
      </ul>
    </section>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def build_card_html(demo: DemoData) -> str:
    badge_class = "pass" if demo.result == "PASS" else "warn"
    final_position = demo.metrics.get("final_position_ned", "n/a")
    return (
        f'<article class="panel card">'
        f"<h2>{escape_html(demo.title)}</h2>"
        f'<div class="badge {badge_class}">{escape_html(demo.result)}</div>'
        "<dl>"
        f"<dt>Timestamp</dt><dd>{escape_html(demo.timestamp)}</dd>"
        f"<dt>Reason</dt><dd>{escape_html(demo.reason)}</dd>"
        f"<dt>Samples</dt><dd>{escape_html(demo.metrics.get('samples', 'n/a'))}</dd>"
        f"<dt>Duration</dt><dd>{escape_html(demo.metrics.get('duration_s', 'n/a'))} s</dd>"
        f"<dt>Path</dt><dd>{escape_html(demo.metrics.get('path_length_m', 'n/a'))} m</dd>"
        f"<dt>Avg Err 3D</dt><dd>{escape_html(demo.metrics.get('avg_error_3d_m', 'n/a'))} m</dd>"
        f"<dt>Final Err 3D</dt><dd>{escape_html(demo.metrics.get('final_error_3d_m', 'n/a'))} m</dd>"
        f"<dt>Final Pos</dt><dd>{escape_html(final_position)}</dd>"
        "</dl>"
        "</article>"
    )


def escape_html(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_mp4_if_available(demos: list[DemoData], output_dir: Path, plt: Any) -> tuple[Path | None, str | None]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None, "ffmpeg not installed; skipped flight_comparison_3d.mp4"

    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_count = 90
    for index in range(frame_count):
        progress = index / max(frame_count - 1, 1)
        fig = plt.figure(figsize=(8.4, 6.0), facecolor="#f7f4ec")
        ax = fig.add_subplot(111, projection="3d")
        draw_mp4_frame(ax, demos, progress)
        fig.tight_layout()
        fig.savefig(frames_dir / f"frame_{index:04d}.png", dpi=120, bbox_inches="tight", facecolor="#f7f4ec")
        plt.close(fig)

    mp4_path = output_dir / MP4_NAME
    completed = subprocess.run(
        [
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
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0 or not mp4_path.is_file():
        return None, "ffmpeg failed; skipped flight_comparison_3d.mp4"
    if mp4_path.stat().st_size > 80 * 1024 * 1024:
        return mp4_path, "flight_comparison_3d.mp4 exceeds 80 MB"
    return mp4_path, None


def draw_mp4_frame(ax: Any, demos: list[DemoData], progress: float) -> None:
    all_x: list[float] = []
    all_y: list[float] = []
    all_z: list[float] = []
    for demo in demos:
        all_x.extend(row["x"] for row in demo.rows)
        all_y.extend(row["y"] for row in demo.rows)
        all_z.extend(row["z"] for row in demo.rows)

        upto = max(2, int(progress * len(demo.rows)))
        current = demo.rows[:upto]
        xs = [row["x"] for row in current]
        ys = [row["y"] for row in current]
        zs = [row["z"] for row in current]
        ax.plot(xs, ys, zs, color=demo.color, linewidth=2.2, label=demo.title if progress < 0.02 else None)
        ax.scatter(xs[-1], ys[-1], zs[-1], color=demo.color, s=28)

        target = [
            (row["target_x"], row["target_y"], row["target_z"])
            for row in current
            if all(math.isfinite(row.get(key, math.nan)) for key in ("target_x", "target_y", "target_z"))
        ]
        if len(target) >= 2:
            ax.plot(
                [point[0] for point in target],
                [point[1] for point in target],
                [point[2] for point in target],
                color=demo.color,
                linestyle="--",
                linewidth=1.0,
                alpha=0.55,
            )

    x_min, x_max = pad_limits(all_x)
    y_min, y_max = pad_limits(all_y)
    z_min, z_max = pad_limits(all_z)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_zlim(z_max, z_min)
    ax.set_xlabel("X north (m)")
    ax.set_ylabel("Y east (m)")
    ax.set_zlabel("Z down (m)")
    ax.set_title(f"Demo 01-04 flight comparison | progress={progress:.0%}", fontsize=11)
    ax.view_init(elev=23, azim=-58 + (progress * 34.0))
    ax.grid(True, alpha=0.25)


def build_summary(
    demos: list[DemoData],
    output_dir: Path,
    png_path: Path,
    html_path: Path,
    mp4_path: Path | None,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "comparison_dir": relative(output_dir),
        "artifacts": {
            "html": relative(html_path),
            "png": relative(png_path),
            "mp4": relative(mp4_path) if mp4_path else relative(output_dir / MP4_NAME),
        },
        "mp4_generated": mp4_path is not None,
        "warnings": warnings,
        "demos": [
            {
                "id": demo.demo_id,
                "title": demo.title,
                "timestamp": demo.timestamp,
                "result": demo.result,
                "reason": demo.reason,
                "visualization_dir": relative(demo.vis_dir),
                "trajectory_csv": relative(demo.trajectory_path),
                "summary_md": relative(demo.summary_path),
                "result_txt": relative(demo.result_path),
                "latest_mp4": relative(demo.vis_dir / "trajectory.mp4") if (demo.vis_dir / "trajectory.mp4").is_file() else None,
                "metrics": demo.metrics,
                "warnings": demo.warnings,
            }
            for demo in demos
        ],
    }


def update_manifest(
    output_dir: Path,
    png_path: Path,
    html_path: Path,
    mp4_path: Path | None,
    warnings: list[str],
    summary: dict[str, Any],
) -> None:
    manifest: dict[str, Any] = {}
    if MANIFEST_PATH.is_file():
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    layers = manifest.setdefault("visualization_layers", {})
    source_runs = manifest.setdefault("source_runs", {})
    layer_warnings = list(dict.fromkeys(warnings))
    selected_artifacts = []
    for label, path in (
        ("flight_comparison_3d.html", html_path),
        ("flight_comparison_3d.png", png_path),
        ("flight_comparison_3d.mp4", mp4_path if mp4_path is not None else output_dir / MP4_NAME),
        ("summary.json", output_dir / SUMMARY_NAME),
    ):
        exists = path is not None and Path(path).is_file()
        selected_artifacts.append(
            {
                "label": label,
                "path": relative(path) if path is not None else None,
                "exists": exists,
                "size_bytes": Path(path).stat().st_size if exists else 0,
                "required": label != "flight_comparison_3d.mp4",
            }
        )

    layers["flight_comparison_3d"] = {
        "title": "Demo 01-04 flight comparison board",
        "status": "GENERATED" if Path(html_path).is_file() and Path(png_path).is_file() else "PARTIAL",
        "source_run_paths": [demo["visualization_dir"] for demo in summary["demos"]],
        "selected_artifacts": selected_artifacts,
        "artifact_paths": selected_artifacts,
        "missing_data_warnings": layer_warnings,
    }
    source_runs["flight_comparison_3d"] = {
        "comparison_dir": relative(output_dir),
        "artifacts": summary["artifacts"],
        "warnings": layer_warnings,
    }
    manifest["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def timestamp_now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def relative(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.resolve().relative_to(WORKSPACE.resolve()).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
