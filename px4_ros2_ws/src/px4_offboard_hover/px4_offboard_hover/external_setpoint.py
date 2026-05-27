import time

from geometry_msgs.msg import Point
import rclpy

from px4_offboard_hover.offboard_base import OffboardPositionControl, Position


class ExternalSetpointInterface(OffboardPositionControl):
    def __init__(self) -> None:
        super().__init__("px4_demo04_external_setpoint_interface")

        self.declare_parameter("initial_x", 0.0)
        self.declare_parameter("initial_y", 0.0)
        self.declare_parameter("initial_z", -2.0)
        self.declare_parameter("target_timeout", 0.0)
        self.declare_parameter("yaw", 0.0)

        self.target: Position = (
            float(self.get_parameter("initial_x").value),
            float(self.get_parameter("initial_y").value),
            float(self.get_parameter("initial_z").value),
        )
        self.target_timeout = float(self.get_parameter("target_timeout").value)
        self.yaw = float(self.get_parameter("yaw").value)
        self.last_target_time = time.time()

        self.create_subscription(Point, "/uav/target_position", self.target_callback, 10)
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            "Demo 04 external setpoint interface ready: publish geometry_msgs/msg/Point "
            "to /uav/target_position with NED x,y,z"
        )

    def target_callback(self, msg: Point) -> None:
        self.target = (float(msg.x), float(msg.y), float(msg.z))
        self.last_target_time = time.time()
        self.get_logger().info(
            f"New target from /uav/target_position: x={msg.x:.2f}, y={msg.y:.2f}, z={msg.z:.2f}"
        )

    def timer_callback(self) -> None:
        if self.target_timeout > 0.0 and time.time() - self.last_target_time > self.target_timeout:
            self.get_logger().warn("Target timeout; holding last setpoint")
            self.last_target_time = time.time()

        self.tick_offboard(self.target, self.yaw)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ExternalSetpointInterface()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
