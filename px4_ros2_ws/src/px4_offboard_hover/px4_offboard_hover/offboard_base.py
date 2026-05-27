import math
from typing import Iterable, Optional, Sequence, Tuple

import rclpy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

Position = Tuple[float, float, float]


class OffboardPositionControl(Node):
    def __init__(self, node_name: str) -> None:
        super().__init__(node_name)

        self.declare_parameter("setpoint_warmup_cycles", 20)
        self.declare_parameter("auto_arm", True)
        self.declare_parameter("land_on_exit", False)

        self.warmup_cycles = int(self.get_parameter("setpoint_warmup_cycles").value)
        self.auto_arm = bool(self.get_parameter("auto_arm").value)
        self.land_on_exit = bool(self.get_parameter("land_on_exit").value)

        px4_in_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.offboard_pub = self.create_publisher(
            OffboardControlMode, "/fmu/in/offboard_control_mode", px4_in_qos
        )
        self.trajectory_pub = self.create_publisher(
            TrajectorySetpoint, "/fmu/in/trajectory_setpoint", px4_in_qos
        )
        self.command_pub = self.create_publisher(
            VehicleCommand, "/fmu/in/vehicle_command", px4_in_qos
        )

        self.counter = 0
        self.landing_requested = False
        self.land_command_repeats = 0

    def timestamp_us(self) -> int:
        return int(self.get_clock().now().nanoseconds / 1000)

    def tick_offboard(self, position: Optional[Position], yaw: float = 0.0) -> None:
        if self.landing_requested:
            self.repeat_land_or_shutdown()
            return

        if position is None:
            return

        self.publish_offboard_control_mode()
        self.publish_trajectory_setpoint(position, yaw)

        if (
            self.auto_arm
            and self.warmup_cycles <= self.counter < self.warmup_cycles + 10
        ):
            self.request_offboard_and_arm()

        self.counter += 1

    def request_offboard_and_arm(self) -> None:
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, [1.0, 6.0])
        self.publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            [float(VehicleCommand.ARMING_ACTION_ARM)],
        )
        self.get_logger().info("Requested OFFBOARD mode and arm")

    def request_land(self) -> None:
        if self.landing_requested:
            return

        self.landing_requested = True
        self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND, [])
        self.land_command_repeats = 1
        self.get_logger().info("Requested land")

    def repeat_land_or_shutdown(self) -> None:
        if self.land_command_repeats < 10:
            self.publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND, [])
            self.land_command_repeats += 1
            return

        self.get_logger().info("Land command sent; stopping offboard setpoint stream")
        self.destroy_timer(self.timer)
        if rclpy.ok():
            rclpy.shutdown()

    def publish_offboard_control_mode(self) -> None:
        msg = OffboardControlMode()
        msg.timestamp = self.timestamp_us()
        msg.position = True
        msg.velocity = False
        msg.acceleration = False
        msg.attitude = False
        msg.body_rate = False
        msg.thrust_and_torque = False
        msg.direct_actuator = False
        self.offboard_pub.publish(msg)

    def publish_trajectory_setpoint(
        self, position: Sequence[float], yaw: float = 0.0
    ) -> None:
        msg = TrajectorySetpoint()
        msg.timestamp = self.timestamp_us()
        msg.position = [float(position[0]), float(position[1]), float(position[2])]
        msg.velocity = [math.nan, math.nan, math.nan]
        msg.acceleration = [math.nan, math.nan, math.nan]
        msg.jerk = [math.nan, math.nan, math.nan]
        msg.yaw = yaw
        msg.yawspeed = math.nan
        self.trajectory_pub.publish(msg)

    def publish_vehicle_command(self, command: int, params: Iterable[float]) -> None:
        values = list(params) + [0.0] * 7
        msg = VehicleCommand()
        msg.timestamp = self.timestamp_us()
        msg.command = command
        msg.param1 = float(values[0])
        msg.param2 = float(values[1])
        msg.param3 = float(values[2])
        msg.param4 = float(values[3])
        msg.param5 = float(values[4])
        msg.param6 = float(values[5])
        msg.param7 = float(values[6])
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        self.command_pub.publish(msg)
