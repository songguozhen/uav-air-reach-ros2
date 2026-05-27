from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "publish_placeholder",
                default_value="false",
                description=(
                    "Publish the documented static target pose when camera "
                    "images or detector runtime are unavailable."
                ),
            ),
            Node(
                package="aerial_manip_vision",
                executable="tag_target_pose_node",
                name="tag_target_pose_node",
                output="screen",
                parameters=[
                    {"publish_placeholder": LaunchConfiguration("publish_placeholder")}
                ],
            ),
        ]
    )
