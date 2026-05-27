import argparse
import importlib.util
import shlex
import subprocess
import sys
from typing import List


def build_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        "-m",
        args.train_module,
        f"--policy.type={args.policy_type}",
        f"--dataset.repo_id={args.dataset_repo_id}",
        f"--output_dir={args.output_dir}",
        f"--job_name={args.job_name}",
    ]
    if args.steps is not None:
        command.append(f"--steps={args.steps}")
    command.extend(args.extra_arg)
    return command


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Small LeRobot training wrapper for high-level UAV/arm action chunks. "
            "The exported dataset should come from tools/export_to_lerobot.py."
        )
    )
    parser.add_argument("--dataset-repo-id", required=True)
    parser.add_argument("--output-dir", default="outputs/lerobot_air_reach")
    parser.add_argument("--job-name", default="air_reach_high_level_policy")
    parser.add_argument("--policy-type", choices=["act", "smolvla"], default="act")
    parser.add_argument("--train-module", default="lerobot.scripts.train")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Additional raw argument passed to the LeRobot train module.",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the command. Without this flag the wrapper prints it only.",
    )
    args = parser.parse_args(argv)

    if importlib.util.find_spec("lerobot") is None:
        print("lerobot package is not importable in this Python environment")
        if args.run:
            return 2

    command = build_command(args)
    print(" ".join(shlex.quote(part) for part in command))
    if not args.run:
        return 0

    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
