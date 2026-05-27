from setuptools import find_packages, setup

package_name = "aerial_manip_eval"

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
    description="Python evaluation utilities for stage-2 aerial manipulation.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "air_reach_demo = aerial_manip_eval.air_reach_demo:main",
            "demo10_dry_run = aerial_manip_eval.demo10_dry_run:main",
            "episode_recorder = aerial_manip_eval.episode_recorder:main",
            "synthetic_arm_controller = aerial_manip_eval.synthetic_arm_controller:main",
        ]
    },
)
