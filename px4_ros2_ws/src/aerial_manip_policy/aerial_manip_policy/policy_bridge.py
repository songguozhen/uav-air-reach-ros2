import json
import math
import shlex
import time
from typing import Any, Dict, List, Optional

from aerial_manip_msgs.msg import ArmCommand, SystemObservation, TaskStatus
from geometry_msgs.msg import Point
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from aerial_manip_policy.action_chunks import (
    ActionChunk,
    HighLevelAction,
    StaticChunkPolicy,
    SubprocessJsonPolicy,
)


class PolicyBridge(Node):
    """Executes learned high-level action chunks through safe project topics."""

    def __init__(self) -> None:
        super().__init__("policy_bridge")

        self.declare_parameter("control_period", 0.1)
        self.declare_parameter("observation_timeout", 1.0)
        self.declare_parameter("inference_timeout", 0.25)
        self.declare_parameter("chunk_timeout", 1.0)
        self.declare_parameter("max_horizontal_range", 8.0)
        self.declare_parameter("min_altitude", 0.4)
        self.declare_parameter("max_altitude", 5.0)
        self.declare_parameter("max_uav_target_step", 0.5)
        self.declare_parameter("joint_names", ["joint1", "joint2", "joint3"])
        self.declare_parameter("fallback_arm_mode", ArmCommand.MODE_HOLD)
        self.declare_parameter("policy_json", "")
        self.declare_parameter("policy_command", "")

        self.control_period = float(self.get_parameter("control_period").value)
        self.observation_timeout = float(
            self.get_parameter("observation_timeout").value
        )
        self.inference_timeout = float(self.get_parameter("inference_timeout").value)
        self.chunk_timeout = float(self.get_parameter("chunk_timeout").value)
        self.max_horizontal_range = float(
            self.get_parameter("max_horizontal_range").value
        )
        self.min_altitude = float(self.get_parameter("min_altitude").value)
        self.max_altitude = float(self.get_parameter("max_altitude").value)
        self.max_uav_target_step = float(
            self.get_parameter("max_uav_target_step").value
        )
        self.joint_names = [str(v) for v in self.get_parameter("joint_names").value]
        self.fallback_arm_mode = str(self.get_parameter("fallback_arm_mode").value)
        self.policy_json = str(self.get_parameter("policy_json").value)
        self.policy_command = str(self.get_parameter("policy_command").value)

        self.latest_observation: Optional[SystemObservation] = None
        self.last_observation_time = 0.0
        self.current_chunk: List[HighLevelAction] = []
        self.chunk_received_time = 0.0
        self.last_uav_target: Optional[List[float]] = None
        self.last_status = ""

        self.policy = self._create_policy()

        self.uav_target_pub = self.create_publisher(Point, "/uav/target_position", 10)
        self.arm_target_pub = self.create_publisher(ArmCommand, "/arm/target_joints", 10)
        self.status_pub = self.create_publisher(TaskStatus, "/policy/status", 10)
        self.create_subscription(
            SystemObservation,
            "/system/observation",
            self.observation_callback,
            10,
        )
        self.timer = self.create_timer(self.control_period, self.control_loop)
        self.get_logger().info(
            "Policy bridge ready; outputs are /uav/target_position, "
            "/arm/target_joints, and /policy/status"
        )

    def observation_callback(self, msg: SystemObservation) -> None:
        self.latest_observation = msg
        self.last_observation_time = time.monotonic()

    def control_loop(self) -> None:
        now = time.monotonic()
        observation = self._fresh_observation(now)
        if observation is None:
            self._publish_fallback("waiting for fresh /system/observation")
            return

        if not self.current_chunk or now - self.chunk_received_time > self.chunk_timeout:
            try:
                chunk = self.policy.predict(
                    self._observation_to_dict(observation), self.inference_timeout
                )
            except Exception as exc:
                self.current_chunk = []
                self._publish_fallback(f"inference unavailable: {exc}")
                return
            self._accept_chunk(chunk, now)

        if not self.current_chunk:
            self._publish_fallback("policy produced an empty action chunk")
            return

        action = self.current_chunk.pop(0)
        try:
            self._publish_action(action, observation)
        except ValueError as exc:
            self.current_chunk = []
            self._publish_fallback(f"rejected unsafe action: {exc}")

    def _create_policy(self):
        if self.policy_command.strip():
            return SubprocessJsonPolicy(shlex.split(self.policy_command))
        if self.policy_json.strip():
            return StaticChunkPolicy(self.policy_json)
        return HoldPolicy()

    def _accept_chunk(self, chunk: ActionChunk, now: float) -> None:
        self.current_chunk = list(chunk.actions)
        self.chunk_received_time = now
        self._publish_status(
            TaskStatus.STATUS_RUNNING,
            f"accepted {len(self.current_chunk)} action(s) from {chunk.source}",
            0.0,
        )

    def _publish_action(
        self, action: HighLevelAction, observation: SystemObservation
    ) -> None:
        if action.uav_target_ned is not None:
            target = self._limited_uav_target(action.uav_target_ned, observation)
            msg = Point()
            msg.x, msg.y, msg.z = target
            self.uav_target_pub.publish(msg)
            self.last_uav_target = target

        arm_msg = ArmCommand()
        arm_msg.header.stamp = self.get_clock().now().to_msg()
        arm_msg.command_mode = action.arm_mode or ArmCommand.MODE_HOLD
        arm_msg.joint_names = (
            action.arm_joint_names if action.arm_joint_names else self.joint_names
        )
        arm_msg.joint_positions = action.arm_joint_positions
        self.arm_target_pub.publish(arm_msg)
        self._publish_status(TaskStatus.STATUS_RUNNING, "published policy action", 0.5)

    def _publish_fallback(self, reason: str) -> None:
        observation = self.latest_observation
        if observation is not None:
            hold = Point()
            if self.last_uav_target is not None:
                hold.x, hold.y, hold.z = self.last_uav_target
            else:
                position = observation.platform.position_ned
                hold.x, hold.y, hold.z = position.x, position.y, position.z
            self.uav_target_pub.publish(hold)

        arm_msg = ArmCommand()
        arm_msg.header.stamp = self.get_clock().now().to_msg()
        arm_msg.command_mode = self.fallback_arm_mode
        arm_msg.joint_names = self.joint_names
        self.arm_target_pub.publish(arm_msg)
        self._publish_status(TaskStatus.STATUS_FAILED, reason, 0.0)

    def _fresh_observation(self, now: float) -> Optional[SystemObservation]:
        if self.latest_observation is None:
            return None
        if now - self.last_observation_time > self.observation_timeout:
            return None
        return self.latest_observation

    def _limited_uav_target(
        self, requested: List[float], observation: SystemObservation
    ) -> List[float]:
        x, y, z = [float(value) for value in requested]
        horizontal = math.hypot(x, y)
        if horizontal > self.max_horizontal_range:
            raise ValueError(
                f"horizontal range {horizontal:.2f} exceeds {self.max_horizontal_range:.2f}"
            )
        altitude = -z
        if altitude < self.min_altitude or altitude > self.max_altitude:
            raise ValueError(
                f"altitude {altitude:.2f} outside "
                f"[{self.min_altitude:.2f}, {self.max_altitude:.2f}]"
            )

        current = observation.platform.position_ned
        if self.last_uav_target is None:
            base = [current.x, current.y, current.z]
        else:
            base = self.last_uav_target
        dx, dy, dz = x - base[0], y - base[1], z - base[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        if distance <= self.max_uav_target_step or distance <= 1.0e-9:
            return [x, y, z]
        scale = self.max_uav_target_step / distance
        return [base[0] + dx * scale, base[1] + dy * scale, base[2] + dz * scale]

    def _observation_to_dict(self, msg: SystemObservation) -> Dict[str, Any]:
        platform = msg.platform
        arm = msg.arm
        return {
            "timestamp_sec": time.time(),
            "phase": msg.phase,
            "target_visible": bool(msg.target_visible),
            "platform": {
                "position_ned": [
                    platform.position_ned.x,
                    platform.position_ned.y,
                    platform.position_ned.z,
                ],
                "velocity_ned": [
                    platform.velocity_ned.x,
                    platform.velocity_ned.y,
                    platform.velocity_ned.z,
                ],
                "yaw_rad": platform.yaw_rad,
                "armed": bool(platform.armed),
                "nav_state": platform.nav_state,
            },
            "arm": {
                "joint_names": list(arm.joint_names),
                "joint_positions": list(arm.joint_positions),
                "state": arm.state,
                "contact_detected": bool(arm.contact_detected),
            },
            "target_pose": {
                "position": [
                    msg.target_pose.pose.position.x,
                    msg.target_pose.pose.position.y,
                    msg.target_pose.pose.position.z,
                ]
            },
        }

    def _publish_status(self, status: int, message: str, progress: float) -> None:
        if message == self.last_status:
            return
        self.last_status = message
        msg = TaskStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.task_id = "policy_bridge"
        msg.status = status
        msg.message = message
        msg.progress = float(progress)
        self.status_pub.publish(msg)


class HoldPolicy:
    def predict(self, observation: Dict[str, Any], _timeout_sec: float) -> ActionChunk:
        position = observation["platform"]["position_ned"]
        return ActionChunk(
            actions=[
                HighLevelAction(
                    dt=0.2,
                    uav_target_ned=[
                        float(position[0]),
                        float(position[1]),
                        float(position[2]),
                    ],
                    arm_mode=ArmCommand.MODE_HOLD,
                )
            ],
            source="hold_policy",
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PolicyBridge()
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
