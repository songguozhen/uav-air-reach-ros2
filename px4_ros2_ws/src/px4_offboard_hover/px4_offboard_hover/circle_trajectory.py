import math

import rclpy

from px4_offboard_hover.offboard_base import OffboardPositionControl


class CircleTrajectory(OffboardPositionControl):
    def __init__(self) -> None:
        super().__init__("px4_demo03_circle_trajectory")

        self.declare_parameter("center_x", 0.0)
        self.declare_parameter("center_y", 0.0)
        self.declare_parameter("altitude", 2.0)
        self.declare_parameter("radius", 1.5)
        self.declare_parameter("angular_speed", 0.35)
        self.declare_parameter("duration", 60.0)
        self.declare_parameter("yaw", 0.0)

        self.center_x = float(self.get_parameter("center_x").value)
        self.center_y = float(self.get_parameter("center_y").value)
        self.z = -abs(float(self.get_parameter("altitude").value))
        self.radius = float(self.get_parameter("radius").value)
        self.angular_speed = float(self.get_parameter("angular_speed").value)
        self.duration = float(self.get_parameter("duration").value)
        self.yaw = float(self.get_parameter("yaw").value)
        self.start_time = None

        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            f"Demo 03 circle trajectory: center=({self.center_x:.1f},{self.center_y:.1f}), "
            f"radius={self.radius:.1f}, z={self.z:.1f}"
        )

    def timer_callback(self) -> None:
        now = self.get_clock().now()
        if self.start_time is None and self.counter >= self.warmup_cycles:
            self.start_time = now

        elapsed = 0.0
        if self.start_time is not None:
            elapsed = (now - self.start_time).nanoseconds / 1e9

        angle = self.angular_speed * elapsed
        target = (
            self.center_x + self.radius * math.cos(angle),
            self.center_y + self.radius * math.sin(angle),
            self.z,
        )
        self.tick_offboard(target, self.yaw)

        if self.duration > 0.0 and elapsed >= self.duration:
            if self.land_on_exit:
                self.request_land()
            else:
                self.get_logger().info("Circle demo duration reached; continuing circle")
                self.start_time = now


def main(args=None) -> None:
    rclpy.init(args=args)
    node = CircleTrajectory()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
