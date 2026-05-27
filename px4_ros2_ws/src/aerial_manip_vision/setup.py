from setuptools import find_packages, setup
from glob import glob

package_name = "aerial_manip_vision"

setup(
    name=package_name,
    version="0.0.1",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="clcwork",
    maintainer_email="clcwork@example.com",
    description="Python perception nodes for stage-2 aerial manipulation.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "tag_target_pose_node = aerial_manip_vision.tag_target_pose_node:main",
        ]
    },
)
