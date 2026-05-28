from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import (
    PackageNotFoundError,
    get_package_share_directory,
)


REQUIRED_PACKAGES = (
    "gz_ros2_control",
    "controller_manager",
    "joint_state_broadcaster",
    "forward_command_controller",
)


def _package_missing(package_name):
    try:
        get_package_share_directory(package_name)
    except PackageNotFoundError:
        return True
    return False


def _launch_setup(context, *args, **kwargs):
    missing = [package for package in REQUIRED_PACKAGES if _package_missing(package)]
    if missing:
        return [
            LogInfo(
                msg=(
                    "WARN: arm ros2_control launch skipped; missing ROS 2 "
                    f"packages: {', '.join(missing)}. Install/provide these "
                    "packages, rebuild, source the workspace, then rerun this "
                    "launch file."
                )
            )
        ]

    controller_manager = LaunchConfiguration("controller_manager").perform(context)
    controller_manager_timeout = LaunchConfiguration(
        "controller_manager_timeout"
    ).perform(context)

    spawner_common_args = [
        "--controller-manager",
        controller_manager,
        "--controller-manager-timeout",
        controller_manager_timeout,
    ]

    return [
        LogInfo(
            msg=(
                "Starting arm ros2_control spawners for a gz_ros2_control "
                f"manager at {controller_manager}."
            )
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["joint_state_broadcaster", *spawner_common_args],
            output="screen",
        ),
        Node(
            package="controller_manager",
            executable="spawner",
            arguments=["arm_position_controller", *spawner_common_args],
            output="screen",
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "controller_manager",
                default_value="/controller_manager",
                description=(
                    "Controller manager provided by the gz_ros2_control SDF plugin."
                ),
            ),
            DeclareLaunchArgument(
                "controller_manager_timeout",
                default_value="10",
                description="Seconds for controller spawners to wait for the manager.",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
