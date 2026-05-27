from setuptools import find_packages, setup

package_name = "aerial_manip_control"

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
    description="Python control nodes for stage-2 aerial manipulation.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "approach_coordinator = aerial_manip_control.approach_coordinator:main",
            "arm_control_bridge = aerial_manip_control.arm_control_bridge:main",
            "state_aggregator = aerial_manip_control.state_aggregator:main",
        ]
    },
)
