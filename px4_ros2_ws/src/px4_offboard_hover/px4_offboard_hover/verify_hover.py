import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from px4_msgs.msg import VehicleLocalPosition, VehicleStatus


class HoverMonitor(Node):
    def __init__(self) -> None:
        super().__init__("px4_offboard_hover_verify")
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.status = None
        self.samples = []
        self.create_subscription(
            VehicleStatus, "/fmu/out/vehicle_status_v4", self.status_callback, qos
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.position_callback,
            qos,
        )

    def status_callback(self, msg: VehicleStatus) -> None:
        self.status = msg

    def position_callback(self, msg: VehicleLocalPosition) -> None:
        if self.status is None or not msg.xy_valid or not msg.z_valid:
            return

        self.samples.append(
            (
                time.time(),
                self.status.arming_state,
                self.status.nav_state,
                msg.x,
                msg.y,
                msg.z,
                msg.vx,
                msg.vy,
                msg.vz,
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=25.0)
    parser.add_argument("--target-z", type=float, default=-2.0)
    parser.add_argument("--z-tolerance", type=float, default=0.35)
    parser.add_argument("--max-speed", type=float, default=0.8)
    parser.add_argument("--window", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rclpy.init()
    node = HoverMonitor()

    end_time = time.time() + args.duration
    while time.time() < end_time:
        rclpy.spin_once(node, timeout_sec=0.1)

    samples = node.samples
    if not samples:
        print("RESULT=FAIL reason=no_samples")
        node.destroy_node()
        rclpy.shutdown()
        raise SystemExit(1)

    stable = samples[-args.window :] if len(samples) >= args.window else samples
    last = samples[-1]
    zs = [sample[5] for sample in stable]
    xs = [sample[3] for sample in stable]
    ys = [sample[4] for sample in stable]
    speeds = [
        math.sqrt(sample[6] ** 2 + sample[7] ** 2 + sample[8] ** 2)
        for sample in stable
    ]
    offboard_count = sum(
        1 for sample in stable if sample[2] == VehicleStatus.NAVIGATION_STATE_OFFBOARD
    )
    armed_count = sum(
        1 for sample in stable if sample[1] == VehicleStatus.ARMING_STATE_ARMED
    )
    z_avg = sum(zs) / len(zs)
    speed_max = max(speeds)

    print(f"samples={len(samples)} stable_window={len(stable)}")
    print(
        "last "
        f"arming_state={last[1]} nav_state={last[2]} "
        f"x={last[3]:.3f} y={last[4]:.3f} z={last[5]:.3f} "
        f"vx={last[6]:.3f} vy={last[7]:.3f} vz={last[8]:.3f}"
    )
    print(f"stable z_avg={z_avg:.3f} z_min={min(zs):.3f} z_max={max(zs):.3f}")
    print(
        f"stable x_abs_max={max(abs(x) for x in xs):.3f} "
        f"y_abs_max={max(abs(y) for y in ys):.3f} "
        f"speed_avg={sum(speeds) / len(speeds):.3f} speed_max={speed_max:.3f}"
    )
    print(f"stable offboard_count={offboard_count} armed_count={armed_count}")

    ok = (
        last[1] == VehicleStatus.ARMING_STATE_ARMED
        and last[2] == VehicleStatus.NAVIGATION_STATE_OFFBOARD
        and offboard_count == len(stable)
        and armed_count == len(stable)
        and abs(z_avg - args.target_z) <= args.z_tolerance
        and speed_max <= args.max_speed
    )
    print("RESULT=" + ("PASS" if ok else "FAIL"))

    node.destroy_node()
    rclpy.shutdown()
    raise SystemExit(0 if ok else 1)
