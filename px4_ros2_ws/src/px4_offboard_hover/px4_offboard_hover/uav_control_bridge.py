import math
import time
from typing import Optional

from geometry_msgs.msg import Point, PointStamped
from px4_msgs.msg import VehicleLocalPosition
import rclpy
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String

from px4_offboard_hover.offboard_base import OffboardPositionControl, Position


class UavControlBridge(OffboardPositionControl):
    """Validated high-level /uav target bridge for PX4 offboard position control."""

    def __init__(self) -> None:
        super().__init__("uav_control_bridge")

        self.declare_parameter("initial_x", 0.0)
        self.declare_parameter("initial_y", 0.0)
        self.declare_parameter("initial_z", -2.0)
        self.declare_parameter("yaw", 0.0)
        self.declare_parameter("target_timeout", 1.0)
        self.declare_parameter("max_altitude", 5.0)
        self.declare_parameter("min_altitude", 0.5)
        self.declare_parameter("max_horizontal_range", 5.0)
        self.declare_parameter("target_jump_limit", 1.5)
        self.declare_parameter("reach_xy_tolerance", 0.30)
        self.declare_parameter("reach_z_tolerance", 0.20)
        self.declare_parameter("reach_hold_time", 1.0)

        self.safe_target: Position = (
            float(self.get_parameter("initial_x").value),
            float(self.get_parameter("initial_y").value),
            float(self.get_parameter("initial_z").value),
        )
        self.yaw = float(self.get_parameter("yaw").value)
        self.target_timeout = float(self.get_parameter("target_timeout").value)
        self.max_altitude = float(self.get_parameter("max_altitude").value)
        self.min_altitude = float(self.get_parameter("min_altitude").value)
        self.max_horizontal_range = float(
            self.get_parameter("max_horizontal_range").value
        )
        self.target_jump_limit = float(self.get_parameter("target_jump_limit").value)
        self.reach_xy_tolerance = float(
            self.get_parameter("reach_xy_tolerance").value
        )
        self.reach_z_tolerance = float(self.get_parameter("reach_z_tolerance").value)
        self.reach_hold_time = float(self.get_parameter("reach_hold_time").value)

        error = self._validate_target(self.safe_target, check_jump=False)
        if error is not None:
            raise ValueError(f"Initial target is unsafe: {error}")

        self.last_safe_target_time = time.monotonic()
        self.last_timeout_warning_time = 0.0
        self.control_state = "HOLDING"
        self.current_position: Optional[Position] = None
        self.reach_start_time: Optional[float] = None
        self.reached_target = False
        self.invalid_target_pending = False

        px4_out_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.current_position_pub = self.create_publisher(
            PointStamped, "/uav/current_position", 10
        )
        self.current_target_pub = self.create_publisher(
            PointStamped, "/uav/current_target", 10
        )
        self.reached_target_pub = self.create_publisher(
            Bool, "/uav/reached_target", 10
        )
        self.control_state_pub = self.create_publisher(
            String, "/uav/control_state", 10
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.position_callback,
            px4_out_qos,
        )
        self.create_subscription(Point, "/uav/target_position", self.target_callback, 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            "UAV control bridge ready on /uav/target_position; targets must be "
            "local PX4 NED points with z=-altitude"
        )

    def position_callback(self, msg: VehicleLocalPosition) -> None:
        if not msg.xy_valid or not msg.z_valid:
            return

        self.current_position = (float(msg.x), float(msg.y), float(msg.z))
        position_msg = self._point_stamped(self.current_position)
        self.current_position_pub.publish(position_msg)

    def target_callback(self, msg: Point) -> None:
        target = (float(msg.x), float(msg.y), float(msg.z))
        error = self._validate_target(target, check_jump=True)
        if error is not None:
            self.get_logger().warn(
                "Rejected /uav/target_position "
                f"x={msg.x:.2f}, y={msg.y:.2f}, z={msg.z:.2f}: {error}"
            )
            self.control_state = "INVALID_TARGET"
            self.invalid_target_pending = True
            self._publish_bridge_state()
            return

        self.safe_target = target
        self.last_safe_target_time = time.monotonic()
        self.last_timeout_warning_time = 0.0
        self.reach_start_time = None
        self.reached_target = False
        self.invalid_target_pending = False
        self.control_state = "TRACKING"
        self.get_logger().info(
            "Accepted /uav/target_position "
            f"x={target[0]:.2f}, y={target[1]:.2f}, z={target[2]:.2f}"
        )

    def timer_callback(self) -> None:
        self.tick_offboard(self.safe_target, self.yaw)
        self._update_reached_target()
        self._update_control_state()
        self._publish_bridge_state()

    def _validate_target(
        self, target: Position, check_jump: bool
    ) -> Optional[str]:
        x, y, z = target
        if not all(math.isfinite(value) for value in target):
            return "target contains non-finite values"

        altitude = -z
        if altitude <= 0.0:
            return "positive altitude commands are not accepted; publish NED z=-altitude"
        if altitude > self.max_altitude:
            return (
                f"altitude {altitude:.2f} m exceeds max_altitude "
                f"{self.max_altitude:.2f} m"
            )
        if altitude < self.min_altitude:
            return (
                f"altitude {altitude:.2f} m is below min_altitude "
                f"{self.min_altitude:.2f} m"
            )

        horizontal_range = math.hypot(x, y)
        if horizontal_range > self.max_horizontal_range:
            return (
                f"horizontal range {horizontal_range:.2f} m exceeds "
                f"max_horizontal_range {self.max_horizontal_range:.2f} m"
            )

        if check_jump:
            jump = self._distance(target, self.safe_target)
            if jump > self.target_jump_limit:
                return (
                    f"target jump {jump:.2f} m exceeds target_jump_limit "
                    f"{self.target_jump_limit:.2f} m"
                )

        return None

    def _target_timed_out(self, now: float) -> bool:
        if self.target_timeout <= 0.0:
            return False

        return now - self.last_safe_target_time > self.target_timeout

    def _warn_if_target_timed_out(self, now: float) -> None:
        if not self._target_timed_out(now):
            return
        if now - self.last_timeout_warning_time < self.target_timeout:
            return

        self.get_logger().warn("Target timeout; holding last safe target")
        self.last_timeout_warning_time = now

    def _update_reached_target(self) -> None:
        if self.current_position is None:
            self.reach_start_time = None
            self.reached_target = False
            return

        dx = self.current_position[0] - self.safe_target[0]
        dy = self.current_position[1] - self.safe_target[1]
        dz = self.current_position[2] - self.safe_target[2]
        within_tolerance = (
            math.hypot(dx, dy) <= self.reach_xy_tolerance
            and abs(dz) <= self.reach_z_tolerance
        )
        if not within_tolerance:
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
        target_msg = self._point_stamped(self.safe_target)
        self.current_target_pub.publish(target_msg)

        reached_msg = Bool()
        reached_msg.data = self.reached_target
        self.reached_target_pub.publish(reached_msg)

        state_msg = String()
        state_msg.data = self.control_state
        self.control_state_pub.publish(state_msg)

    def _point_stamped(self, point: Position) -> PointStamped:
        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "uav_local_ned"
        msg.point.x = point[0]
        msg.point.y = point[1]
        msg.point.z = point[2]
        return msg

    @staticmethod
    def _distance(first: Position, second: Position) -> float:
        dx = first[0] - second[0]
        dy = first[1] - second[1]
        dz = first[2] - second[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = UavControlBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
