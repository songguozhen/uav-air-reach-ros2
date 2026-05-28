#!/usr/bin/env python3
"""Generate an interactive Demo 10 UAV/arm path replay HTML."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
LOG_ROOT = WORKSPACE / "logs" / "demo10_air_reach"
VIS_ROOT = WORKSPACE / "visualizations" / "demo10_air_reach"
REPLAY_NAME = "trajectory_replay.html"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an interactive Demo 10 UAV and arm path replay."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest-live", action="store_true")
    group.add_argument("--run-dir", type=Path)
    args = parser.parse_args()

    run_dir = resolve_run_dir(args)
    metrics = read_json(run_dir / "metrics.json")
    events = read_jsonl(run_dir / "sequence_events.jsonl")
    episode_dir = find_episode_dir(run_dir)
    if episode_dir is None:
        raise SystemExit(f"REPLAY=FAIL reason=no episode directory under {run_dir}")
    observations = read_jsonl(episode_dir / "observations.jsonl")
    actions = read_jsonl(episode_dir / "actions.jsonl")
    if not observations:
        raise SystemExit(f"REPLAY=FAIL reason=no observations in {episode_dir}")

    timestamp = str(metrics.get("timestamp") or run_dir.name)
    output_dir = VIS_ROOT / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / REPLAY_NAME

    replay = build_replay(run_dir, metrics, events, observations, actions)
    output_path.write_text(render_html(replay), encoding="utf-8")
    print(f"REPLAY=PASS path={relative(output_path)} frames={len(replay['frames'])}")
    return 0


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir:
        path = args.run_dir if args.run_dir.is_absolute() else WORKSPACE / args.run_dir
        if not (path / "metrics.json").is_file():
            raise SystemExit(f"REPLAY=FAIL reason=missing metrics.json under {path}")
        return path
    candidates: list[Path] = []
    for run_dir in sorted(LOG_ROOT.glob("*")):
        metrics = read_json(run_dir / "metrics.json")
        result = read_text(run_dir / "result.txt")
        if metrics.get("mode") == "live" and "RESULT=PASS" in result and find_episode_dir(run_dir):
            candidates.append(run_dir)
    if not candidates:
        raise SystemExit("REPLAY=FAIL reason=no successful live Demo 10 episode found")
    return candidates[-1]


def find_episode_dir(run_dir: Path) -> Path | None:
    root = run_dir / "episodes"
    direct = root / run_dir.name
    if direct.is_dir():
        return direct
    if not root.is_dir():
        return None
    children = sorted(path for path in root.iterdir() if path.is_dir())
    return children[-1] if children else None


def build_replay(
    run_dir: Path,
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    time_zero = first_time(observations, actions)
    arm_actions = actions_by_time(actions, "arm_command", time_zero)
    uav_targets = actions_by_time(actions, "uav_target_position_ned", time_zero)
    frames: list[dict[str, Any]] = []

    for row in observations:
        t = rel_time(row, time_zero)
        platform = point_at(row, "platform", "position_ned")
        arm = row.get("arm") if isinstance(row.get("arm"), dict) else {}
        target = row.get("target") if isinstance(row.get("target"), dict) else {}
        ee_local = point_value(arm.get("end_effector_position")) if isinstance(arm, dict) else None
        joints = arm.get("joint_positions") if isinstance(arm, dict) else []
        joint_names = arm.get("joint_names") if isinstance(arm, dict) else []
        if t is None or platform is None:
            continue
        endpoint = add_points(platform, ee_local) if ee_local else None
        target_point = point_value(target.get("position")) if isinstance(target, dict) else None
        frames.append(
            {
                "t": round(t, 4),
                "phase": str(row.get("phase") or ""),
                "nav": nested(row, "platform", "nav_state") or "",
                "uav": platform,
                "endpoint": endpoint,
                "eeLocal": ee_local,
                "target": target_point,
                "targetVisible": bool(target.get("visible")) if isinstance(target, dict) else False,
                "joints": [float(v) for v in joints if isinstance(v, (int, float))],
                "jointNames": [str(v) for v in joint_names] if isinstance(joint_names, list) else [],
                "armCommand": nearest_payload(arm_actions, t),
                "uavTarget": nearest_payload(uav_targets, t),
            }
        )

    if not frames:
        raise SystemExit("REPLAY=FAIL reason=no usable frames")

    bounds = compute_bounds(frames)
    phase_events = [
        {
            "t": rel_time(row, time_zero),
            "phase": str(row.get("phase") or ""),
            "event": str(row.get("event") or ""),
            "message": str(row.get("message") or ""),
        }
        for row in events
        if rel_time(row, time_zero) is not None
    ]
    return {
        "schema": "demo10_replay_v1",
        "runDir": relative(run_dir),
        "timestamp": str(metrics.get("timestamp") or run_dir.name),
        "mode": metrics.get("mode"),
        "result": metrics.get("result"),
        "reason": metrics.get("reason"),
        "metrics": summarize_metrics(metrics),
        "duration": frames[-1]["t"],
        "bounds": bounds,
        "events": phase_events,
        "frames": frames,
    }


def actions_by_time(actions: list[dict[str, Any]], action_type: str, time_zero: float) -> list[tuple[float, Any]]:
    out: list[tuple[float, Any]] = []
    for row in actions:
        if row.get("action_type") != action_type:
            continue
        t = rel_time(row, time_zero)
        if t is None:
            continue
        if action_type == "arm_command":
            payload = {
                "jointNames": row.get("joint_names") or [],
                "jointPositions": row.get("joint_positions") or [],
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


def summarize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "maxFlightErrorM": nested(metrics, "flight_error", "max_m"),
        "flightErrorLimitM": nested(metrics, "flight_error", "limit_m"),
        "finalEndpointErrorM": nested(metrics, "final_endpoint_error", "error_m"),
        "finalEndpointLimitM": nested(metrics, "final_endpoint_error", "limit_m"),
        "targetVisibleRatio": nested(metrics, "target_visibility", "visible_ratio"),
        "jointLimitViolations": nested(metrics, "joint_limits", "violations"),
        "timedOut": nested(metrics, "task_timeout", "timed_out"),
    }


def compute_bounds(frames: list[dict[str, Any]]) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for frame in frames:
        for key in ("uav", "endpoint", "target", "uavTarget"):
            point = frame.get(key)
            if isinstance(point, dict):
                xs.append(float(point["x"]))
                ys.append(float(point["y"]))
                zs.append(float(point["z"]))
    margin = 0.35
    return {
        "minX": min(xs) - margin,
        "maxX": max(xs) + margin,
        "minY": min(ys) - margin,
        "maxY": max(ys) + margin,
        "minZ": min(zs) - margin,
        "maxZ": max(zs) + margin,
    }


def render_html(replay: dict[str, Any]) -> str:
    data = json.dumps(replay, ensure_ascii=False, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Demo 10 UAV Arm Path Replay</title>
  <style>
    :root {{
      --bg: #eef1f4;
      --panel: #fbfcfd;
      --ink: #18212c;
      --muted: #687586;
      --line: #cfd7e2;
      --uav: #126f83;
      --endpoint: #c0472d;
      --target: #2f6fb3;
      --command: #8a6d1f;
      --grid: rgba(24, 33, 44, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #eef1f4 0%, #f8f9fb 100%);
      color: var(--ink);
      font: 14px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 18px 20px;
      background: #18212c;
      color: #fff;
    }}
    h1 {{ margin: 0 0 4px; font-size: 22px; letter-spacing: 0; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 16px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 340px; gap: 14px; align-items: start; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      box-shadow: 0 1px 2px rgba(20, 30, 40, 0.04);
    }}
    canvas {{ display: block; width: 100%; height: min(68vh, 720px); min-height: 520px; background: #fff; border: 1px solid var(--line); border-radius: 6px; }}
    button {{
      border: 1px solid #9aa8b8;
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      min-height: 34px;
      padding: 0 12px;
      cursor: pointer;
    }}
    button:hover {{ background: #f1f4f7; }}
    input[type="range"] {{ width: 100%; }}
    .controls {{ display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; margin-top: 10px; }}
    .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .stat {{ border-top: 1px solid var(--line); padding-top: 8px; min-width: 0; }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; }}
    .stat strong {{ display: block; overflow-wrap: anywhere; }}
    .legend {{ display: grid; gap: 7px; margin-top: 10px; }}
    .legend div {{ display: flex; align-items: center; gap: 8px; }}
    .swatch {{ width: 26px; height: 3px; border-radius: 99px; display: inline-block; }}
    .events {{ max-height: 220px; overflow: auto; border-top: 1px solid var(--line); margin-top: 12px; padding-top: 8px; }}
    .events div {{ padding: 5px 0; border-bottom: 1px solid #edf0f4; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
      canvas {{ min-height: 560px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Demo 10 UAV Arm Path Replay</h1>
    <div>Run: <code>{escape(str(replay["runDir"]))}</code> | mode: <strong>{escape(str(replay["mode"]))}</strong> | result: <strong>{escape(str(replay["result"]))}</strong></div>
  </header>
  <main>
    <div class="grid">
      <section class="panel">
        <canvas id="scene" width="1400" height="820"></canvas>
        <div class="controls">
          <button id="play">Pause</button>
          <input id="time" type="range" min="0" max="1000" value="0">
          <button id="speed">1x</button>
        </div>
      </section>
      <aside class="panel">
        <h2>Replay State</h2>
        <div class="stats">
          <div class="stat"><span>Time</span><strong id="statTime">0.00 s</strong></div>
          <div class="stat"><span>Frame</span><strong id="statFrame">0</strong></div>
          <div class="stat"><span>UAV NED</span><strong id="statUav">-</strong></div>
          <div class="stat"><span>Endpoint NED</span><strong id="statEe">-</strong></div>
          <div class="stat"><span>Joint 1</span><strong id="statJ0">-</strong></div>
          <div class="stat"><span>Joint 2</span><strong id="statJ1">-</strong></div>
          <div class="stat"><span>Max flight error</span><strong>{fmt_metric(replay["metrics"].get("maxFlightErrorM"))} m</strong></div>
          <div class="stat"><span>Endpoint error</span><strong>{fmt_metric(replay["metrics"].get("finalEndpointErrorM"))} m</strong></div>
        </div>
        <div class="legend">
          <div><span class="swatch" style="background: var(--uav)"></span> UAV flight path</div>
          <div><span class="swatch" style="background: var(--endpoint)"></span> End-effector path</div>
          <div><span class="swatch" style="background: var(--target)"></span> Visual target</div>
          <div><span class="swatch" style="background: var(--command)"></span> Commanded UAV target</div>
        </div>
        <div class="events" id="events"></div>
      </aside>
    </div>
  </main>
  <script id="replay-data" type="application/json">{data}</script>
  <script>
    const replay = JSON.parse(document.getElementById('replay-data').textContent);
    const canvas = document.getElementById('scene');
    const ctx = canvas.getContext('2d');
    const timeInput = document.getElementById('time');
    const playButton = document.getElementById('play');
    const speedButton = document.getElementById('speed');
    const speeds = [0.5, 1, 2, 4];
    let speedIndex = 1;
    let playing = true;
    let replayTime = 0;
    let lastNow = performance.now();

    const colors = {{
      uav: getCss('--uav'),
      endpoint: getCss('--endpoint'),
      target: getCss('--target'),
      command: getCss('--command'),
      grid: getCss('--grid'),
      ink: getCss('--ink'),
      muted: getCss('--muted'),
      line: getCss('--line')
    }};

    function getCss(name) {{
      return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }}

    function frameAt(t) {{
      const frames = replay.frames;
      let lo = 0, hi = frames.length - 1;
      while (lo < hi) {{
        const mid = Math.ceil((lo + hi) / 2);
        if (frames[mid].t <= t) lo = mid; else hi = mid - 1;
      }}
      return Math.max(0, lo);
    }}

    function projectTop(p, box) {{
      const b = replay.bounds;
      return {{
        x: box.x + (p.x - b.minX) / Math.max(b.maxX - b.minX, 0.001) * box.w,
        y: box.y + box.h - (p.y - b.minY) / Math.max(b.maxY - b.minY, 0.001) * box.h
      }};
    }}

    function projectSide(p, box) {{
      const b = replay.bounds;
      const alt = -p.z;
      const minAlt = -b.maxZ;
      const maxAlt = -b.minZ;
      return {{
        x: box.x + (p.x - b.minX) / Math.max(b.maxX - b.minX, 0.001) * box.w,
        y: box.y + box.h - (alt - minAlt) / Math.max(maxAlt - minAlt, 0.001) * box.h
      }};
    }}

    function drawPath(frames, index, key, box, project, color, width) {{
      ctx.beginPath();
      let started = false;
      for (let i = 0; i <= index; i++) {{
        const p = frames[i][key];
        if (!p) continue;
        const q = project(p, box);
        if (!started) {{ ctx.moveTo(q.x, q.y); started = true; }}
        else ctx.lineTo(q.x, q.y);
      }}
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.stroke();
    }}

    function drawGrid(box, title, xLabel, yLabel) {{
      ctx.strokeStyle = colors.grid;
      ctx.lineWidth = 1;
      for (let i = 0; i <= 5; i++) {{
        const x = box.x + box.w * i / 5;
        const y = box.y + box.h * i / 5;
        ctx.beginPath(); ctx.moveTo(x, box.y); ctx.lineTo(x, box.y + box.h); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(box.x, y); ctx.lineTo(box.x + box.w, y); ctx.stroke();
      }}
      ctx.strokeStyle = colors.line;
      ctx.strokeRect(box.x, box.y, box.w, box.h);
      ctx.fillStyle = colors.ink;
      ctx.font = '700 18px system-ui, sans-serif';
      ctx.fillText(title, box.x, box.y - 12);
      ctx.fillStyle = colors.muted;
      ctx.font = '12px system-ui, sans-serif';
      ctx.fillText(xLabel, box.x + box.w - 82, box.y + box.h + 24);
      ctx.save();
      ctx.translate(box.x - 32, box.y + 84);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(yLabel, 0, 0);
      ctx.restore();
    }}

    function dot(p, box, project, color, r, label) {{
      if (!p) return;
      const q = project(p, box);
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(q.x, q.y, r, 0, Math.PI * 2);
      ctx.fill();
      if (label) {{
        ctx.fillStyle = colors.ink;
        ctx.font = '12px system-ui, sans-serif';
        ctx.fillText(label, q.x + 8, q.y - 8);
      }}
    }}

    function drawArm(frame, box) {{
      const base = {{x: box.x + box.w * 0.22, y: box.y + box.h * 0.62}};
      const j0 = frame.joints[0] || 0;
      const j1 = frame.joints[1] || 0;
      const l1 = Math.min(box.w, box.h) * 0.22;
      const l2 = Math.min(box.w, box.h) * 0.18;
      const shoulder = -Math.PI / 7 + j0;
      const elbow = shoulder + j1 - Math.PI / 5;
      const p1 = {{x: base.x + Math.cos(shoulder) * l1, y: base.y + Math.sin(shoulder) * l1}};
      const p2 = {{x: p1.x + Math.cos(elbow) * l2, y: p1.y + Math.sin(elbow) * l2}};
      ctx.strokeStyle = '#25313f';
      ctx.lineWidth = 8;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(base.x, base.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
      ctx.fillStyle = colors.endpoint;
      for (const p of [base, p1, p2]) {{
        ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2); ctx.fill();
      }}
      ctx.fillStyle = colors.muted;
      ctx.font = '12px system-ui, sans-serif';
      ctx.fillText('2-DOF arm pose from joint samples', box.x, box.y + box.h + 24);
    }}

    function draw() {{
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(900, Math.floor(rect.width * dpr));
      canvas.height = Math.max(620, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const w = canvas.width / dpr, h = canvas.height / dpr;
      ctx.clearRect(0, 0, w, h);

      const index = frameAt(replayTime);
      const frame = replay.frames[index];
      const top = {{x: 54, y: 58, w: w * 0.57 - 68, h: h * 0.52}};
      const side = {{x: w * 0.57 + 28, y: 58, w: w * 0.38 - 52, h: h * 0.52}};
      const arm = {{x: 54, y: h * 0.68, w: w * 0.42, h: h * 0.22}};
      const notes = {{x: w * 0.53, y: h * 0.68, w: w * 0.40, h: h * 0.22}};

      drawGrid(top, 'Top view: XY flight and end-effector path', 'X north', 'Y east');
      drawGrid(side, 'Side view: X and altitude', 'X north', 'Altitude');
      drawPath(replay.frames, index, 'uav', top, projectTop, colors.uav, 3);
      drawPath(replay.frames, index, 'endpoint', top, projectTop, colors.endpoint, 2);
      drawPath(replay.frames, index, 'uav', side, projectSide, colors.uav, 3);
      drawPath(replay.frames, index, 'endpoint', side, projectSide, colors.endpoint, 2);
      dot(frame.uavTarget, top, projectTop, colors.command, 5, 'cmd');
      dot(frame.target, top, projectTop, colors.target, 6, frame.targetVisible ? 'target' : '');
      dot(frame.uav, top, projectTop, colors.uav, 7, 'UAV');
      dot(frame.endpoint, top, projectTop, colors.endpoint, 5, 'EE');
      dot(frame.uavTarget, side, projectSide, colors.command, 5, 'cmd');
      dot(frame.uav, side, projectSide, colors.uav, 7, 'UAV');
      dot(frame.endpoint, side, projectSide, colors.endpoint, 5, 'EE');

      ctx.strokeStyle = colors.line;
      ctx.strokeRect(arm.x, arm.y, arm.w, arm.h);
      ctx.fillStyle = colors.ink;
      ctx.font = '700 18px system-ui, sans-serif';
      ctx.fillText('Arm configuration', arm.x, arm.y - 12);
      drawArm(frame, arm);

      ctx.strokeStyle = colors.line;
      ctx.strokeRect(notes.x, notes.y, notes.w, notes.h);
      ctx.fillStyle = colors.ink;
      ctx.font = '700 18px system-ui, sans-serif';
      ctx.fillText('Current sample', notes.x + 14, notes.y + 28);
      ctx.font = '14px system-ui, sans-serif';
      ctx.fillText(`phase: ${{frame.phase || 'n/a'}}`, notes.x + 14, notes.y + 60);
      ctx.fillText(`nav: ${{frame.nav || 'n/a'}}`, notes.x + 14, notes.y + 84);
      ctx.fillText(`target visible: ${{frame.targetVisible ? 'yes' : 'no'}}`, notes.x + 14, notes.y + 108);
      ctx.fillText(`reason: ${{replay.reason || 'ok'}}`, notes.x + 14, notes.y + 132);

      updateStats(index, frame);
    }}

    function fmtPoint(p) {{
      if (!p) return '-';
      return `${{p.x.toFixed(2)}}, ${{p.y.toFixed(2)}}, ${{p.z.toFixed(2)}}`;
    }}

    function updateStats(index, frame) {{
      document.getElementById('statTime').textContent = `${{frame.t.toFixed(2)}} s`;
      document.getElementById('statFrame').textContent = `${{index + 1}} / ${{replay.frames.length}}`;
      document.getElementById('statUav').textContent = fmtPoint(frame.uav);
      document.getElementById('statEe').textContent = fmtPoint(frame.endpoint);
      document.getElementById('statJ0').textContent = frame.joints[0] == null ? '-' : `${{frame.joints[0].toFixed(3)}} rad`;
      document.getElementById('statJ1').textContent = frame.joints[1] == null ? '-' : `${{frame.joints[1].toFixed(3)}} rad`;
      timeInput.value = String(Math.round(frame.t / Math.max(replay.duration, 0.001) * 1000));
    }}

    function animate(now) {{
      const dt = (now - lastNow) / 1000;
      lastNow = now;
      if (playing) {{
        replayTime += dt * speeds[speedIndex];
        if (replayTime > replay.duration) replayTime = 0;
      }}
      draw();
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
    timeInput.addEventListener('input', () => {{
      replayTime = Number(timeInput.value) / 1000 * replay.duration;
      playing = false;
      playButton.textContent = 'Play';
      draw();
    }});
    window.addEventListener('resize', draw);

    document.getElementById('events').innerHTML = replay.events.map(e =>
      `<div><strong>${{Number(e.t).toFixed(2)}}s</strong> ${{e.phase || e.event}}<br><span>${{e.message || ''}}</span></div>`
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
        for line in handle:
            line = line.strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def first_time(*groups: list[dict[str, Any]]) -> float:
    values = [t for group in groups for row in group if (t := event_time(row)) is not None]
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
    return t if "t_sec" in row else t - time_zero


def point_at(row: dict[str, Any], *keys: str) -> dict[str, float] | None:
    return point_value(nested(row, *keys))


def point_value(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {"x": float(value["x"]), "y": float(value["y"]), "z": float(value["z"])}
    except (KeyError, TypeError, ValueError):
        return None


def add_points(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    return {"x": left["x"] + right["x"], "y": left["y"] + right["y"], "z": left["z"] + right["z"]}


def nested(row: dict[str, Any], *keys: str) -> Any:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def relative(path: Path) -> str:
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_metric(value: Any) -> str:
    return f"{float(value):.3f}" if isinstance(value, (int, float)) else "-"


if __name__ == "__main__":
    raise SystemExit(main())
