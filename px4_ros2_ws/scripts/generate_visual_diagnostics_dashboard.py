#!/usr/bin/env python3
"""Generate a 2D diagnostics dashboard and poster sheets from Demo 10 evidence."""

from __future__ import annotations

import base64
import bisect
import io
import json
import math
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
LOG_ROOT = WORKSPACE / "logs" / "demo10_air_reach"
VIS_ROOT = WORKSPACE / "visualizations" / "demo10_air_reach"
DIAG_ROOT = WORKSPACE / "visualizations" / "diagnostics"

EXISTING_PANEL_FILES = {
    "phase_timeline": "phase_timeline.png",
    "flight_error": "flight_error.png",
    "target_visibility": "target_visibility.png",
    "joint_positions": "joint_positions.png",
    "endpoint_error": "endpoint_error.png",
}

GENERATED_FILES = [
    "diagnostics_dashboard.html",
    "overview_sheet.png",
    "metrics_sheet.png",
    "diagnostics_summary.json",
]


def main() -> int:
    try:
        run_dir = latest_live_run()
        if run_dir is None:
            raise RuntimeError("no successful live Demo 10 run with episode evidence found")

        metrics = read_json(run_dir / "metrics.json")
        source_timestamp = str(metrics.get("timestamp") or run_dir.name)
        vis_dir = VIS_ROOT / source_timestamp
        if not vis_dir.is_dir():
            raise RuntimeError(f"missing Demo 10 visualization directory {relative(vis_dir)}")

        output_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = DIAG_ROOT / output_timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        episode_dir = find_episode_dir(run_dir)
        if episode_dir is None:
            raise RuntimeError(f"missing episode directory under {relative(run_dir)}")

        events = read_jsonl(run_dir / "sequence_events.jsonl")
        observations = read_jsonl(episode_dir / "observations.jsonl")
        actions = read_jsonl(episode_dir / "actions.jsonl")
        task_status = read_jsonl(episode_dir / "task_status.jsonl")
        metadata = read_json(episode_dir / "metadata.json")

        context = build_context(
            run_dir=run_dir,
            vis_dir=vis_dir,
            output_dir=output_dir,
            metrics=metrics,
            events=events,
            observations=observations,
            actions=actions,
            task_status=task_status,
            metadata=metadata,
        )
        render_outputs(context)

    except RuntimeError as exc:
        print(f"DIAGNOSTICS=FAIL reason={exc}")
        return 1

    print(
        "DIAGNOSTICS=PASS "
        f"run_dir={context['run_dir']} "
        f"source_visualization_dir={context['vis_dir']} "
        f"output_dir={context['output_dir']} "
        f"status={context['status_label']}"
    )
    for filename in GENERATED_FILES:
        print(f"OUTPUT {context['output_dir'] / filename}")
    for warning in context["warnings"]:
        print(f"WARNING={warning}")
    return 0


def latest_live_run() -> Path | None:
    if not LOG_ROOT.is_dir():
        return None
    candidates: list[Path] = []
    for run_dir in sorted(LOG_ROOT.iterdir()):
        if not run_dir.is_dir():
            continue
        metrics = read_json(run_dir / "metrics.json")
        if metrics.get("mode") != "live" or metrics.get("result") != "PASS":
            continue
        if not has_episode_data(run_dir):
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
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            value = line.strip()
            if not value:
                continue
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid JSONL in {path}:{line_number}: {exc}") from exc
            if isinstance(decoded, dict):
                rows.append(decoded)
    return rows


def build_context(
    *,
    run_dir: Path,
    vis_dir: Path,
    output_dir: Path,
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    task_status: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    time_zero = first_time(events, observations, actions, task_status)

    phases = phase_ranges(events, metrics, time_zero)
    xy_panel = build_xy_panel(observations, actions, time_zero, warnings)
    altitude_panel = build_altitude_panel(observations, actions, phases, time_zero, warnings)
    speed_panel = build_speed_panel(observations, phases, time_zero, warnings)
    status_panel = build_status_panel(metrics, task_status, warnings)
    existing_panels = build_existing_panel_info(vis_dir, warnings)

    panel_status = {
        "phase_timeline": existing_panels["phase_timeline"]["status"],
        "xy_path": xy_panel["status"],
        "altitude": altitude_panel["status"],
        "speed": speed_panel["status"],
        "flight_error": existing_panels["flight_error"]["status"],
        "target_visibility": existing_panels["target_visibility"]["status"],
        "joint_positions": existing_panels["joint_positions"]["status"],
        "endpoint_error": existing_panels["endpoint_error"]["status"],
        "final_task_status": status_panel["status"],
    }

    status_label = "PASS"
    if any(value == "WARN" for value in panel_status.values()):
        status_label = "WARN"

    return {
        "run_dir": run_dir,
        "vis_dir": vis_dir,
        "output_dir": output_dir,
        "metrics": metrics,
        "events": events,
        "observations": observations,
        "actions": actions,
        "task_status": task_status,
        "metadata": metadata,
        "time_zero": time_zero,
        "phases": phases,
        "xy_panel": xy_panel,
        "altitude_panel": altitude_panel,
        "speed_panel": speed_panel,
        "status_panel": status_panel,
        "existing_panels": existing_panels,
        "panel_status": panel_status,
        "status_label": status_label,
        "warnings": dedupe(warnings),
    }


def render_outputs(context: dict[str, Any]) -> None:
    render_dashboard(context)
    render_overview_sheet(context)
    render_metrics_sheet(context)
    write_summary(context)


def first_time(*groups: list[dict[str, Any]]) -> float:
    values: list[float] = []
    for group in groups:
        for row in group:
            timestamp = event_time(row)
            if timestamp is not None:
                values.append(timestamp)
    return min(values) if values else 0.0


def event_time(row: dict[str, Any]) -> float | None:
    for key in ("t_sec", "receipt_time_sec", "stamp_sec"):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def rel_time(row: dict[str, Any], time_zero: float) -> float | None:
    timestamp = event_time(row)
    if timestamp is None:
        return None
    if "t_sec" in row:
        return timestamp
    return timestamp - time_zero


def phase_ranges(
    events: list[dict[str, Any]], metrics: dict[str, Any], time_zero: float
) -> list[dict[str, Any]]:
    rows = sorted(
        [row for row in events if rel_time(row, time_zero) is not None],
        key=lambda row: rel_time(row, time_zero) or 0.0,
    )
    if not rows:
        return []
    duration = numeric(nested(metrics, "task_timeout", "duration_sec")) or (
        (rel_time(rows[-1], time_zero) or 0.0) + 1.0
    )
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        start = rel_time(row, time_zero) or 0.0
        next_start = rel_time(rows[index + 1], time_zero) if index + 1 < len(rows) else duration
        end = max(next_start or duration, start)
        result.append(
            {
                "phase": str(row.get("phase", f"phase_{index + 1}")),
                "message": str(row.get("message", "")),
                "start_sec": start,
                "end_sec": end,
            }
        )
    return result


def build_existing_panel_info(vis_dir: Path, warnings: list[str]) -> dict[str, dict[str, Any]]:
    panels: dict[str, dict[str, Any]] = {}
    for key, filename in EXISTING_PANEL_FILES.items():
        path = vis_dir / filename
        if path.is_file():
            panels[key] = {
                "status": "READY",
                "filename": filename,
                "path": path,
                "message": "reused existing generated PNG",
            }
        else:
            warnings.append(f"{filename} missing under {relative(vis_dir)}; dashboard will show WARN.")
            panels[key] = {
                "status": "WARN",
                "filename": filename,
                "path": path,
                "message": f"WARN: missing {filename}",
            }
    return panels


def build_xy_panel(
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    time_zero: float,
    warnings: list[str],
) -> dict[str, Any]:
    obs_points = [vector(row, "platform", "position_ned") for row in observations]
    obs_points = [point for point in obs_points if point is not None]
    target_points = [
        vector(row, "target_position_ned")
        for row in actions
        if row.get("action_type") == "uav_target_position_ned"
    ]
    target_points = [point for point in target_points if point is not None]

    if not obs_points and not target_points:
        warnings.append("xy_path panel missing both observation and UAV target samples.")
        return {"status": "WARN", "image_data_uri": placeholder_data_uri("WARN\nNo XY samples available")}

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    if obs_points:
        xs = [point[0] for point in obs_points]
        ys = [point[1] for point in obs_points]
        ax.plot(xs, ys, linewidth=2.0, color="#0f766e", label="UAV path")
        ax.scatter([xs[0]], [ys[0]], color="#0f766e", marker="o", s=28, label="start")
        ax.scatter([xs[-1]], [ys[-1]], color="#0f766e", marker="x", s=44, label="end")
    if target_points:
        tx = [point[0] for point in target_points]
        ty = [point[1] for point in target_points]
        ax.plot(tx, ty, linestyle="--", linewidth=1.8, color="#dc2626", label="UAV targets")
    ax.set_title("XY Path")
    ax.set_xlabel("X north (m)")
    ax.set_ylabel("Y east (m)")
    ax.grid(alpha=0.25)
    ax.axis("equal")
    ax.legend(loc="best", fontsize=8)
    return {"status": "READY", "image_data_uri": figure_data_uri(fig)}


def build_altitude_panel(
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    time_zero: float,
    warnings: list[str],
) -> dict[str, Any]:
    obs_times: list[float] = []
    obs_heights: list[float] = []
    for row in observations:
        timestamp = rel_time(row, time_zero)
        point = vector(row, "platform", "position_ned")
        if timestamp is None or point is None:
            continue
        obs_times.append(timestamp)
        obs_heights.append(-point[2])

    target_times: list[float] = []
    target_heights: list[float] = []
    for row in actions:
        if row.get("action_type") != "uav_target_position_ned":
            continue
        timestamp = rel_time(row, time_zero)
        point = vector(row, "target_position_ned")
        if timestamp is None or point is None:
            continue
        target_times.append(timestamp)
        target_heights.append(-point[2])

    if not obs_times and not target_times:
        warnings.append("altitude panel missing observation and target samples.")
        return {"status": "WARN", "image_data_uri": placeholder_data_uri("WARN\nNo altitude samples available")}

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    if obs_times:
        ax.plot(obs_times, obs_heights, color="#1d4ed8", linewidth=2.0, label="UAV height")
    if target_times:
        ax.step(
            target_times,
            target_heights,
            where="post",
            color="#ea580c",
            linewidth=1.6,
            linestyle="--",
            label="Commanded height",
        )
    add_phase_lines(ax, phases)
    ax.set_title("Altitude")
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("Height above NED origin (m)")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    return {"status": "READY", "image_data_uri": figure_data_uri(fig)}


def build_speed_panel(
    observations: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    time_zero: float,
    warnings: list[str],
) -> dict[str, Any]:
    times: list[float] = []
    speeds: list[float] = []
    for row in observations:
        timestamp = rel_time(row, time_zero)
        velocity = vector(row, "platform", "velocity_ned")
        if timestamp is None:
            continue
        if velocity is not None:
            speed = math.sqrt(sum(component * component for component in velocity))
        else:
            speed = None
        if speed is not None:
            times.append(timestamp)
            speeds.append(speed)

    if not times:
        warnings.append("speed panel missing platform velocity samples.")
        return {"status": "WARN", "image_data_uri": placeholder_data_uri("WARN\nNo speed samples available")}

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot(times, speeds, color="#7c3aed", linewidth=2.0, label="Platform speed")
    add_phase_lines(ax, phases)
    ax.set_title("Speed")
    ax.set_xlabel("Time since episode start (s)")
    ax.set_ylabel("Speed (m/s)")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    return {"status": "READY", "image_data_uri": figure_data_uri(fig)}


def build_status_panel(
    metrics: dict[str, Any], task_status: list[dict[str, Any]], warnings: list[str]
) -> dict[str, Any]:
    status_row = task_status[-1] if task_status else {}
    if not task_status:
        warnings.append("final_task_status panel missing task_status.jsonl samples.")
    progress = numeric(status_row.get("progress"))
    timeout = nested(metrics, "task_timeout", "timed_out")
    return {
        "status": "READY" if task_status else "WARN",
        "result": str(metrics.get("result", "UNKNOWN")),
        "reason": str(metrics.get("reason", "unknown")),
        "mode": str(metrics.get("mode", "unknown")),
        "task_status": str(status_row.get("status", "missing")),
        "message": str(status_row.get("message", "task_status.jsonl missing")),
        "progress": progress,
        "timed_out": bool(timeout) if isinstance(timeout, bool) else False,
        "duration_sec": numeric(nested(metrics, "task_timeout", "duration_sec")),
        "limit_sec": numeric(nested(metrics, "task_timeout", "limit_sec")),
        "flight_error_avg_m": numeric(nested(metrics, "flight_error", "avg_m")),
        "flight_error_max_m": numeric(nested(metrics, "flight_error", "max_m")),
        "endpoint_error_m": numeric(nested(metrics, "final_endpoint_error", "error_m")),
        "visible_ratio": numeric(nested(metrics, "target_visibility", "visible_ratio")),
    }


def render_dashboard(context: dict[str, Any]) -> None:
    output_dir = context["output_dir"]
    vis_dir = context["vis_dir"]
    panels = [
        panel_html_from_existing("Phase Timeline", context["existing_panels"]["phase_timeline"], output_dir),
        panel_html_inline("XY Path", context["xy_panel"]),
        panel_html_inline("Altitude", context["altitude_panel"]),
        panel_html_inline("Speed", context["speed_panel"]),
        panel_html_from_existing("Flight Error", context["existing_panels"]["flight_error"], output_dir),
        panel_html_from_existing(
            "Target Visibility", context["existing_panels"]["target_visibility"], output_dir
        ),
        panel_html_from_existing("Joint Positions", context["existing_panels"]["joint_positions"], output_dir),
        panel_html_from_existing("Endpoint Error", context["existing_panels"]["endpoint_error"], output_dir),
        status_card_html(context["status_panel"], context["phases"], vis_dir),
    ]

    phase_rows = "".join(
        f"<tr><td>{escape(item['phase'])}</td><td>{item['start_sec']:.2f}</td><td>{item['end_sec']:.2f}</td><td>{escape(item['message'])}</td></tr>"
        for item in context["phases"]
    )
    warning_rows = "".join(f"<li>{escape(item)}</li>" for item in context["warnings"]) or "<li>None</li>"
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Demo 10 Diagnostics Dashboard</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --panel: #fffdf8;
      --ink: #1b1b18;
      --muted: #6b665f;
      --line: #d8cec0;
      --ok: #166534;
      --warn: #b45309;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "DejaVu Sans", "Liberation Sans", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.12), transparent 28%),
        linear-gradient(180deg, #f7f1e8 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{ max-width: 1680px; margin: 0 auto; padding: 24px; }}
    .hero {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .card {{
      background: rgba(255,253,248,0.96);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 18px 48px rgba(90, 73, 49, 0.08);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      font-size: 14px;
    }}
    .meta code {{ font-size: 12px; }}
    .badge {{
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      font-weight: 700;
      letter-spacing: 0.04em;
      background: #e7f7ee;
      color: var(--ok);
    }}
    .badge.warn {{ background: #fff1dd; color: var(--warn); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      min-height: 360px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: 0 12px 32px rgba(78, 64, 46, 0.08);
    }}
    .panel h3 {{
      font-size: 16px;
      margin-bottom: 0;
    }}
    .panel .sub {{
      color: var(--muted);
      font-size: 12px;
    }}
    .panel img {{
      width: 100%;
      height: auto;
      border-radius: 12px;
      border: 1px solid #e7dfd1;
      background: white;
    }}
    .warn {{
      color: var(--warn);
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      padding: 8px 10px;
      border-bottom: 1px solid #eadfce;
      text-align: left;
      vertical-align: top;
    }}
    ul {{
      padding-left: 18px;
      margin: 0;
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 8px 0 12px;
    }}
    .status-box {{
      background: #f7f1e8;
      border-radius: 12px;
      padding: 10px;
      border: 1px solid #e5d9c7;
    }}
    .footer {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 16px;
      margin-top: 18px;
    }}
    @media (max-width: 1080px) {{
      .hero, .footer, .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <article class="card">
        <h1>Demo 10 2D Diagnostics Dashboard</h1>
        <p>Source run <code>{escape(relative(context['run_dir']))}</code> aligned with visualization set <code>{escape(relative(context['vis_dir']))}</code>.</p>
        <div class="meta">
          <div><strong>Generated at</strong><br />{escape(generated_at)}</div>
          <div><strong>Output dir</strong><br /><code>{escape(relative(context['output_dir']))}</code></div>
          <div><strong>Coordinate frame</strong><br />{escape(str(context["metadata"].get("coordinate_frame", "unknown")))}</div>
          <div><strong>Sequence</strong><br />{escape(", ".join(str(item) for item in context["metrics"].get("sequence", [])))}</div>
        </div>
      </article>
      <article class="card">
        <div class="badge{' warn' if context['status_label'] == 'WARN' else ''}">{escape(context['status_label'])}</div>
        <h2>Panel Coverage</h2>
        <table>
          <tr><th>Panel</th><th>Status</th></tr>
          {''.join(f"<tr><td>{escape(key)}</td><td>{escape(value)}</td></tr>" for key, value in context['panel_status'].items())}
        </table>
      </article>
    </section>
    <section class="grid">
      {''.join(panels)}
    </section>
    <section class="footer">
      <article class="card">
        <h2>Phase Table</h2>
        <table>
          <tr><th>Phase</th><th>Start (s)</th><th>End (s)</th><th>Message</th></tr>
          {phase_rows or '<tr><td colspan="4" class="warn">WARN: no phase rows available</td></tr>'}
        </table>
      </article>
      <article class="card">
        <h2>Warnings</h2>
        <ul>{warning_rows}</ul>
      </article>
    </section>
  </main>
</body>
</html>
"""
    (output_dir / "diagnostics_dashboard.html").write_text(html, encoding="utf-8")


def panel_html_from_existing(title: str, info: dict[str, Any], output_dir: Path) -> str:
    subtitle = escape(str(info["message"]))
    if info["status"] == "READY" and info["path"].is_file():
        rel_path = relative_from(info["path"], output_dir)
        body = f'<img src="{escape(rel_path)}" alt="{escape(title)}" />'
    else:
        body = f'<div class="warn">{escape(str(info["message"]))}</div>'
    return (
        f'<article class="panel"><h3>{escape(title)}</h3><div class="sub">{subtitle}</div>{body}</article>'
    )


def panel_html_inline(title: str, panel: dict[str, Any]) -> str:
    subtitle = "rendered from JSONL/command samples"
    body = f'<img src="{panel["image_data_uri"]}" alt="{escape(title)}" />'
    if panel["status"] == "WARN":
        subtitle = "WARN placeholder due to missing stream"
    return (
        f'<article class="panel"><h3>{escape(title)}</h3><div class="sub">{escape(subtitle)}</div>{body}</article>'
    )


def status_card_html(
    status_panel: dict[str, Any],
    phases: list[dict[str, Any]],
    vis_dir: Path,
) -> str:
    progress = status_panel.get("progress")
    progress_text = f"{progress * 100.0:.0f}%" if isinstance(progress, float) else "n/a"
    duration = status_panel.get("duration_sec")
    limit_sec = status_panel.get("limit_sec")
    phase_text = ", ".join(item["phase"] for item in phases) if phases else "n/a"
    badge_class = "warn" if status_panel["status"] == "WARN" or status_panel["result"] != "PASS" else ""
    replay_rel = relative(vis_dir / "trajectory_replay.html")
    return f"""
<article class="panel">
  <h3>Final Task Status</h3>
  <div class="sub">metrics.json and task_status.jsonl summary</div>
  <div class="badge {badge_class}">{escape(status_panel['result'])}</div>
  <div class="status-grid">
    <div class="status-box"><strong>Task status</strong><br />{escape(status_panel['task_status'])}</div>
    <div class="status-box"><strong>Progress</strong><br />{escape(progress_text)}</div>
    <div class="status-box"><strong>Reason</strong><br />{escape(status_panel['reason'])}</div>
    <div class="status-box"><strong>Mode</strong><br />{escape(status_panel['mode'])}</div>
    <div class="status-box"><strong>Visible ratio</strong><br />{metric_text(status_panel['visible_ratio'], '.2f')}</div>
    <div class="status-box"><strong>Endpoint error</strong><br />{metric_text(status_panel['endpoint_error_m'], '.3f')} m</div>
  </div>
  <table>
    <tr><th>Duration</th><td>{metric_text(duration, '.2f')} / {metric_text(limit_sec, '.2f')} s</td></tr>
    <tr><th>Flight error avg / max</th><td>{metric_text(status_panel['flight_error_avg_m'], '.3f')} / {metric_text(status_panel['flight_error_max_m'], '.3f')} m</td></tr>
    <tr><th>Timed out</th><td>{escape('yes' if status_panel['timed_out'] else 'no')}</td></tr>
    <tr><th>Sequence</th><td>{escape(phase_text)}</td></tr>
    <tr><th>Task message</th><td>{escape(status_panel['message'])}</td></tr>
    <tr><th>Replay</th><td><code>{escape(replay_rel)}</code></td></tr>
  </table>
</article>
"""


def render_overview_sheet(context: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16, 9), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=[0.18, 0.82])
    title_ax = fig.add_subplot(grid[0, :])
    title_ax.axis("off")
    title_ax.text(0.0, 0.72, "Demo 10 Overview Sheet", fontsize=24, fontweight="bold", color="#1f2937")
    title_ax.text(
        0.0,
        0.28,
        f"Source: {relative(context['run_dir'])} | Visuals: {relative(context['vis_dir'])} | Dashboard: {relative(context['output_dir'])}",
        fontsize=10,
        color="#6b7280",
    )
    title_ax.text(
        0.0,
        0.02,
        f"Result={context['metrics'].get('result')} reason={context['metrics'].get('reason')} mode={context['metrics'].get('mode')}",
        fontsize=11,
        color="#0f766e" if context["metrics"].get("result") == "PASS" else "#b45309",
    )

    plot_axes = [
        fig.add_subplot(grid[1, 0]),
        fig.add_subplot(grid[1, 1]),
        fig.add_subplot(grid[1, 2]),
    ]
    render_image_or_warn(plot_axes[0], context["vis_dir"] / "trajectory_3d.png", "Trajectory 3D")
    render_image_or_warn(plot_axes[1], context["vis_dir"] / "phase_timeline.png", "Phase Timeline")
    render_inline_image(plot_axes[2], context["xy_panel"]["image_data_uri"], "XY Path")
    fig.savefig(context["output_dir"] / "overview_sheet.png", dpi=150, facecolor="#f8f3eb")
    plt.close(fig)


def render_metrics_sheet(context: dict[str, Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16, 9), constrained_layout=True)
    grid = fig.add_gridspec(3, 3, height_ratios=[0.20, 0.40, 0.40])
    header_ax = fig.add_subplot(grid[0, :])
    header_ax.axis("off")
    header_ax.text(0.0, 0.70, "Demo 10 Metrics Sheet", fontsize=24, fontweight="bold", color="#1f2937")
    header_ax.text(
        0.0,
        0.28,
        f"Flight avg={metric_text(nested(context['metrics'], 'flight_error', 'avg_m'), '.3f')} m | "
        f"Flight max={metric_text(nested(context['metrics'], 'flight_error', 'max_m'), '.3f')} m | "
        f"Endpoint={metric_text(nested(context['metrics'], 'final_endpoint_error', 'error_m'), '.3f')} m | "
        f"Visibility={metric_text(nested(context['metrics'], 'target_visibility', 'visible_ratio'), '.2f')}",
        fontsize=11,
        color="#6b7280",
    )

    axes = [fig.add_subplot(grid[1, i]) for i in range(3)] + [fig.add_subplot(grid[2, i]) for i in range(3)]
    render_inline_image(axes[0], context["altitude_panel"]["image_data_uri"], "Altitude")
    render_inline_image(axes[1], context["speed_panel"]["image_data_uri"], "Speed")
    render_image_or_warn(axes[2], context["vis_dir"] / "flight_error.png", "Flight Error")
    render_image_or_warn(axes[3], context["vis_dir"] / "target_visibility.png", "Target Visibility")
    render_image_or_warn(axes[4], context["vis_dir"] / "joint_positions.png", "Joint Positions")
    render_image_or_warn(axes[5], context["vis_dir"] / "endpoint_error.png", "Endpoint Error")
    fig.savefig(context["output_dir"] / "metrics_sheet.png", dpi=150, facecolor="#f8f3eb")
    plt.close(fig)


def render_image_or_warn(ax: Any, path: Path, title: str) -> None:
    ax.set_title(title, fontsize=12)
    ax.axis("off")
    if path.is_file():
        ax.imshow(read_image(path))
        return
    ax.text(0.5, 0.5, f"WARN\nMissing {path.name}", ha="center", va="center", fontsize=12, color="#b45309")


def render_inline_image(ax: Any, data_uri: str, title: str) -> None:
    ax.set_title(title, fontsize=12)
    ax.axis("off")
    _, encoded = data_uri.split(",", 1)
    binary = base64.b64decode(encoded)
    ax.imshow(read_image(io.BytesIO(binary)))


def read_image(source: Any) -> Any:
    import matplotlib.image as mpimg

    return mpimg.imread(source)


def write_summary(context: dict[str, Any]) -> None:
    summary = {
        "schema_version": "diagnostics_dashboard_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_run_dir": relative(context["run_dir"]),
        "source_visualization_dir": relative(context["vis_dir"]),
        "diagnostics_dir": relative(context["output_dir"]),
        "status_label": context["status_label"],
        "panel_status": context["panel_status"],
        "metrics_snapshot": {
            "result": context["metrics"].get("result"),
            "reason": context["metrics"].get("reason"),
            "mode": context["metrics"].get("mode"),
            "flight_error": context["metrics"].get("flight_error"),
            "final_endpoint_error": context["metrics"].get("final_endpoint_error"),
            "target_visibility": context["metrics"].get("target_visibility"),
            "task_timeout": context["metrics"].get("task_timeout"),
        },
        "phase_ranges": context["phases"],
        "warnings": context["warnings"],
        "outputs": {
            "diagnostics_dashboard_html": relative(context["output_dir"] / "diagnostics_dashboard.html"),
            "overview_sheet_png": relative(context["output_dir"] / "overview_sheet.png"),
            "metrics_sheet_png": relative(context["output_dir"] / "metrics_sheet.png"),
            "diagnostics_summary_json": relative(context["output_dir"] / "diagnostics_summary.json"),
        },
        "reused_visual_panels": {
            key: relative(info["path"]) if info["path"].is_file() else None
            for key, info in context["existing_panels"].items()
        },
    }
    (context["output_dir"] / "diagnostics_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def flight_error_series(
    observations: list[dict[str, Any]], actions: list[dict[str, Any]], time_zero: float
) -> tuple[list[float], list[float]]:
    target_times: list[float] = []
    target_points: list[tuple[float, float, float]] = []
    for row in actions:
        if row.get("action_type") != "uav_target_position_ned":
            continue
        timestamp = rel_time(row, time_zero)
        point = vector(row, "target_position_ned")
        if timestamp is not None and point is not None:
            target_times.append(timestamp)
            target_points.append(point)
    times: list[float] = []
    errors: list[float] = []
    for row in observations:
        timestamp = rel_time(row, time_zero)
        point = vector(row, "platform", "position_ned")
        if timestamp is None or point is None:
            continue
        index = bisect.bisect_right(target_times, timestamp) - 1
        if index < 0:
            continue
        times.append(timestamp)
        errors.append(distance(point, target_points[index]))
    return times, errors


def add_phase_lines(ax: Any, phases: list[dict[str, Any]]) -> None:
    for phase in phases:
        start = numeric(phase.get("start_sec"))
        if start is not None:
            ax.axvline(start, color="#9ca3af", linewidth=0.8, alpha=0.45)


def figure_data_uri(fig: Any) -> str:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150, facecolor="white")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    fig.clf()
    return f"data:image/png;base64,{encoded}"


def placeholder_data_uri(message: str) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes, color="#b45309")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(False)
    return figure_data_uri(fig)


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
    if any(item is None for item in coords):
        return None
    return (coords[0], coords[1], coords[2])  # type: ignore[return-value]


def numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def metric_text(value: Any, fmt: str) -> str:
    number = numeric(value)
    if number is None:
        return "n/a"
    return format(number, fmt)


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def relative(path: Path) -> str:
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def relative_from(path: Path, start: Path) -> str:
    return os.path.relpath(path, start)


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


if __name__ == "__main__":
    sys.exit(main())
