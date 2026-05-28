import math
import time
from typing import Dict, List, Optional, Sequence

from aerial_manip_control.stage2_schema import (
    CANONICAL_ARM_JOINT_NAMES,
    CANONICAL_FRAMES,
    DEFAULT_ARM_MAX_POSITIONS,
    DEFAULT_ARM_MAX_VELOCITIES,
    DEFAULT_ARM_MIN_POSITIONS,
)
from aerial_manip_msgs.msg import ArmCommand, ArmState
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String


JointVector = List[float]
DEFAULT_ARM_JOINT_NAMES = list(CANONICAL_ARM_JOINT_NAMES)


class ArmControlBridge(Node):
    """Validated high-level /arm target bridge for arm joint control."""

    def __init__(self) -> None:
        super().__init__("arm_control_bridge")

        self.declare_parameter("joint_names", DEFAULT_ARM_JOINT_NAMES)
        self.declare_parameter("initial_joint_positions", [0.0, 0.0])
        self.declare_parameter("stow_joint_positions", [0.0, 0.0])
        self.declare_parameter("min_joint_positions", list(DEFAULT_ARM_MIN_POSITIONS))
        self.declare_parameter("max_joint_positions", list(DEFAULT_ARM_MAX_POSITIONS))
        self.declare_parameter("max_joint_velocities", list(DEFAULT_ARM_MAX_VELOCITIES))
        self.declare_parameter("target_jump_limit", 0.35)
        self.declare_parameter("command_timeout", 1.0)
        self.declare_parameter("reach_tolerance", 0.03)
        self.declare_parameter("reach_hold_time", 0.5)
        self.declare_parameter("command_period", 0.05)

        self.joint_names = self._string_list_parameter("joint_names")
        self.initial_joint_positions = self._float_list_parameter(
            "initial_joint_positions"
        )
        self.stow_joint_positions = self._float_list_parameter("stow_joint_positions")
        self.min_joint_positions = self._float_list_parameter("min_joint_positions")
        self.max_joint_positions = self._float_list_parameter("max_joint_positions")
        self.max_joint_velocities = self._float_list_parameter("max_joint_velocities")
        self.target_jump_limit = float(self.get_parameter("target_jump_limit").value)
        self.command_timeout = float(self.get_parameter("command_timeout").value)
        self.reach_tolerance = float(self.get_parameter("reach_tolerance").value)
        self.reach_hold_time = float(self.get_parameter("reach_hold_time").value)
        self.command_period = float(self.get_parameter("command_period").value)

        self._validate_config()

        self.safe_target = list(self.initial_joint_positions)
        error = self._validate_positions(self.safe_target, check_jump=False)
        if error is not None:
            raise ValueError(f"Initial arm target is unsafe: {error}")

        stow_error = self._validate_positions(
            self.stow_joint_positions, check_jump=False
        )
        if stow_error is not None:
            raise ValueError(f"Stow arm target is unsafe: {stow_error}")

        self.current_positions: Optional[JointVector] = None
        self.current_velocities: JointVector = [0.0] * len(self.joint_names)
        self.current_efforts: JointVector = [0.0] * len(self.joint_names)
        self.last_safe_target_time = time.monotonic()
        self.last_timeout_warning_time = 0.0
        self.reach_start_time: Optional[float] = None
        self.reached_target = False
        self.control_state = "HOLDING"
        self.active_command_mode = ArmCommand.MODE_HOLD
        self.invalid_target_pending = False

        self.command_pub = self.create_publisher(
            ArmCommand, "/arm/controller_command", 10
        )
        self.current_joint_state_pub = self.create_publisher(
            ArmState, "/arm/current_joint_state", 10
        )
        self.current_target_pub = self.create_publisher(
            ArmState, "/arm/current_target", 10
        )
        self.reached_target_pub = self.create_publisher(
            Bool, "/arm/reached_target", 10
        )
        self.control_state_pub = self.create_publisher(
            String, "/arm/control_state", 10
        )
        self.create_subscription(
            ArmCommand, "/arm/target_joints", self.target_callback, 10
        )
        self.create_subscription(
            ArmState, "/arm/controller_state", self.controller_state_callback, 10
        )
        self.timer = self.create_timer(self.command_period, self.timer_callback)
        self.get_logger().info(
            "Arm control bridge ready on /arm/target_joints; low-level arm "
            "commands are published only on /arm/controller_command"
        )

    def target_callback(self, msg: ArmCommand) -> None:
        command_mode = msg.command_mode or ArmCommand.MODE_JOINT_POSITION
        if command_mode == ArmCommand.MODE_HOLD:
            target = self.safe_target
        elif command_mode == ArmCommand.MODE_STOW:
            target = list(self.stow_joint_positions)
        elif command_mode == ArmCommand.MODE_JOINT_POSITION:
            target = self._ordered_positions(msg)
        else:
            self._reject_target(f"unsupported command_mode '{command_mode}'")
            return

        if target is None:
            self._reject_target("joint_names must match configured arm joints")
            return

        error = self._validate_positions(target, check_jump=True)
        if error is not None:
            self._reject_target(error)
            return

        velocity_error = self._validate_command_velocities(msg)
        if velocity_error is not None:
            self._reject_target(velocity_error)
            return

        self.safe_target = list(target)
        self.active_command_mode = command_mode
        self.last_safe_target_time = time.monotonic()
        self.last_timeout_warning_time = 0.0
        self.reach_start_time = None
        self.reached_target = False
        self.invalid_target_pending = False
        self.control_state = "TRACKING"
        self.get_logger().info(
            "Accepted /arm/target_joints "
            + ", ".join(
                f"{name}={position:.3f}"
                for name, position in zip(self.joint_names, self.safe_target)
            )
        )

    def controller_state_callback(self, msg: ArmState) -> None:
        positions = self._ordered_state_values(msg.joint_names, msg.joint_positions)
        if positions is None:
            self.get_logger().warn(
                "Ignored /arm/controller_state with mismatched joint_names"
            )
            return

        velocities = self._ordered_state_values(msg.joint_names, msg.joint_velocities)
        efforts = self._ordered_state_values(msg.joint_names, msg.joint_efforts)
        self.current_positions = positions
        self.current_velocities = velocities or [0.0] * len(self.joint_names)
        self.current_efforts = efforts or [0.0] * len(self.joint_names)

        state_msg = ArmState()
        state_msg.header.stamp = self.get_clock().now().to_msg()
        state_msg.header.frame_id = msg.header.frame_id or CANONICAL_FRAMES["arm_base"]
        state_msg.joint_names = list(self.joint_names)
        state_msg.joint_positions = list(self.current_positions)
        state_msg.joint_velocities = list(self.current_velocities)
        state_msg.joint_efforts = list(self.current_efforts)
        state_msg.end_effector_pose = msg.end_effector_pose
        state_msg.contact_detected = msg.contact_detected
        state_msg.state = msg.state
        self.current_joint_state_pub.publish(state_msg)

    def timer_callback(self) -> None:
        self._publish_low_level_command()
        self._update_reached_target()
        self._update_control_state()
        self._publish_bridge_state()

    def _publish_low_level_command(self) -> None:
        command = ArmCommand()
        command.header.stamp = self.get_clock().now().to_msg()
        command.header.frame_id = CANONICAL_FRAMES["arm_base"]
        command.command_mode = ArmCommand.MODE_JOINT_POSITION
        command.joint_names = list(self.joint_names)
        command.joint_positions = list(self.safe_target)
        command.joint_velocities = [0.0] * len(self.joint_names)
        command.joint_efforts = [0.0] * len(self.joint_names)
        self.command_pub.publish(command)

    def _validate_positions(
        self, positions: Sequence[float], check_jump: bool
    ) -> Optional[str]:
        if len(positions) != len(self.joint_names):
            return (
                f"expected {len(self.joint_names)} joint positions, got "
                f"{len(positions)}"
            )

        if not all(math.isfinite(value) for value in positions):
            return "target contains non-finite joint positions"

        for index, (name, position) in enumerate(zip(self.joint_names, positions)):
            min_position = self.min_joint_positions[index]
            max_position = self.max_joint_positions[index]
            if position < min_position or position > max_position:
                return (
                    f"{name}={position:.3f} rad is outside "
                    f"[{min_position:.3f}, {max_position:.3f}] rad"
                )

        if check_jump:
            jump = max(
                abs(position - previous)
                for position, previous in zip(positions, self.safe_target)
            )
            if jump > self.target_jump_limit:
                return (
                    f"target jump {jump:.3f} rad exceeds target_jump_limit "
                    f"{self.target_jump_limit:.3f} rad"
                )

        return None

    def _validate_command_velocities(self, msg: ArmCommand) -> Optional[str]:
        if not msg.joint_velocities:
            return None

        velocities = self._ordered_state_values(msg.joint_names, msg.joint_velocities)
        if velocities is None:
            return "joint_velocities must match configured arm joints"

        for name, velocity, limit in zip(
            self.joint_names, velocities, self.max_joint_velocities
        ):
            if not math.isfinite(velocity):
                return "target contains non-finite joint velocities"
            if abs(velocity) > limit:
                return (
                    f"{name} velocity {velocity:.3f} rad/s exceeds "
                    f"max_joint_velocity {limit:.3f} rad/s"
                )

        return None

    def _reject_target(self, reason: str) -> None:
        self.get_logger().warn(f"Rejected /arm/target_joints: {reason}")
        self.control_state = "INVALID_TARGET"
        self.invalid_target_pending = True
        self._publish_bridge_state()

    def _target_timed_out(self, now: float) -> bool:
        if self.command_timeout <= 0.0:
            return False

        return now - self.last_safe_target_time > self.command_timeout

    def _warn_if_target_timed_out(self, now: float) -> None:
        if not self._target_timed_out(now):
            return
        if now - self.last_timeout_warning_time < self.command_timeout:
            return

        self.get_logger().warn("Arm command timeout; holding last safe target")
        self.last_timeout_warning_time = now

    def _update_reached_target(self) -> None:
        if self.current_positions is None:
            self.reach_start_time = None
            self.reached_target = False
            return

        max_error = max(
            abs(current - target)
            for current, target in zip(self.current_positions, self.safe_target)
        )
        if max_error > self.reach_tolerance:
            self.reach_start_time = None
            self.reached_target = False
            return

        now = time.monotonic()
        if self.reach_start_time is None:
            self.reach_start_time = now
        self.reached_target = now - self.reach_start_time >= self.reach_hold_time

    def _update_control_state(self) -> None:
        if self.invalid_target_pending:
            self.control_state = "INVALID_TARGET"
            self.invalid_target_pending = False
            return

        now = time.monotonic()
        if self._target_timed_out(now):
            self._warn_if_target_timed_out(now)
            self.control_state = "HOLDING"
            return

        if self.reached_target:
            self.control_state = "REACHED"
            return

        self.control_state = "TRACKING"

    def _publish_bridge_state(self) -> None:
        target_msg = ArmState()
        target_msg.header.stamp = self.get_clock().now().to_msg()
        target_msg.header.frame_id = CANONICAL_FRAMES["arm_base"]
        target_msg.joint_names = list(self.joint_names)
        target_msg.joint_positions = list(self.safe_target)
        target_msg.joint_velocities = [0.0] * len(self.joint_names)
        target_msg.joint_efforts = [0.0] * len(self.joint_names)
        target_msg.state = self.active_command_mode
        self.current_target_pub.publish(target_msg)

        reached_msg = Bool()
        reached_msg.data = self.reached_target
        self.reached_target_pub.publish(reached_msg)

        state_msg = String()
        state_msg.data = self.control_state
        self.control_state_pub.publish(state_msg)

    def _ordered_positions(self, msg: ArmCommand) -> Optional[JointVector]:
        return self._ordered_state_values(msg.joint_names, msg.joint_positions)

    def _ordered_state_values(
        self, joint_names: Sequence[str], values: Sequence[float]
    ) -> Optional[JointVector]:
        if not values:
            return None
        if len(values) != len(self.joint_names):
            return None
        if not joint_names:
            return list(values)
        if set(joint_names) != set(self.joint_names):
            return None

        value_by_joint: Dict[str, float] = dict(zip(joint_names, values))
        return [float(value_by_joint[name]) for name in self.joint_names]

    def _validate_config(self) -> None:
        if not self.joint_names:
            raise ValueError("joint_names must not be empty")
        if len(set(self.joint_names)) != len(self.joint_names):
            raise ValueError("joint_names must be unique")

        expected_length = len(self.joint_names)
        for parameter_name in (
            "initial_joint_positions",
            "stow_joint_positions",
            "min_joint_positions",
            "max_joint_positions",
            "max_joint_velocities",
        ):
            values = getattr(self, parameter_name)
            if len(values) != expected_length:
                raise ValueError(
                    f"{parameter_name} length {len(values)} does not match "
                    f"joint_names length {expected_length}"
                )
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"{parameter_name} contains non-finite values")

        for name, min_position, max_position in zip(
            self.joint_names, self.min_joint_positions, self.max_joint_positions
        ):
            if min_position > max_position:
                raise ValueError(f"{name} min_joint_position exceeds max")

        if any(limit <= 0.0 for limit in self.max_joint_velocities):
            raise ValueError("max_joint_velocities must be positive")
        if self.target_jump_limit <= 0.0:
            raise ValueError("target_jump_limit must be positive")
        if self.reach_tolerance <= 0.0:
            raise ValueError("reach_tolerance must be positive")
        if self.reach_hold_time < 0.0:
            raise ValueError("reach_hold_time must be non-negative")
        if self.command_period <= 0.0:
            raise ValueError("command_period must be positive")

    def _string_list_parameter(self, parameter_name: str) -> List[str]:
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{parameter_name} must be a list")

        return [str(item) for item in value]

    def _float_list_parameter(self, parameter_name: str) -> JointVector:
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{parameter_name} must be a list")

        return [float(item) for item in value]


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ArmControlBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
