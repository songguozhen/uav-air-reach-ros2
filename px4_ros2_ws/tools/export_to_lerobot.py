#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "air_reach_lerobot_v1"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def discover_episodes(input_root: Path) -> List[Path]:
    if (input_root / "metadata.json").exists():
        return [input_root]
    return sorted(
        path.parent for path in input_root.rglob("metadata.json") if path.parent.name
    )


def nearest_action(
    actions: List[Dict[str, Any]], stamp: float
) -> Optional[Dict[str, Any]]:
    if not actions:
        return None
    return min(actions, key=lambda item: abs(float(item.get("receipt_time_sec", 0.0)) - stamp))


def convert_episode(episode_dir: Path, output_root: Path, copy_images: bool) -> Dict[str, Any]:
    metadata = load_json(episode_dir / "metadata.json")
    result = load_json(episode_dir / "result.json", {"status": "unknown"})
    observations = read_jsonl(episode_dir / "observations.jsonl")
    actions = read_jsonl(episode_dir / "actions.jsonl")
    images = read_jsonl(episode_dir / "images.jsonl")

    episode_id = str(metadata.get("episode_id") or episode_dir.name)
    out_episode_dir = output_root / "episodes" / episode_id
    rows = []
    for index, observation in enumerate(observations):
        stamp = float(observation.get("receipt_time_sec", observation.get("stamp_sec", 0.0)))
        action = nearest_action(actions, stamp)
        rows.append(
            {
                "episode_id": episode_id,
                "frame_index": index,
                "timestamp_sec": stamp,
                "task": metadata.get("task_label", observation.get("task_label", "")),
                "observation": observation,
                "action": action,
                "done": index == len(observations) - 1,
                "success": result.get("status") == "succeeded",
            }
        )

    write_jsonl(out_episode_dir / "frames.jsonl", rows)
    write_json(out_episode_dir / "metadata.json", metadata)
    write_json(out_episode_dir / "result.json", result)

    exported_images = []
    if copy_images:
        for image in images:
            relative_path = Path(str(image.get("relative_path", "")))
            if not relative_path.as_posix():
                continue
            source = episode_dir / relative_path
            target = out_episode_dir / relative_path
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                exported_images.append(relative_path.as_posix())

    return {
        "episode_id": episode_id,
        "source_dir": str(episode_dir),
        "frames": len(rows),
        "actions": len(actions),
        "images": len(images),
        "exported_images": len(exported_images),
        "result_status": result.get("status", "unknown"),
    }


def check_lerobot_available() -> bool:
    try:
        __import__("lerobot")
    except ImportError:
        return False
    return True


def export_dataset(args: argparse.Namespace) -> int:
    input_root = Path(args.input).expanduser()
    output_root = Path(args.output).expanduser()
    output_root.mkdir(parents=True, exist_ok=True)

    episodes = discover_episodes(input_root)
    if not episodes:
        raise SystemExit(f"no episode metadata found under {input_root}")

    summaries = [
        convert_episode(episode_dir, output_root, copy_images=not args.no_copy_images)
        for episode_dir in episodes
    ]
    lerobot_available = check_lerobot_available()
    write_json(
        output_root / "meta" / "dataset.json",
        {
            "schema_version": SCHEMA_VERSION,
            "dataset_name": args.dataset_name,
            "source_root": str(input_root),
            "episode_count": len(summaries),
            "lerobot_package_available": lerobot_available,
            "format_note": (
                "JSONL fallback export. Install LeRobot to convert this directory "
                "to the exact upstream dataset class required by a training job."
            ),
            "episodes": summaries,
        },
    )
    print(
        f"exported {len(summaries)} episode(s) to {output_root}; "
        f"lerobot_available={lerobot_available}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export stage-2 episode recorder output to LeRobot-ready JSONL data."
    )
    parser.add_argument(
        "--input",
        default="logs/stage2_air_reach",
        help="Episode directory, run directory, or logs/<demo> root.",
    )
    parser.add_argument(
        "--output",
        default="datasets/air_reach_v1",
        help="Output dataset root.",
    )
    parser.add_argument("--dataset-name", default="air_reach_v1")
    parser.add_argument(
        "--no-copy-images",
        action="store_true",
        help="Leave image payloads in the raw evidence directory.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return export_dataset(args)


if __name__ == "__main__":
    raise SystemExit(main())
