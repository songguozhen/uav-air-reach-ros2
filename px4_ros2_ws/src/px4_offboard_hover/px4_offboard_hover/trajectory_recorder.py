import csv
import math
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import animation
from px4_msgs.msg import TrajectorySetpoint, VehicleLocalPosition
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

Position = Tuple[float, float, float]
Sample = Tuple[float, float, float, float, float, float, float, float, float, float]


class TrajectoryRecorder(Node):
    def __init__(self) -> None:
        super().__init__("px4_trajectory_recorder")

        self.declare_parameter("output_dir", "logs/trajectory")
        self.declare_parameter("duration", 90.0)
        self.declare_parameter("title", "PX4 trajectory")
        self.declare_parameter("demo_id", "generic")
        self.declare_parameter("fps", 12)
        self.declare_parameter("make_video", True)
        self.declare_parameter("max_speed_pass", 3.0)
        self.declare_parameter("avg_error_pass", 0.9)
        self.declare_parameter("max_error_pass", 2.0)
        self.declare_parameter("height_error_pass", 0.35)
        self.declare_parameter("final_error_pass", 0.6)
        self.declare_parameter("min_samples_pass", 40)

        self.output_dir = Path(str(self.get_parameter("output_dir").value))
        self.duration = float(self.get_parameter("duration").value)
        self.title = str(self.get_parameter("title").value)
        self.demo_id = str(self.get_parameter("demo_id").value)
        self.fps = int(self.get_parameter("fps").value)
        self.make_video = bool(self.get_parameter("make_video").value)
        self.thresholds = {
            "max_speed_pass": float(self.get_parameter("max_speed_pass").value),
            "avg_error_pass": float(self.get_parameter("avg_error_pass").value),
            "max_error_pass": float(self.get_parameter("max_error_pass").value),
            "height_error_pass": float(self.get_parameter("height_error_pass").value),
            "final_error_pass": float(self.get_parameter("final_error_pass").value),
            "min_samples_pass": int(self.get_parameter("min_samples_pass").value),
        }

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / "trajectory.csv"
        self.start_time = time.time()
        self.latest_target: Optional[Position] = None
        self.samples: List[Sample] = []

        px4_out_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        px4_in_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.create_subscription(
            VehicleLocalPosition,
            "/fmu/out/vehicle_local_position_v1",
            self.position_callback,
            px4_out_qos,
        )
        self.create_subscription(
            TrajectorySetpoint,
            "/fmu/in/trajectory_setpoint",
            self.target_callback,
            px4_in_qos,
        )
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.get_logger().info(
            f"Recording {self.demo_id} for {self.duration:.1f}s into {self.output_dir}"
        )

    def target_callback(self, msg: TrajectorySetpoint) -> None:
        if len(msg.position) >= 3:
            self.latest_target = (
                float(msg.position[0]),
                float(msg.position[1]),
                float(msg.position[2]),
            )

    def position_callback(self, msg: VehicleLocalPosition) -> None:
        if not msg.xy_valid or not msg.z_valid:
            return

        elapsed = time.time() - self.start_time
        target = self.latest_target or (math.nan, math.nan, math.nan)
        self.samples.append(
            (
                elapsed,
                float(msg.x),
                float(msg.y),
                float(msg.z),
                float(msg.vx),
                float(msg.vy),
                float(msg.vz),
                target[0],
                target[1],
                target[2],
            )
        )

    def timer_callback(self) -> None:
        if time.time() - self.start_time < self.duration:
            return

        self.write_outputs()
        self.destroy_timer(self.timer)
        if rclpy.ok():
            rclpy.shutdown()

    def write_outputs(self) -> None:
        metrics = self.compute_metrics()
        self.write_csv()
        if not self.samples:
            self.write_result(False, "no_samples")
            self.write_summary(metrics, None)
            self.get_logger().warn("No samples recorded; skipped visualization")
            return

        self.write_xy_path()
        self.write_3d_path()
        self.write_height_curve()
        self.write_speed_curve()
        self.write_tracking_error()
        video_path = self.write_animation() if self.make_video else None
        passed, reason = self.evaluate_pass_fail(metrics)
        self.write_result(passed, reason)
        self.write_summary(metrics, video_path, passed, reason)
        self.get_logger().info(f"Visualization written to {self.output_dir}")

    def write_csv(self) -> None:
        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "t",
                    "x",
                    "y",
                    "z",
                    "vx",
                    "vy",
                    "vz",
                    "speed_mps",
                    "target_x",
                    "target_y",
                    "target_z",
                    "error_xy_m",
                    "error_z_m",
                    "error_3d_m",
                ]
            )
            for sample in self.samples:
                speed = self.speed(sample)
                err_xy, err_z, err_3d = self.error_components(sample)
                writer.writerow(
                    [
                        f"{sample[0]:.3f}",
                        f"{sample[1]:.4f}",
                        f"{sample[2]:.4f}",
                        f"{sample[3]:.4f}",
                        f"{sample[4]:.4f}",
                        f"{sample[5]:.4f}",
                        f"{sample[6]:.4f}",
                        f"{speed:.4f}",
                        self.float_cell(sample[7]),
                        self.float_cell(sample[8]),
                        self.float_cell(sample[9]),
                        self.float_cell(err_xy),
                        self.float_cell(err_z),
                        self.float_cell(err_3d),
                    ]
                )

    def write_xy_path(self) -> None:
        x = [s[1] for s in self.samples]
        y = [s[2] for s in self.samples]
        tx, ty, _ = self.target_series()

        fig, ax = plt.subplots(figsize=(8, 7), constrained_layout=True)
        ax.set_title(f"{self.title} - XY path")
        ax.plot(x, y, color="#1764ab", linewidth=2.2, label="actual")
        if tx and ty:
            ax.plot(tx, ty, color="#d1495b", linestyle="--", linewidth=1.7, label="target")
            target_points = self.unique_target_points()
            if target_points:
                ax.scatter(
                    [p[0] for p in target_points],
                    [p[1] for p in target_points],
                    color="#d1495b",
                    s=42,
                    zorder=4,
                    label="target points",
                )
        ax.scatter(x[0], y[0], color="#2a9d8f", s=58, zorder=5, label="start")
        ax.scatter(x[-1], y[-1], color="#111111", s=58, zorder=5, label="end")
        ax.set_xlabel("x forward (m)")
        ax.set_ylabel("y right (m)")
        ax.axis("equal")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.savefig(self.output_dir / "xy_path.png", dpi=160)
        plt.close(fig)

    def write_3d_path(self) -> None:
        x = [s[1] for s in self.samples]
        y = [s[2] for s in self.samples]
        alt = [-s[3] for s in self.samples]
        tx, ty, tz = self.target_series()

        fig = plt.figure(figsize=(9, 7), constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d")
        ax.set_title(f"{self.title} - 3D trajectory")
        ax.plot(x, y, alt, color="#1764ab", linewidth=2.0, label="actual")
        if tx and ty and tz:
            ax.plot(tx, ty, [-z for z in tz], color="#d1495b", linestyle="--", linewidth=1.5, label="target")
        ax.scatter([x[0]], [y[0]], [alt[0]], color="#2a9d8f", s=45, label="start")
        ax.scatter([x[-1]], [y[-1]], [alt[-1]], color="#111111", s=45, label="end")
        ax.set_xlabel("x forward (m)")
        ax.set_ylabel("y right (m)")
        ax.set_zlabel("altitude (m)")
        ax.legend(loc="best")
        fig.savefig(self.output_dir / "trajectory_3d.png", dpi=160)
        plt.close(fig)

    def write_height_curve(self) -> None:
        t = [s[0] for s in self.samples]
        altitude = [-s[3] for s in self.samples]
        _, _, tz = self.target_series()

        fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
        ax.set_title(f"{self.title} - height")
        ax.plot(t, altitude, color="#1764ab", linewidth=2.0, label="actual altitude")
        if tz:
            ax.plot(t[: len(tz)], [-z for z in tz], color="#d1495b", linestyle="--", linewidth=1.5, label="target altitude")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("altitude (m)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.savefig(self.output_dir / "height_curve.png", dpi=160)
        plt.close(fig)

    def write_speed_curve(self) -> None:
        t = [s[0] for s in self.samples]
        speed = [self.speed(s) for s in self.samples]

        fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
        ax.set_title(f"{self.title} - speed")
        ax.plot(t, speed, color="#1764ab", linewidth=2.0, label="speed")
        ax.axhline(self.thresholds["max_speed_pass"], color="#d1495b", linestyle="--", linewidth=1.3, label="PASS limit")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("speed (m/s)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.savefig(self.output_dir / "speed_curve.png", dpi=160)
        plt.close(fig)

    def write_tracking_error(self) -> None:
        t = [s[0] for s in self.samples]
        err_xy = []
        err_3d = []
        err_z = []
        for sample in self.samples:
            xy, z, err = self.error_components(sample)
            err_xy.append(xy)
            err_z.append(abs(z) if not math.isnan(z) else math.nan)
            err_3d.append(err)

        fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
        ax.set_title(f"{self.title} - tracking error")
        ax.plot(t, err_3d, color="#1764ab", linewidth=2.0, label="3D error")
        ax.plot(t, err_xy, color="#2a9d8f", linewidth=1.5, label="XY error")
        ax.plot(t, err_z, color="#7a5195", linewidth=1.3, label="height error")
        ax.axhline(self.thresholds["avg_error_pass"], color="#d1495b", linestyle="--", linewidth=1.3, label="avg PASS limit")
        ax.set_xlabel("time (s)")
        ax.set_ylabel("error (m)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        fig.savefig(self.output_dir / "tracking_error.png", dpi=160)
        plt.close(fig)

    def write_animation(self) -> Optional[Path]:
        if len(self.samples) < 2:
            return None

        step = max(1, len(self.samples) // 160)
        frames = list(range(0, len(self.samples), step))
        x = [s[1] for s in self.samples]
        y = [s[2] for s in self.samples]
        tx, ty, _ = self.target_series()

        fig, ax = plt.subplots(figsize=(7, 7), constrained_layout=True)
        ax.set_title(self.title)
        ax.set_xlabel("x forward (m)")
        ax.set_ylabel("y right (m)")
        ax.grid(True, alpha=0.3)
        ax.axis("equal")
        margin = 0.75
        all_x = x + tx
        all_y = y + ty
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

        actual_line, = ax.plot([], [], color="#1764ab", linewidth=2.2, label="actual")
        target_line, = ax.plot([], [], color="#d1495b", linestyle="--", linewidth=1.5, label="target")
        current_dot = ax.scatter([], [], color="#111111", s=70, zorder=4)
        ax.legend(loc="best")

        def update(frame_index: int):
            actual_line.set_data(x[: frame_index + 1], y[: frame_index + 1])
            if tx and ty:
                target_line.set_data(tx[: frame_index + 1], ty[: frame_index + 1])
            current_dot.set_offsets([[x[frame_index], y[frame_index]]])
            return actual_line, target_line, current_dot

        ani = animation.FuncAnimation(fig, update, frames=frames, interval=1000 / self.fps, blit=True)
        if shutil.which("ffmpeg"):
            output = self.output_dir / "trajectory.mp4"
            ani.save(output, writer="ffmpeg", fps=self.fps, dpi=130)
        else:
            output = self.output_dir / "trajectory.gif"
            ani.save(output, writer="pillow", fps=self.fps, dpi=110)
        plt.close(fig)
        return output

    def compute_metrics(self) -> Dict[str, float]:
        metrics: Dict[str, float] = {
            "samples": float(len(self.samples)),
            "duration_s": 0.0,
            "path_length_m": 0.0,
            "max_speed_mps": 0.0,
            "avg_speed_mps": 0.0,
            "avg_error_3d_m": math.nan,
            "max_error_3d_m": math.nan,
            "avg_error_xy_m": math.nan,
            "avg_height_error_m": math.nan,
            "final_error_3d_m": math.nan,
            "target_point_count": float(len(self.unique_target_points())),
            "circle_radius_avg_m": math.nan,
            "circle_radius_error_avg_m": math.nan,
            "stable_avg_error_3d_m": math.nan,
            "stable_avg_height_error_m": math.nan,
            "stable_max_speed_mps": math.nan,
            "flight_avg_error_3d_m": math.nan,
            "flight_avg_error_xy_m": math.nan,
            "flight_avg_height_error_m": math.nan,
            "flight_circle_radius_error_avg_m": math.nan,
        }
        if not self.samples:
            return metrics

        metrics["duration_s"] = self.samples[-1][0]
        speeds = [self.speed(sample) for sample in self.samples]
        metrics["max_speed_mps"] = max(speeds)
        metrics["avg_speed_mps"] = sum(speeds) / len(speeds)
        for prev, cur in zip(self.samples, self.samples[1:]):
            metrics["path_length_m"] += math.dist(prev[1:4], cur[1:4])

        errors_3d = []
        errors_xy = []
        errors_z = []
        for sample in self.samples:
            err_xy, err_z, err_3d = self.error_components(sample)
            if not math.isnan(err_3d):
                errors_3d.append(err_3d)
            if not math.isnan(err_xy):
                errors_xy.append(err_xy)
            if not math.isnan(err_z):
                errors_z.append(abs(err_z))
        if errors_3d:
            metrics["avg_error_3d_m"] = sum(errors_3d) / len(errors_3d)
            metrics["max_error_3d_m"] = max(errors_3d)
            metrics["final_error_3d_m"] = errors_3d[-1]
        if errors_xy:
            metrics["avg_error_xy_m"] = sum(errors_xy) / len(errors_xy)
        if errors_z:
            metrics["avg_height_error_m"] = sum(errors_z) / len(errors_z)

        stable = self.stable_samples()
        flight = self.flight_samples()
        if self.demo_id == "demo03":
            circle_samples = flight or stable or self.samples
            radii = [math.hypot(s[7], s[8]) for s in circle_samples if self.has_target(s)]
            actual_radii = [math.hypot(s[1], s[2]) for s in circle_samples]
            if radii and actual_radii:
                radius = sum(radii) / len(radii)
                metrics["circle_radius_avg_m"] = sum(actual_radii) / len(actual_radii)
                metrics["circle_radius_error_avg_m"] = sum(abs(r - radius) for r in actual_radii) / len(actual_radii)
                metrics["flight_circle_radius_error_avg_m"] = metrics["circle_radius_error_avg_m"]
        if stable:
            stable_errors = [self.error_components(s) for s in stable if self.has_target(s)]
            stable_3d = [e[2] for e in stable_errors if not math.isnan(e[2])]
            stable_z = [abs(e[1]) for e in stable_errors if not math.isnan(e[1])]
            stable_speed = [self.speed(s) for s in stable]
            if stable_3d:
                metrics["stable_avg_error_3d_m"] = sum(stable_3d) / len(stable_3d)
            if stable_z:
                metrics["stable_avg_height_error_m"] = sum(stable_z) / len(stable_z)
            if stable_speed:
                metrics["stable_max_speed_mps"] = max(stable_speed)
        if flight:
            flight_errors = [self.error_components(s) for s in flight if self.has_target(s)]
            flight_3d = [e[2] for e in flight_errors if not math.isnan(e[2])]
            flight_xy = [e[0] for e in flight_errors if not math.isnan(e[0])]
            flight_z = [abs(e[1]) for e in flight_errors if not math.isnan(e[1])]
            if flight_3d:
                metrics["flight_avg_error_3d_m"] = sum(flight_3d) / len(flight_3d)
            if flight_xy:
                metrics["flight_avg_error_xy_m"] = sum(flight_xy) / len(flight_xy)
            if flight_z:
                metrics["flight_avg_height_error_m"] = sum(flight_z) / len(flight_z)
        return metrics

    def evaluate_pass_fail(self, metrics: Dict[str, float]) -> Tuple[bool, str]:
        if metrics["samples"] < self.thresholds["min_samples_pass"]:
            return False, "too_few_samples"
        if metrics["max_speed_mps"] > self.thresholds["max_speed_pass"]:
            return False, "max_speed_exceeded"
        if math.isnan(metrics["avg_error_3d_m"]):
            return False, "no_target_samples"

        demo = self.demo_id
        if demo == "demo01":
            if metrics["stable_max_speed_mps"] > self.thresholds["max_speed_pass"]:
                return False, "stable_speed_exceeded"
            if metrics["stable_avg_height_error_m"] > self.thresholds["height_error_pass"]:
                return False, "height_not_stable"
            if metrics["stable_avg_error_3d_m"] > self.thresholds["avg_error_pass"]:
                return False, "hover_error_high"
        elif demo == "demo02":
            if metrics["target_point_count"] < 4:
                return False, "waypoints_not_observed"
            if math.isnan(metrics["flight_avg_error_3d_m"]):
                return False, "no_airborne_tracking_samples"
            if metrics["flight_avg_error_3d_m"] > self.thresholds["avg_error_pass"]:
                return False, "waypoint_tracking_error_high"
        elif demo == "demo03":
            if math.isnan(metrics["flight_circle_radius_error_avg_m"]):
                return False, "no_airborne_circle_samples"
            if metrics["flight_circle_radius_error_avg_m"] > 0.6:
                return False, "circle_radius_error_high"
            if math.isnan(metrics["flight_avg_height_error_m"]):
                return False, "no_airborne_height_samples"
            if metrics["flight_avg_height_error_m"] > self.thresholds["height_error_pass"]:
                return False, "circle_height_error_high"
        elif demo == "demo04":
            if metrics["target_point_count"] < 4:
                return False, "external_targets_not_observed"
            if metrics["final_error_3d_m"] > self.thresholds["final_error_pass"]:
                return False, "final_target_error_high"
            if metrics["avg_error_3d_m"] > self.thresholds["avg_error_pass"]:
                return False, "external_tracking_error_high"
        else:
            if metrics["avg_error_3d_m"] > self.thresholds["avg_error_pass"]:
                return False, "tracking_error_high"

        return True, "ok"

    def write_summary(
        self,
        metrics: Dict[str, float],
        video_path: Optional[Path],
        passed: bool = False,
        reason: str = "no_samples",
    ) -> None:
        lines = [
            f"# {self.title}",
            "",
            f"RESULT={'PASS' if passed else 'FAIL'}",
            f"reason={reason}",
            "",
            f"- demo_id: {self.demo_id}",
            f"- samples: {int(metrics['samples'])}",
            f"- duration_s: {metrics['duration_s']:.2f}",
            f"- path_length_m: {metrics['path_length_m']:.2f}",
            f"- max_speed_mps: {metrics['max_speed_mps']:.2f}",
            f"- avg_speed_mps: {metrics['avg_speed_mps']:.2f}",
            f"- avg_error_3d_m: {self.metric_cell(metrics['avg_error_3d_m'])}",
            f"- max_error_3d_m: {self.metric_cell(metrics['max_error_3d_m'])}",
            f"- avg_error_xy_m: {self.metric_cell(metrics['avg_error_xy_m'])}",
            f"- avg_height_error_m: {self.metric_cell(metrics['avg_height_error_m'])}",
            f"- final_error_3d_m: {self.metric_cell(metrics['final_error_3d_m'])}",
            f"- stable_avg_error_3d_m: {self.metric_cell(metrics['stable_avg_error_3d_m'])}",
            f"- stable_avg_height_error_m: {self.metric_cell(metrics['stable_avg_height_error_m'])}",
            f"- stable_max_speed_mps: {self.metric_cell(metrics['stable_max_speed_mps'])}",
            f"- flight_avg_error_3d_m: {self.metric_cell(metrics['flight_avg_error_3d_m'])}",
            f"- flight_avg_error_xy_m: {self.metric_cell(metrics['flight_avg_error_xy_m'])}",
            f"- flight_avg_height_error_m: {self.metric_cell(metrics['flight_avg_height_error_m'])}",
            f"- flight_circle_radius_error_avg_m: {self.metric_cell(metrics['flight_circle_radius_error_avg_m'])}",
            f"- target_point_count: {int(metrics['target_point_count'])}",
            f"- final_position_ned: {self.final_position_text()}",
            "",
            "## Outputs",
            "",
            "- trajectory.csv",
            "- trajectory_3d.png",
            "- xy_path.png",
            "- height_curve.png",
            "- speed_curve.png",
            "- tracking_error.png",
        ]
        if video_path:
            lines.append(f"- {video_path.name}")
        lines.append("- result.txt")
        (self.output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_result(self, passed: bool, reason: str) -> None:
        text = f"RESULT={'PASS' if passed else 'FAIL'} reason={reason}\n"
        (self.output_dir / "result.txt").write_text(text, encoding="utf-8")

    def target_series(self) -> Tuple[List[float], List[float], List[float]]:
        tx: List[float] = []
        ty: List[float] = []
        tz: List[float] = []
        for sample in self.samples:
            if self.has_target(sample):
                tx.append(sample[7])
                ty.append(sample[8])
                tz.append(sample[9])
        return tx, ty, tz

    def unique_target_points(self) -> List[Position]:
        points: List[Position] = []
        last: Optional[Position] = None
        for sample in self.samples:
            if not self.has_target(sample):
                continue
            point = (round(sample[7], 2), round(sample[8], 2), round(sample[9], 2))
            if point != last:
                points.append(point)
                last = point
        return points

    def stable_samples(self) -> List[Sample]:
        if len(self.samples) < 3:
            return self.samples
        start = len(self.samples) // 2
        return self.samples[start:]

    def flight_samples(self) -> List[Sample]:
        samples = []
        for sample in self.samples:
            if not self.has_target(sample):
                continue
            target_altitude = -sample[9]
            actual_altitude = -sample[3]
            if target_altitude <= 0.0:
                samples.append(sample)
            elif actual_altitude >= max(0.5, target_altitude * 0.5):
                samples.append(sample)
        return samples

    def error_components(self, sample: Sample) -> Tuple[float, float, float]:
        if not self.has_target(sample):
            return math.nan, math.nan, math.nan
        dx = sample[1] - sample[7]
        dy = sample[2] - sample[8]
        dz = sample[3] - sample[9]
        return math.hypot(dx, dy), dz, math.sqrt(dx * dx + dy * dy + dz * dz)

    def has_target(self, sample: Sample) -> bool:
        return not (
            math.isnan(sample[7]) or math.isnan(sample[8]) or math.isnan(sample[9])
        )

    def speed(self, sample: Sample) -> float:
        return math.sqrt(sample[4] ** 2 + sample[5] ** 2 + sample[6] ** 2)

    def final_position_text(self) -> str:
        if not self.samples:
            return "(nan, nan, nan)"
        sample = self.samples[-1]
        return f"({sample[1]:.2f}, {sample[2]:.2f}, {sample[3]:.2f})"

    def float_cell(self, value: float) -> str:
        return "" if math.isnan(value) else f"{value:.4f}"

    def metric_cell(self, value: float) -> str:
        return "nan" if math.isnan(value) else f"{value:.2f}"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TrajectoryRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.write_outputs()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
