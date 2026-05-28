#!/usr/bin/env python3
"""Deterministic stage-2 frame and schema regression checker."""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
CONTROL_SRC = WORKSPACE_ROOT / "src" / "aerial_manip_control"
sys.path.insert(0, str(CONTROL_SRC))

from aerial_manip_control.stage2_schema import (  # noqa: E402
    CANONICAL_ARM_DOF,
    CANONICAL_ARM_JOINT_NAMES,
    CANONICAL_FRAMES,
    CANONICAL_TF_CHAIN,
    DEFAULT_ARM_BASE_XYZ,
    DEFAULT_ARM_MAX_POSITIONS,
    DEFAULT_ARM_MAX_VELOCITIES,
    DEFAULT_ARM_MIN_POSITIONS,
    DEFAULT_CAMERA_XYZ,
    PLATFORM_NED_FRAME,
    enu_to_ned_xyz,
    ned_to_enu_xyz,
)


Check = Dict[str, Any]
Vector3 = Tuple[float, float, float]

EXPECTED_FRAMES = {
    "map": "map",
    "uav_base": "uav/base_link",
    "arm_base": "uav/arm_base",
    "ee": "uav/ee_link",
    "camera": "uav/camera_link",
}
EXPECTED_TF_CHAIN = (
    ("map", "uav/base_link"),
    ("uav/base_link", "uav/arm_base"),
    ("uav/arm_base", "uav/ee_link"),
    ("uav/ee_link", "uav/camera_link"),
)
EXPECTED_ARM_JOINT_NAMES = (
    "arm_shoulder_pitch_joint",
    "arm_elbow_pitch_joint",
)
NED_ENU_CASES: Tuple[Tuple[Vector3, Vector3], ...] = (
    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
    ((1.0, 2.0, -3.0), (2.0, 1.0, 3.0)),
    ((-4.5, 0.25, 2.0), (0.25, -4.5, -2.0)),
)
VECTOR_FIELDS = ("joint_positions", "joint_velocities", "joint_efforts")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check stage-2 frame conversion and 2-DOF schema invariants."
    )
    parser.add_argument(
        "--output-root",
        default=str(WORKSPACE_ROOT / "logs" / "demo_06_state_agg"),
        help="Directory under which a timestamped tf_report.json is written.",
    )
    parser.add_argument(
        "--timestamp",
        default=time.strftime("%Y%m%d_%H%M%S"),
        help="Timestamp directory name for the generated report.",
    )
    args = parser.parse_args()

    report_dir = Path(args.output_root) / args.timestamp
    report_path = report_dir / "tf_report.json"

    checks = [
        _check_frame_constants(),
        _check_ned_enu_conversions(),
        _check_arm_schema_constants(),
        _check_message_files(),
        _check_source_alignment(),
    ]
    result = "PASS" if all(check["passed"] for check in checks) else "FAIL"
    report: Dict[str, Any] = {
        "schema_version": "stage2_frame_schema_regression_v1",
        "generated_at": args.timestamp,
        "result": result,
        "workspace": str(WORKSPACE_ROOT),
        "report_path": str(report_path),
        "enforced": {
            "frames": EXPECTED_FRAMES,
            "tf_chain": EXPECTED_TF_CHAIN,
            "platform_ned_frame": PLATFORM_NED_FRAME,
            "ned_to_enu_formula": "enu_x=ned_y, enu_y=ned_x, enu_z=-ned_z",
            "arm_joint_names": EXPECTED_ARM_JOINT_NAMES,
            "arm_dof": 2,
            "arm_vector_fields": VECTOR_FIELDS,
        },
        "checks": checks,
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"CHECK={result} report={report_path}")
    if result != "PASS":
        for check in checks:
            if not check["passed"]:
                print(f"FAIL {check['name']}: {check['reason']}")
        return 1
    return 0


def _check_frame_constants() -> Check:
    details = {
        "actual_frames": dict(CANONICAL_FRAMES),
        "actual_tf_chain": list(CANONICAL_TF_CHAIN),
        "arm_base_xyz": DEFAULT_ARM_BASE_XYZ,
        "camera_xyz": DEFAULT_CAMERA_XYZ,
    }
    if dict(CANONICAL_FRAMES) != EXPECTED_FRAMES:
        return _fail("canonical_frame_constants", "canonical frame names changed", details)
    if tuple(CANONICAL_TF_CHAIN) != EXPECTED_TF_CHAIN:
        return _fail("canonical_frame_constants", "canonical TF chain changed", details)
    if len(DEFAULT_ARM_BASE_XYZ) != 3 or len(DEFAULT_CAMERA_XYZ) != 3:
        return _fail("canonical_frame_constants", "fixed transforms must be xyz triplets", details)
    return _pass("canonical_frame_constants", details)


def _check_ned_enu_conversions() -> Check:
    case_reports = []
    for ned, expected_enu in NED_ENU_CASES:
        actual_enu = ned_to_enu_xyz(ned)
        round_trip_ned = enu_to_ned_xyz(actual_enu)
        case_reports.append(
            {
                "ned": ned,
                "expected_enu": expected_enu,
                "actual_enu": actual_enu,
                "round_trip_ned": round_trip_ned,
            }
        )
        if not _vector_close(actual_enu, expected_enu):
            return _fail("ned_enu_conversion", "NED to ENU case failed", case_reports)
        if not _vector_close(round_trip_ned, ned):
            return _fail("ned_enu_conversion", "ENU to NED round trip failed", case_reports)
    return _pass("ned_enu_conversion", case_reports)


def _check_arm_schema_constants() -> Check:
    details = {
        "joint_names": CANONICAL_ARM_JOINT_NAMES,
        "arm_dof": CANONICAL_ARM_DOF,
        "min_positions": DEFAULT_ARM_MIN_POSITIONS,
        "max_positions": DEFAULT_ARM_MAX_POSITIONS,
        "max_velocities": DEFAULT_ARM_MAX_VELOCITIES,
    }
    if tuple(CANONICAL_ARM_JOINT_NAMES) != EXPECTED_ARM_JOINT_NAMES:
        return _fail("arm_schema_constants", "canonical joint names changed", details)
    if CANONICAL_ARM_DOF != 2:
        return _fail("arm_schema_constants", "canonical arm DOF must remain 2", details)
    for name, values in (
        ("min_positions", DEFAULT_ARM_MIN_POSITIONS),
        ("max_positions", DEFAULT_ARM_MAX_POSITIONS),
        ("max_velocities", DEFAULT_ARM_MAX_VELOCITIES),
    ):
        if len(values) != CANONICAL_ARM_DOF:
            return _fail("arm_schema_constants", f"{name} length must be 2", details)
        if not all(math.isfinite(float(value)) for value in values):
            return _fail("arm_schema_constants", f"{name} contains non-finite values", details)
    for lower, upper in zip(DEFAULT_ARM_MIN_POSITIONS, DEFAULT_ARM_MAX_POSITIONS):
        if lower > upper:
            return _fail("arm_schema_constants", "joint min exceeds max", details)
    if any(value <= 0.0 for value in DEFAULT_ARM_MAX_VELOCITIES):
        return _fail("arm_schema_constants", "max velocities must be positive", details)
    return _pass("arm_schema_constants", details)


def _check_message_files() -> Check:
    msg_dir = WORKSPACE_ROOT / "src" / "aerial_manip_msgs" / "msg"
    arm_command = _read_msg_fields(msg_dir / "ArmCommand.msg")
    arm_state = _read_msg_fields(msg_dir / "ArmState.msg")
    platform = _read_msg_fields(msg_dir / "PlatformState.msg")
    observation = _read_msg_fields(msg_dir / "SystemObservation.msg")
    details = {
        "ArmCommand": arm_command,
        "ArmState": arm_state,
        "PlatformState": platform,
        "SystemObservation": observation,
        "expected_arm_vector_length": CANONICAL_ARM_DOF,
    }

    for msg_name, fields in (("ArmCommand", arm_command), ("ArmState", arm_state)):
        if fields.get("joint_names") != "string[]":
            return _fail("message_files", f"{msg_name}.joint_names must be string[]", details)
        for field_name in VECTOR_FIELDS:
            if fields.get(field_name) != "float64[]":
                return _fail("message_files", f"{msg_name}.{field_name} must be float64[]", details)

    expected_platform_fields = {
        "position_ned": "geometry_msgs/Point",
        "velocity_ned": "geometry_msgs/Vector3",
    }
    for field_name, field_type in expected_platform_fields.items():
        if platform.get(field_name) != field_type:
            return _fail("message_files", f"PlatformState.{field_name} changed", details)

    if observation.get("platform") != "aerial_manip_msgs/PlatformState":
        return _fail("message_files", "SystemObservation.platform changed", details)
    if observation.get("arm") != "aerial_manip_msgs/ArmState":
        return _fail("message_files", "SystemObservation.arm changed", details)
    return _pass("message_files", details)


def _check_source_alignment() -> Check:
    source_expectations = {
        "src/aerial_manip_control/aerial_manip_control/state_aggregator.py": [
            "CANONICAL_FRAMES",
            "PLATFORM_NED_FRAME",
            "ned_to_enu_xyz",
        ],
        "src/aerial_manip_control/aerial_manip_control/arm_control_bridge.py": [
            "CANONICAL_ARM_JOINT_NAMES",
            "CANONICAL_FRAMES",
        ],
        "src/aerial_manip_control/aerial_manip_control/approach_coordinator.py": [
            "CANONICAL_ARM_JOINT_NAMES",
            "CANONICAL_FRAMES",
        ],
        "src/aerial_manip_eval/aerial_manip_eval/synthetic_arm_controller.py": [
            "CANONICAL_ARM_JOINT_NAMES",
            "CANONICAL_FRAMES",
        ],
        "src/aerial_manip_eval/aerial_manip_eval/demo10_dry_run.py": [
            "CANONICAL_ARM_JOINT_NAMES",
        ],
    }
    details: Dict[str, Any] = {}
    for relative_path, required_tokens in source_expectations.items():
        text = (WORKSPACE_ROOT / relative_path).read_text(encoding="utf-8")
        missing = [token for token in required_tokens if token not in text]
        details[relative_path] = {
            "required_tokens": required_tokens,
            "missing_tokens": missing,
        }
        if missing:
            return _fail("source_alignment", f"{relative_path} is not using canonical constants", details)
    return _pass("source_alignment", details)


def _read_msg_fields(path: Path) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" in line:
            continue
        parts = line.split()
        if len(parts) == 2:
            field_type, field_name = parts
            fields[field_name] = field_type
    return fields


def _vector_close(left: Sequence[float], right: Sequence[float]) -> bool:
    if len(left) != len(right):
        return False
    return all(abs(float(a) - float(b)) <= 1.0e-9 for a, b in zip(left, right))


def _pass(name: str, details: Any) -> Check:
    return {"name": name, "passed": True, "reason": "ok", "details": details}


def _fail(name: str, reason: str, details: Any) -> Check:
    return {"name": name, "passed": False, "reason": reason, "details": details}


if __name__ == "__main__":
    sys.exit(main())
