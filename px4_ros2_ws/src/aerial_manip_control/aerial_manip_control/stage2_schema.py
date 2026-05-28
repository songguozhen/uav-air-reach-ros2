"""Canonical stage-2 frame, joint, and conversion definitions."""

from typing import Sequence, Tuple


Vector3 = Tuple[float, float, float]

CANONICAL_FRAMES = {
    "map": "map",
    "uav_base": "uav/base_link",
    "arm_base": "uav/arm_base",
    "ee": "uav/ee_link",
    "camera": "uav/camera_link",
}

CANONICAL_TF_CHAIN = (
    (CANONICAL_FRAMES["map"], CANONICAL_FRAMES["uav_base"]),
    (CANONICAL_FRAMES["uav_base"], CANONICAL_FRAMES["arm_base"]),
    (CANONICAL_FRAMES["arm_base"], CANONICAL_FRAMES["ee"]),
    (CANONICAL_FRAMES["ee"], CANONICAL_FRAMES["camera"]),
)

PLATFORM_NED_FRAME = "uav_local_ned"

DEFAULT_ARM_BASE_XYZ = (0.0, 0.0, -0.08)
DEFAULT_CAMERA_XYZ = (0.12, 0.0, -0.04)

CANONICAL_ARM_JOINT_NAMES = (
    "arm_shoulder_pitch_joint",
    "arm_elbow_pitch_joint",
)
CANONICAL_ARM_DOF = len(CANONICAL_ARM_JOINT_NAMES)
DEFAULT_ARM_MIN_POSITIONS = (-0.7, -1.2)
DEFAULT_ARM_MAX_POSITIONS = (0.7, 1.2)
DEFAULT_ARM_MAX_VELOCITIES = (1.5, 1.5)
DEFAULT_ARM_LINK_LENGTHS = (0.20, 0.16)


def ned_to_enu_xyz(point_ned: Sequence[float]) -> Vector3:
    """Convert PX4 local NED xyz to ROS ENU xyz."""
    if len(point_ned) != 3:
        raise ValueError("point_ned must contain exactly 3 values")
    x_ned, y_ned, z_ned = point_ned
    return float(y_ned), float(x_ned), float(-z_ned)


def enu_to_ned_xyz(point_enu: Sequence[float]) -> Vector3:
    """Convert ROS ENU xyz back to PX4 local NED xyz."""
    if len(point_enu) != 3:
        raise ValueError("point_enu must contain exactly 3 values")
    x_enu, y_enu, z_enu = point_enu
    return float(y_enu), float(x_enu), float(-z_enu)
