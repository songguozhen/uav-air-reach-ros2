from setuptools import find_packages, setup

package_name = "px4_offboard_hover"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="clcwork",
    maintainer_email="clcwork@example.com",
    description="Minimal PX4 ROS 2 offboard takeoff and hover example.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "hover = px4_offboard_hover.hover:main",
            "verify_hover = px4_offboard_hover.verify_hover:main",
            "demo02_waypoint_flight = px4_offboard_hover.waypoint_flight:main",
            "demo03_circle_trajectory = px4_offboard_hover.circle_trajectory:main",
            "demo04_external_setpoint = px4_offboard_hover.external_setpoint:main",
            "uav_control_bridge = px4_offboard_hover.uav_control_bridge:main",
            "trajectory_recorder = px4_offboard_hover.trajectory_recorder:main",
        ],
    },
)
