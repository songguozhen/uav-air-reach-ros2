#!/usr/bin/env python3
"""Collect the latest visualization evidence into a stable manifest."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[1]
MANIFEST_PATH = WORKSPACE / "visualizations" / "visualization_manifest.json"

STANDARD_DEMOS = [
    ("demo01_hover", "Demo 01 Offboard Hover"),
    ("demo02_waypoint_flight", "Demo 02 Waypoint Flight"),
    ("demo03_circle_trajectory", "Demo 03 Circle Trajectory"),
    ("demo04_external_setpoint", "Demo 04 External Setpoint Bridge"),
]

STANDARD_FILES = [
    "trajectory.csv",
    "trajectory_3d.png",
    "xy_path.png",
    "height_curve.png",
    "speed_curve.png",
    "tracking_error.png",
    "trajectory.mp4",
    "summary.md",
    "result.txt",
]

DEMO10_PLOT_FILES = [
    "trajectory_3d.png",
    "phase_timeline.png",
    "flight_error.png",
    "target_visibility.png",
    "joint_positions.png",
    "endpoint_error.png",
    "summary.json",
    "trajectory_replay.html",
]

DEMO10_ADVANCED_FILES = [
    ("advanced_replay", "advanced_replay.html", True),
    ("advanced_replay_summary", "advanced_replay_summary.json", True),
    ("advanced_replay_mp4", "advanced_replay.mp4", False),
]


def main() -> int:
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"MANIFEST=PASS path={relative(MANIFEST_PATH)}")
    for layer_name, layer in manifest["visualization_layers"].items():
        print(f"LAYER={layer_name} status={layer['status']}")
    for warning in manifest["missing_data_warnings"]:
        print(f"WARNING={warning}")
    return 0


def build_manifest() -> dict[str, Any]:
    standard_demo_sources = [collect_standard_demo(demo_id, title) for demo_id, title in STANDARD_DEMOS]
    demo07_source = collect_demo07_source()
    demo10_live = collect_demo10_run("live")
    demo10_dry_run = collect_demo10_run("dry-run")
    demo10_visuals = collect_demo10_visuals()

    layers = {
        "flight_comparison_3d": build_flight_comparison_layer(standard_demo_sources),
        "advanced_replay": build_advanced_replay_layer(demo10_live, demo10_visuals),
        "workspace_reach_3d": build_workspace_reach_layer(demo10_live, demo10_visuals),
        "diagnostics_dashboard": build_dashboard_layer(demo10_live, demo10_visuals),
        "poster_sheets": build_poster_sheet_layer(standard_demo_sources, demo07_source, demo10_visuals),
        "evidence_index": build_evidence_index_layer(),
    }

    warnings = []
    for layer in layers.values():
        warnings.extend(layer["missing_data_warnings"])

    return {
        "schema_version": "advanced_visualization_manifest_v1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace_root": WORKSPACE.as_posix(),
        "manifest_path": relative(MANIFEST_PATH),
        "source_runs": {
            "demo01_to_demo04": standard_demo_sources,
            "demo07_camera": demo07_source,
            "demo10_live": demo10_live,
            "demo10_dry_run": demo10_dry_run,
            "demo10_visualizations": demo10_visuals,
        },
        "visualization_layers": layers,
        "missing_data_warnings": warnings,
    }


def build_flight_comparison_layer(demos: list[dict[str, Any]]) -> dict[str, Any]:
    selected = []
    warnings = []
    for demo in demos:
        selected.extend(demo["selected_artifacts"])
        if demo["status"] != "PASS":
            warnings.append(f"{demo['id']} latest evidence is {demo['status']}.")

    status = "READY" if not warnings and len(demos) == 4 else "PARTIAL"
    return layer_entry(
        title="Demo 01-04 flight comparison board",
        status=status,
        source_run_paths=[demo["visualization_dir"] for demo in demos if demo["visualization_dir"]],
        selected_artifacts=selected,
        planned_outputs=[
            planned_output("visualizations/demo01_04_comparison/<timestamp>/flight_comparison_3d.html"),
            planned_output("visualizations/demo01_04_comparison/<timestamp>/flight_comparison_3d.mp4"),
        ],
        warnings=warnings,
    )


def build_advanced_replay_layer(
    demo10_live: dict[str, Any], demo10_visuals: dict[str, Any]
) -> dict[str, Any]:
    required = []
    warnings = []
    for key in ("metrics", "sequence_events", "observations", "actions"):
        required.append(demo10_live["selected_artifacts_by_key"][key])
    required.append(demo10_visuals["selected_artifacts_by_key"]["advanced_replay"])
    required.append(demo10_visuals["selected_artifacts_by_key"]["advanced_replay_summary"])
    required.append(demo10_visuals["selected_artifacts_by_key"]["trajectory_3d"])

    optional = [
        demo10_live["selected_artifacts_by_key"]["images_jsonl"],
        demo10_live["selected_artifacts_by_key"]["task_status"],
        demo10_visuals["selected_artifacts_by_key"]["advanced_replay_mp4"],
    ]

    warnings.extend(missing_required_messages(required, "advanced_replay"))
    warnings.extend(missing_optional_messages(optional, "advanced_replay"))
    warnings.extend(demo10_visuals.get("advanced_warnings", []))

    generated_outputs = [
        demo10_visuals["selected_artifacts_by_key"]["advanced_replay"],
        demo10_visuals["selected_artifacts_by_key"]["advanced_replay_summary"],
        demo10_visuals["selected_artifacts_by_key"]["advanced_replay_mp4"],
    ]
    status = "MISSING"
    if all(item["exists"] for item in required):
        status = "GENERATED"
        if any(not item["exists"] for item in optional) or warnings:
            status = "PARTIAL"

    return layer_entry(
        title="Demo 10 advanced 3D replay",
        status=status,
        source_run_paths=compact(
            [
                demo10_live["run_dir"],
                demo10_visuals["visualization_dir"],
                demo10_visuals.get("advanced_dir"),
                demo10_live["episode_dir"],
            ]
        ),
        selected_artifacts=required + optional,
        planned_outputs=generated_outputs,
        warnings=warnings,
    )


def build_workspace_reach_layer(
    demo10_live: dict[str, Any], demo10_visuals: dict[str, Any]
) -> dict[str, Any]:
    required = [
        demo10_live["selected_artifacts_by_key"]["metrics"],
        demo10_live["selected_artifacts_by_key"]["observations"],
        demo10_live["selected_artifacts_by_key"]["actions"],
        demo10_live["selected_artifacts_by_key"]["metadata"],
        demo10_visuals["selected_artifacts_by_key"]["joint_positions"],
        demo10_visuals["selected_artifacts_by_key"]["endpoint_error"],
    ]
    optional = [demo10_live["selected_artifacts_by_key"]["images_jsonl"]]
    warnings = []
    warnings.extend(missing_required_messages(required, "workspace_reach_3d"))
    warnings.extend(missing_optional_messages(optional, "workspace_reach_3d"))

    return layer_entry(
        title="Demo 10 workspace and reach view",
        status=layer_status(required, optional),
        source_run_paths=compact(
            [demo10_live["run_dir"], demo10_visuals["visualization_dir"], demo10_live["episode_dir"]]
        ),
        selected_artifacts=required + optional,
        planned_outputs=[
            planned_output("visualizations/demo10_air_reach/<timestamp>/workspace_reach_3d.html"),
            planned_output("visualizations/demo10_air_reach/<timestamp>/workspace_reach_3d.mp4"),
        ],
        warnings=warnings,
    )


def build_dashboard_layer(
    demo10_live: dict[str, Any], demo10_visuals: dict[str, Any]
) -> dict[str, Any]:
    required = [
        demo10_live["selected_artifacts_by_key"]["metrics"],
        demo10_live["selected_artifacts_by_key"]["sequence_events"],
        demo10_visuals["selected_artifacts_by_key"]["phase_timeline"],
        demo10_visuals["selected_artifacts_by_key"]["flight_error"],
        demo10_visuals["selected_artifacts_by_key"]["target_visibility"],
        demo10_visuals["selected_artifacts_by_key"]["joint_positions"],
        demo10_visuals["selected_artifacts_by_key"]["endpoint_error"],
    ]
    optional = [demo10_live["selected_artifacts_by_key"]["task_status"]]
    warnings = []
    warnings.extend(missing_required_messages(required, "diagnostics_dashboard"))
    warnings.extend(missing_optional_messages(optional, "diagnostics_dashboard"))

    return layer_entry(
        title="Demo 10 diagnostics dashboard",
        status=layer_status(required, optional),
        source_run_paths=compact(
            [demo10_live["run_dir"], demo10_visuals["visualization_dir"], demo10_live["episode_dir"]]
        ),
        selected_artifacts=required + optional,
        planned_outputs=[
            planned_output("visualizations/demo10_air_reach/<timestamp>/diagnostics_dashboard.html"),
        ],
        warnings=warnings,
    )


def build_poster_sheet_layer(
    demos: list[dict[str, Any]], demo07_source: dict[str, Any], demo10_visuals: dict[str, Any]
) -> dict[str, Any]:
    required = []
    warnings = []
    for demo in demos:
        required.append(demo["selected_artifacts_by_key"]["trajectory_3d"])
        required.append(demo["selected_artifacts_by_key"]["tracking_error"])
    required.append(demo10_visuals["selected_artifacts_by_key"]["trajectory_3d"])
    required.append(demo10_visuals["selected_artifacts_by_key"]["phase_timeline"])
    required.append(demo07_source["selected_artifacts_by_key"]["sample_frame"])
    optional = [demo07_source["selected_artifacts_by_key"]["live_target_pose"]]

    warnings.extend(missing_required_messages(required, "poster_sheets"))
    warnings.extend(missing_optional_messages(optional, "poster_sheets"))

    return layer_entry(
        title="Overview and metrics poster sheets",
        status=layer_status(required, optional),
        source_run_paths=compact(
            [
                demo07_source["visualization_dir"],
                demo10_visuals["visualization_dir"],
                *[demo["visualization_dir"] for demo in demos],
            ]
        ),
        selected_artifacts=required + optional,
        planned_outputs=[
            planned_output("visualizations/demo10_air_reach/<timestamp>/overview_sheet.png"),
            planned_output("visualizations/demo10_air_reach/<timestamp>/metrics_sheet.png"),
        ],
        warnings=warnings,
    )


def build_evidence_index_layer() -> dict[str, Any]:
    manifest_entry = {
        "label": "visualization_manifest.json",
        "path": relative(MANIFEST_PATH),
        "exists": True,
        "size_bytes": MANIFEST_PATH.stat().st_size if MANIFEST_PATH.is_file() else 0,
        "required": True,
    }
    return layer_entry(
        title="Machine-readable evidence index",
        status="GENERATED",
        source_run_paths=["visualizations"],
        selected_artifacts=[manifest_entry],
        planned_outputs=[manifest_entry],
        warnings=[],
    )


def collect_standard_demo(demo_id: str, title: str) -> dict[str, Any]:
    vis_root = WORKSPACE / "visualizations" / demo_id
    latest = latest_dir(vis_root)
    selected = []
    selected_by_key = {}
    warnings = []

    if latest:
        for name in ("trajectory.csv", "trajectory_3d.png", "tracking_error.png", "result.txt", "summary.md"):
            info = file_info(latest / name, label=name, required=True)
            selected.append(info)
            selected_by_key[path_key(name)] = info
            if not info["exists"]:
                warnings.append(f"{demo_id} missing required file {name}.")
    else:
        for name in ("trajectory.csv", "trajectory_3d.png", "tracking_error.png", "result.txt", "summary.md"):
            info = missing_info(None, name, required=True)
            selected.append(info)
            selected_by_key[path_key(name)] = info
        warnings.append(f"{demo_id} has no visualization timestamp directory.")

    result_text = read_text((latest / "result.txt") if latest else None)
    status = "PASS" if latest and "RESULT=PASS" in result_text else "MISSING"
    log_dir = corresponding_log_dir("logs", demo_id, latest.name if latest else None)

    return {
        "id": demo_id,
        "title": title,
        "status": status,
        "visualization_dir": relative(latest) if latest else None,
        "log_dir": relative(log_dir) if log_dir else None,
        "result_line": result_text.strip(),
        "selected_artifacts": selected,
        "selected_artifacts_by_key": selected_by_key,
        "warnings": warnings,
    }


def collect_demo07_source() -> dict[str, Any]:
    vis_root = WORKSPACE / "visualizations" / "demo_07_camera"
    latest = latest_dir(vis_root)
    selected_by_key: dict[str, dict[str, Any]] = {}
    selected = []
    warnings = []

    sample = file_info((latest / "sample_frame.png") if latest else None, "sample_frame.png", required=True)
    selected_by_key["sample_frame"] = sample
    selected.append(sample)

    target_pose = file_info(
        (latest / "live_target_pose.yaml") if latest else None,
        "live_target_pose.yaml",
        required=False,
    )
    selected_by_key["live_target_pose"] = target_pose
    selected.append(target_pose)

    bridge_log = file_info(
        (latest / "front_camera_bridge.log") if latest else None,
        "front_camera_bridge.log",
        required=False,
    )
    selected_by_key["front_camera_bridge_log"] = bridge_log
    selected.append(bridge_log)

    status_file = file_info(
        (latest / "sample_frame_status.txt") if latest else None,
        "sample_frame_status.txt",
        required=False,
    )
    selected_by_key["sample_frame_status"] = status_file
    selected.append(status_file)

    if not latest:
        warnings.append("demo_07_camera has no visualization timestamp directory.")
    elif not sample["exists"]:
        if status_file["exists"]:
            warnings.append("demo_07_camera latest evidence has no captured sample_frame.png.")
        else:
            warnings.append("demo_07_camera latest evidence has neither sample_frame.png nor sample_frame_status.txt.")

    return {
        "id": "demo_07_camera",
        "status": "PASS" if latest and sample["exists"] else "PARTIAL",
        "visualization_dir": relative(latest) if latest else None,
        "selected_artifacts": selected,
        "selected_artifacts_by_key": selected_by_key,
        "warnings": warnings,
    }


def collect_demo10_run(mode: str) -> dict[str, Any]:
    root = WORKSPACE / "logs" / "demo10_air_reach"
    run_dir = latest_demo10_run(root, mode)
    episode_dir = latest_dir(run_dir / "episodes") if run_dir else None
    selected_by_key: dict[str, dict[str, Any]] = {}
    selected = []
    warnings = []

    paths = {
        "metrics": (run_dir / "metrics.json") if run_dir else None,
        "sequence_events": (run_dir / "sequence_events.jsonl") if run_dir else None,
        "result": (run_dir / "result.txt") if run_dir else None,
        "stack_readiness": (run_dir / "stack_readiness.txt") if run_dir else None,
        "observations": (episode_dir / "observations.jsonl") if episode_dir else None,
        "actions": (episode_dir / "actions.jsonl") if episode_dir else None,
        "task_status": (episode_dir / "task_status.jsonl") if episode_dir else None,
        "metadata": (episode_dir / "metadata.json") if episode_dir else None,
        "images_jsonl": (episode_dir / "images.jsonl") if episode_dir else None,
    }

    required_keys = {"metrics", "sequence_events", "result"}
    if mode == "live":
        required_keys.update({"observations", "actions", "metadata"})

    for key, path in paths.items():
        info = file_info(path, label=path.name if path else key, required=key in required_keys)
        selected_by_key[key] = info
        selected.append(info)
        if key in required_keys and not info["exists"]:
            warnings.append(f"demo10_{mode} missing required file {info['label']}.")

    result_text = read_text(paths["result"])
    run_status = "PASS" if run_dir and "RESULT=PASS" in result_text else "MISSING"
    if not run_dir:
        warnings.append(f"demo10_air_reach has no successful {mode} run directory.")

    return {
        "id": f"demo10_air_reach_{mode}",
        "status": run_status,
        "run_dir": relative(run_dir) if run_dir else None,
        "episode_dir": relative(episode_dir) if episode_dir else None,
        "selected_artifacts": selected,
        "selected_artifacts_by_key": selected_by_key,
        "warnings": warnings,
    }


def collect_demo10_visuals() -> dict[str, Any]:
    root = WORKSPACE / "visualizations" / "demo10_air_reach"
    vis_dir = latest_dir(root)
    advanced_dir = (vis_dir / "advanced") if vis_dir else None
    selected_by_key: dict[str, dict[str, Any]] = {}
    selected = []
    warnings = []
    advanced_warnings = []

    for name in DEMO10_PLOT_FILES:
        info = file_info((vis_dir / name) if vis_dir else None, label=name, required=True)
        selected.append(info)
        selected_by_key[path_key(name)] = info
        if not info["exists"]:
            warnings.append(f"demo10_visualizations missing required file {name}.")

    summary_data = read_json((vis_dir / "summary.json") if vis_dir else None)
    advanced_summary = read_json((advanced_dir / "advanced_replay_summary.json") if advanced_dir else None)
    for key, name, required in DEMO10_ADVANCED_FILES:
        info = file_info((advanced_dir / name) if advanced_dir else None, label=name, required=required)
        selected.append(info)
        selected_by_key[key] = info
        if not info["exists"] and required:
            warnings.append(f"demo10_visualizations missing required advanced file {name}.")

    if isinstance(advanced_summary.get("warnings"), list):
        advanced_warnings = [str(item) for item in advanced_summary["warnings"]]

    return {
        "id": "demo10_air_reach_visualizations",
        "status": "PASS" if vis_dir and not warnings else "PARTIAL",
        "visualization_dir": relative(vis_dir) if vis_dir else None,
        "advanced_dir": relative(advanced_dir) if advanced_dir and advanced_dir.is_dir() else None,
        "source_run_dir": relativize_string(summary_data.get("source_run_dir")),
        "mode": summary_data.get("mode"),
        "selected_artifacts": selected,
        "selected_artifacts_by_key": selected_by_key,
        "advanced_warnings": advanced_warnings,
        "warnings": warnings if vis_dir else ["demo10_air_reach has no visualization timestamp directory."],
    }


def latest_demo10_run(root: Path, mode: str) -> Path | None:
    if not root.is_dir():
        return None
    matches = []
    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue
        metrics = read_json(candidate / "metrics.json")
        result_text = read_text(candidate / "result.txt")
        if metrics.get("mode") == mode and "RESULT=PASS" in result_text:
            matches.append(candidate)
    return matches[-1] if matches else None


def layer_entry(
    title: str,
    status: str,
    source_run_paths: list[str],
    selected_artifacts: list[dict[str, Any]],
    planned_outputs: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "title": title,
        "status": status,
        "source_run_paths": source_run_paths,
        "selected_artifacts": selected_artifacts,
        "artifact_paths": planned_outputs,
        "missing_data_warnings": warnings,
    }


def layer_status(required: list[dict[str, Any]], optional: list[dict[str, Any]]) -> str:
    if any(not item["exists"] for item in required):
        return "MISSING"
    if any(not item["exists"] for item in optional):
        return "PARTIAL"
    return "READY"


def planned_output(rel_path: str) -> dict[str, Any]:
    return {
        "label": Path(rel_path).name,
        "path": rel_path,
        "exists": False,
        "size_bytes": 0,
        "required": False,
    }


def missing_required_messages(items: list[dict[str, Any]], layer_name: str) -> list[str]:
    return [f"{layer_name} missing required source {item['label']}." for item in items if not item["exists"]]


def missing_optional_messages(items: list[dict[str, Any]], layer_name: str) -> list[str]:
    return [f"{layer_name} missing optional source {item['label']}." for item in items if not item["exists"]]


def corresponding_log_dir(root_name: str, demo_id: str, timestamp: str | None) -> Path | None:
    if not timestamp:
        return None
    path = WORKSPACE / root_name / demo_id / timestamp
    return path if path.is_dir() else None


def latest_dir(root: Path | None) -> Path | None:
    if root is None or not root.is_dir():
        return None
    candidates = sorted(path for path in root.iterdir() if path.is_dir())
    return candidates[-1] if candidates else None


def file_info(path: Path | None, label: str, required: bool) -> dict[str, Any]:
    if path is None:
        return missing_info(None, label, required)
    return {
        "label": label,
        "path": relative(path) if path.exists() else relative(path),
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
        "required": required,
    }


def missing_info(path: Path | None, label: str, required: bool) -> dict[str, Any]:
    return {
        "label": label,
        "path": relative(path) if path else None,
        "exists": False,
        "size_bytes": 0,
        "required": required,
    }


def read_text(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def path_key(filename: str) -> str:
    return Path(filename).stem.replace("-", "_")


def relative(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def relativize_string(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return relative(Path(value))


def compact(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


if __name__ == "__main__":
    raise SystemExit(main())
