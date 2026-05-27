from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_config = PathJoinSubstitution(
        [
            FindPackageShare("aerial_manip_gazebo"),
            "config",
            "front_camera_bridge.yaml",
        ]
    )

    bridge_config = LaunchConfiguration("bridge_config")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bridge_config",
                default_value=default_config,
                description="YAML ros_gz_bridge configuration for the front camera.",
            ),
            Node(
                package="ros_gz_bridge",
                executable="parameter_bridge",
                name="front_camera_bridge",
                output="screen",
                parameters=[{"config_file": bridge_config}],
            ),
        ]
    )
