from typing import List, Optional

from aerial_manip_msgs.msg import ArmState, PlatformState, SafetyStatus
from aerial_manip_msgs.msg import SystemObservation
from geometry_msgs.msg import PointStamped, TransformStamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster


class StateAggregator(Node):
    """Single observation and TF boundary for stage-2 UAV-arm state."""

    def __init__(self) -> None:
        super().__init__("state_aggregator")

        self.declare_parameter("publish_period", 0.05)
        self.declare_parameter("state_timeout", 1.0)
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("uav_frame", "uav/base_link")
        self.declare_parameter("arm_base_frame", "uav/arm_base")
        self.declare_parameter("ee_frame", "uav/ee_link")
        self.declare_parameter("camera_frame", "uav/camera_link")
        self.declare_parameter("arm_base_xyz", [0.0, 0.0, -0.08])
        self.declare_parameter("camera_xyz", [0.12, 0.0, -0.04])

        self.publish_period = float(self.get_parameter("publish_period").value)
        self.state_timeout = float(self.get_parameter("state_timeout").value)
        self.map_frame = str(self.get_parameter("map_frame").value)
        self.uav_frame = str(self.get_parameter("uav_frame").value)
        self.arm_base_frame = str(self.get_parameter("arm_base_frame").value)
        self.ee_frame = str(self.get_parameter("ee_frame").value)
        self.camera_frame = str(self.get_parameter("camera_frame").value)
        self.arm_base_xyz = self._float_triplet_parameter("arm_base_xyz")
        self.camera_xyz = self._float_triplet_parameter("camera_xyz")

        if self.publish_period <= 0.0:
            raise ValueError("publish_period must be positive")
        if self.state_timeout <= 0.0:
            raise ValueError("state_timeout must be positive")

        self.latest_uav_position: Optional[PointStamped] = None
        self.latest_uav_state = "UNKNOWN"
        self.latest_arm_state: Optional[ArmState] = None
        self.latest_arm_control_state = "UNKNOWN"
        self.last_uav_time_ns: Optional[int] = None
        self.last_arm_time_ns: Optional[int] = None

        self.observation_pub = self.create_publisher(
            SystemObservation, "/system/observation", 10
        )
        self.safety_pub = self.create_publisher(
            SafetyStatus, "/system/safety_status", 10
        )
        self.tf_broadcaster = TransformBroadcaster(self)

        self.create_subscription(
            PointStamped, "/uav/current_position", self.uav_position_callback, 10
        )
        self.create_subscription(
            String, "/uav/control_state", self.uav_state_callback, 10
        )
        self.create_subscription(
            ArmState, "/arm/current_joint_state", self.arm_state_callback, 10
        )
        self.create_subscription(
            String, "/arm/control_state", self.arm_control_state_callback, 10
        )

        self.timer = self.create_timer(self.publish_period, self.timer_callback)
        self.get_logger().info(
            "State aggregator publishing /system/observation, "
            "/system/safety_status, and TF map -> uav/base_link -> "
            "uav/arm_base -> uav/ee_link -> uav/camera_link"
        )

    def uav_position_callback(self, msg: PointStamped) -> None:
        self.latest_uav_position = msg
        self.last_uav_time_ns = self.get_clock().now().nanoseconds

    def uav_state_callback(self, msg: String) -> None:
        self.latest_uav_state = msg.data or "UNKNOWN"

    def arm_state_callback(self, msg: ArmState) -> None:
        self.latest_arm_state = msg
        self.last_arm_time_ns = self.get_clock().now().nanoseconds

    def arm_control_state_callback(self, msg: String) -> None:
        self.latest_arm_control_state = msg.data or "UNKNOWN"

    def timer_callback(self) -> None:
        now = self.get_clock().now()
        safety = self._build_safety_status(now.nanoseconds)
        observation = self._build_observation(now.to_msg(), safety)

        self.observation_pub.publish(observation)
        self.safety_pub.publish(safety)
        self._broadcast_tf(now.to_msg(), observation)

    def _build_observation(
        self, stamp, safety: SafetyStatus
    ) -> SystemObservation:
        observation = SystemObservation()
        observation.header.stamp = stamp
        observation.header.frame_id = self.map_frame
        observation.platform = self._build_platform_state(stamp)
        observation.arm = self._build_arm_state(stamp)
        observation.target_pose.header.stamp = stamp
        observation.target_pose.header.frame_id = self.map_frame
        observation.target_pose.pose.orientation.w = 1.0
        observation.target_visible = False
        observation.phase = safety.state
        return observation

    def _build_platform_state(self, stamp) -> PlatformState:
        platform = PlatformState()
        platform.header.stamp = stamp
        platform.header.frame_id = "uav_local_ned"
        platform.attitude.w = 1.0
        platform.nav_state = self.latest_uav_state
        if self.latest_uav_position is not None:
            platform.position_ned = self.latest_uav_position.point
        return platform

    def _build_arm_state(self, stamp) -> ArmState:
        if self.latest_arm_state is None:
            arm = ArmState()
            arm.header.stamp = stamp
            arm.header.frame_id = self.arm_base_frame
            arm.end_effector_pose.header.stamp = stamp
            arm.end_effector_pose.header.frame_id = self.arm_base_frame
            arm.end_effector_pose.pose.orientation.w = 1.0
            arm.state = self.latest_arm_control_state
            return arm

        arm = ArmState()
        arm.header = self.latest_arm_state.header
        arm.header.stamp = stamp
        arm.header.frame_id = self.latest_arm_state.header.frame_id or self.arm_base_frame
        arm.joint_names = list(self.latest_arm_state.joint_names)
        arm.joint_positions = list(self.latest_arm_state.joint_positions)
        arm.joint_velocities = list(self.latest_arm_state.joint_velocities)
        arm.joint_efforts = list(self.latest_arm_state.joint_efforts)
        arm.end_effector_pose = self.latest_arm_state.end_effector_pose
        if not arm.end_effector_pose.header.frame_id:
            arm.end_effector_pose.header.frame_id = self.arm_base_frame
        arm.end_effector_pose.header.stamp = stamp
        arm.contact_detected = self.latest_arm_state.contact_detected
        arm.state = self.latest_arm_state.state or self.latest_arm_control_state
        return arm

    def _build_safety_status(self, now_ns: int) -> SafetyStatus:
        status = SafetyStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = self.map_frame

        reasons: List[str] = []
        self._append_stale_reason(reasons, "uav", self.last_uav_time_ns, now_ns)
        self._append_stale_reason(reasons, "arm", self.last_arm_time_ns, now_ns)

        if self.latest_uav_state == "INVALID_TARGET":
            reasons.append("uav control state is INVALID_TARGET")
        if self.latest_arm_control_state == "INVALID_TARGET":
            reasons.append("arm control state is INVALID_TARGET")

        status.safe = not reasons
        status.severity = (
            SafetyStatus.SEVERITY_OK if status.safe else SafetyStatus.SEVERITY_WARN
        )
        status.state = "OK" if status.safe else "DEGRADED"
        status.reasons = reasons
        return status

    def _append_stale_reason(
        self,
        reasons: List[str],
        label: str,
        stamp_ns: Optional[int],
        now_ns: int,
    ) -> None:
        if stamp_ns is None:
            reasons.append(f"{label} state has not been received")
            return

        age_sec = (now_ns - stamp_ns) / 1_000_000_000.0
        if age_sec > self.state_timeout:
            reasons.append(
                f"{label} state age {age_sec:.2f}s exceeds "
                f"state_timeout {self.state_timeout:.2f}s"
            )

    def _broadcast_tf(self, stamp, observation: SystemObservation) -> None:
        transforms = [
            self._map_to_uav_transform(stamp, observation.platform.position_ned),
            self._fixed_transform(
                stamp, self.uav_frame, self.arm_base_frame, self.arm_base_xyz
            ),
            self._ee_transform(stamp, observation.arm),
            self._fixed_transform(
                stamp, self.ee_frame, self.camera_frame, self.camera_xyz
            ),
        ]
        self.tf_broadcaster.sendTransform(transforms)

    def _map_to_uav_transform(self, stamp, position_ned) -> TransformStamped:
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = self.map_frame
        transform.child_frame_id = self.uav_frame
        enu_x, enu_y, enu_z = self._ned_point_to_enu_xyz(
            position_ned.x, position_ned.y, position_ned.z
        )
        transform.transform.translation.x = enu_x
        transform.transform.translation.y = enu_y
        transform.transform.translation.z = enu_z
        transform.transform.rotation.w = 1.0
        return transform

    def _ee_transform(self, stamp, arm: ArmState) -> TransformStamped:
        if arm.end_effector_pose.header.frame_id:
            parent_frame = arm.end_effector_pose.header.frame_id
        else:
            parent_frame = self.arm_base_frame

        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = parent_frame
        transform.child_frame_id = self.ee_frame
        transform.transform.translation.x = arm.end_effector_pose.pose.position.x
        transform.transform.translation.y = arm.end_effector_pose.pose.position.y
        transform.transform.translation.z = arm.end_effector_pose.pose.position.z
        transform.transform.rotation = arm.end_effector_pose.pose.orientation
        if transform.transform.rotation.w == 0.0:
            transform.transform.rotation.w = 1.0
        return transform

    def _fixed_transform(
        self,
        stamp,
        parent_frame: str,
        child_frame: str,
        xyz: List[float],
    ) -> TransformStamped:
        transform = TransformStamped()
        transform.header.stamp = stamp
        transform.header.frame_id = parent_frame
        transform.child_frame_id = child_frame
        transform.transform.translation.x = xyz[0]
        transform.transform.translation.y = xyz[1]
        transform.transform.translation.z = xyz[2]
        transform.transform.rotation.w = 1.0
        return transform

    def _float_triplet_parameter(self, parameter_name: str) -> List[float]:
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValueError(f"{parameter_name} must be a length-3 list")
        return [float(item) for item in value]

    @staticmethod
    def _ned_point_to_enu_xyz(x_ned: float, y_ned: float, z_ned: float):
        return float(y_ned), float(x_ned), float(-z_ned)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StateAggregator()
    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
