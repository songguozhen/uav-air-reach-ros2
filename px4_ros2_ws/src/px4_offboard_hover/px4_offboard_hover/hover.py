import rclpy

from px4_offboard_hover.offboard_base import OffboardPositionControl, Position


class OffboardHover(OffboardPositionControl):
    def __init__(self) -> None:
        super().__init__("px4_offboard_hover")

        self.declare_parameter("altitude", 2.0)
        self.declare_parameter("x", 0.0)
        self.declare_parameter("y", 0.0)
        self.declare_parameter("yaw", 0.0)
        self.declare_parameter("hover_duration", 0.0)

        self.altitude = float(self.get_parameter("altitude").value)
        self.x = float(self.get_parameter("x").value)
        self.y = float(self.get_parameter("y").value)
        self.yaw = float(self.get_parameter("yaw").value)
        self.hover_duration = float(self.get_parameter("hover_duration").value)
        self.target: Position = (self.x, self.y, -abs(self.altitude))

        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            f"Streaming hover setpoint x={self.x:.1f}, y={self.y:.1f}, z=-{self.altitude:.1f} m"
        )

    def timer_callback(self) -> None:
        self.tick_offboard(self.target, self.yaw)
        if self.should_land():
            self.request_land()

    def should_land(self) -> bool:
        if not self.land_on_exit or self.landing_requested or self.hover_duration <= 0.0:
            return False

        hover_cycles = int(self.hover_duration / 0.1)
        return self.counter >= self.warmup_cycles + hover_cycles


def main(args=None) -> None:
    rclpy.init(args=args)
    node = OffboardHover()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
