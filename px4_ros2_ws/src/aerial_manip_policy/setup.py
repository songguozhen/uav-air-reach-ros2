from setuptools import find_packages, setup

package_name = "aerial_manip_policy"

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
    description="Python policy integration package for stage-2 aerial manipulation.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "policy_bridge = aerial_manip_policy.policy_bridge:main",
            "train_lerobot_baseline = aerial_manip_policy.train_lerobot_baseline:main",
        ]
    },
)
