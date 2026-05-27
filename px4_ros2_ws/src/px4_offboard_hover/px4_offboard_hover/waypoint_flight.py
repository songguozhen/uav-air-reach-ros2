import math
from typing import Optional

import rclpy
from px4_msgs.msg import VehicleLocalPosition
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from px4_offboard_hover.offboard_base import OffboardPositionControl, Position


class WaypointFlight(OffboardPositionControl):
    def __init__(self) -> None:
        super().__init__("px4_demo02_waypoint_flight")

        self.declare_parameter("waypoint_acceptance", 0.25)
        self.declare_parameter("waypoint_hold_time", 1.0)
        self.declare_parameter("final_hold_time", 5.0)

        self.acceptance = float(self.get_parameter("waypoint_acceptance").value)
        self.hold_cycles = max(1, int(float(self.get_parameter("waypoint_hold_time").value) / 0.1))
        self.final_hold_cycles = max(
            1, int(float(self.get_parameter("final_hold_time").value) / 0.1)
        )
        self.waypoints = [
            (0.0, 0.0, -2.0),
            (2.0, 0.0, -2.0),
            (2.0, 2.0, -2.0),
            (0.0, 0.0, -2.0),
        ]
        self.index = 0
        self.reached_cycles = 0
        self.final_hold_counter = 0
        self.position: Optional[Position] = None

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.position_callback,
            qos,
        )
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.get_logger().info(
            "Demo 02 waypoint flight: (0,0,-2) -> (2,0,-2) -> (2,2,-2) -> (0,0,-2)"
        )

    def position_callback(self, msg: VehicleLocalPosition) -> None:
        if msg.xy_valid and msg.z_valid:
            self.position = (msg.x, msg.y, msg.z)

    def timer_callback(self) -> None:
        target = self.waypoints[self.index]
        self.tick_offboard(target)
        self.update_waypoint_state(target)

    def update_waypoint_state(self, target: Position) -> None:
        if self.position is None or self.counter <= self.warmup_cycles:
            return

        distance = math.dist(self.position, target)
        if distance > self.acceptance:
            self.reached_cycles = 0
            return

        self.reached_cycles += 1
        if self.index < len(self.waypoints) - 1 and self.reached_cycles >= self.hold_cycles:
            self.index += 1
            self.reached_cycles = 0
            self.get_logger().info(f"Switching to waypoint {self.index + 1}: {self.waypoints[self.index]}")
            return

        if self.index == len(self.waypoints) - 1:
            self.final_hold_counter += 1
            if self.final_hold_counter >= self.final_hold_cycles:
                if self.land_on_exit:
                    self.request_land()
                else:
                    self.get_logger().info("Waypoint demo complete; holding final waypoint")
                    self.final_hold_counter = 0


def main(args=None) -> None:
    rclpy.init(args=args)
    node = WaypointFlight()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
