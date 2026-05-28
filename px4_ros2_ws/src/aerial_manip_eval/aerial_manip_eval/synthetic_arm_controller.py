import math
import time
from typing import List, Optional

from aerial_manip_control.stage2_schema import (
    CANONICAL_ARM_JOINT_NAMES,
    CANONICAL_FRAMES,
    DEFAULT_ARM_LINK_LENGTHS,
)
from aerial_manip_msgs.msg import ArmCommand, ArmState
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


DEFAULT_ARM_JOINT_NAMES = list(CANONICAL_ARM_JOINT_NAMES)


class SyntheticArmController(Node):
    """Small first-order arm plant for Demo 10 regression runs."""

    def __init__(self) -> None:
        super().__init__("synthetic_arm_controller")
        self.declare_parameter("joint_names", DEFAULT_ARM_JOINT_NAMES)
        self.declare_parameter("initial_joint_positions", [0.0, 0.0])
        self.declare_parameter("publish_period", 0.05)
        self.declare_parameter("max_step_per_tick", 0.03)
        self.declare_parameter("link_lengths", list(DEFAULT_ARM_LINK_LENGTHS))

        self.joint_names = self._string_list_parameter("joint_names")
        self.positions = self._float_list_parameter("initial_joint_positions")
        self.target = list(self.positions)
        self.publish_period = float(self.get_parameter("publish_period").value)
        self.max_step_per_tick = float(self.get_parameter("max_step_per_tick").value)
        self.link_lengths = self._float_list_parameter("link_lengths")
        self.last_time: Optional[float] = None

        if len(self.positions) != len(self.joint_names):
            raise ValueError("initial_joint_positions length must match joint_names")
        if len(self.link_lengths) < 2:
            raise ValueError("link_lengths must contain at least two values")
        if self.publish_period <= 0.0 or self.max_step_per_tick <= 0.0:
            raise ValueError("publish_period and max_step_per_tick must be positive")

        self.state_pub = self.create_publisher(ArmState, "/arm/controller_state", 10)
        self.create_subscription(
            ArmCommand, "/arm/controller_command", self.command_callback, 10
        )
        self.timer = self.create_timer(self.publish_period, self.timer_callback)
        self.get_logger().info("Synthetic arm controller publishing /arm/controller_state")

    def command_callback(self, msg: ArmCommand) -> None:
        if msg.joint_positions and len(msg.joint_positions) == len(self.joint_names):
            self.target = [float(value) for value in msg.joint_positions]

    def timer_callback(self) -> None:
        now = time.monotonic()
        if self.last_time is None:
            self.last_time = now
        self.positions = [
            current + max(-self.max_step_per_tick, min(self.max_step_per_tick, target - current))
            for current, target in zip(self.positions, self.target)
        ]

        msg = ArmState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = CANONICAL_FRAMES["arm_base"]
        msg.joint_names = list(self.joint_names)
        msg.joint_positions = list(self.positions)
        msg.joint_velocities = [0.0] * len(self.positions)
        msg.joint_efforts = [0.0] * len(self.positions)
        msg.end_effector_pose.header = msg.header
        msg.end_effector_pose.pose.orientation.w = 1.0
        x, y, z = self._forward_kinematics(self.positions)
        msg.end_effector_pose.pose.position.x = x
        msg.end_effector_pose.pose.position.y = y
        msg.end_effector_pose.pose.position.z = z
        msg.contact_detected = False
        msg.state = "synthetic_tracking"
        self.state_pub.publish(msg)

    def _forward_kinematics(self, joints: List[float]):
        shoulder = joints[0] if len(joints) > 0 else 0.0
        elbow = joints[1] if len(joints) > 1 else 0.0
        reach = (
            self.link_lengths[0] * math.cos(shoulder)
            + self.link_lengths[1] * math.cos(shoulder + elbow)
        )
        height = (
            self.link_lengths[0] * math.sin(shoulder)
            + self.link_lengths[1] * math.sin(shoulder + elbow)
        )
        return (
            0.10 + reach,
            0.0,
            -0.08 - height,
        )

    def _string_list_parameter(self, name: str) -> List[str]:
        value = self.get_parameter(name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be a list")
        return [str(item) for item in value]

    def _float_list_parameter(self, name: str) -> List[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be a list")
        return [float(item) for item in value]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SyntheticArmController()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
