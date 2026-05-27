import argparse
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aerial_manip_msgs.action import Approach
from aerial_manip_msgs.msg import SystemObservation, TaskStatus
from geometry_msgs.msg import Point, PointStamped, PoseStamped
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


Vector3 = Tuple[float, float, float]


class AirReachDemo(Node):
    """Demo 10 orchestrator for hover, tag detection, approach, and endpoint hold."""

    def __init__(self, output_dir: Path) -> None:
        super().__init__("air_reach_demo")
        self.declare_parameter("hover_target_ned", [0.0, 0.0, -2.0])
        self.declare_parameter("hover_hold_sec", 2.0)
        self.declare_parameter("target_wait_sec", 10.0)
        self.declare_parameter("endpoint_hold_sec", 1.0)
        self.declare_parameter("task_timeout_sec", 45.0)
        self.declare_parameter("standoff_distance_m", 0.65)
        self.declare_parameter("max_flight_error_m", 0.55)
        self.declare_parameter("max_final_endpoint_error_m", 0.35)
        self.declare_parameter("min_target_visible_ratio", 0.20)
        self.declare_parameter("joint_min_positions", [-1.57, -1.57, -1.57])
        self.declare_parameter("joint_max_positions", [1.57, 1.57, 1.57])

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.hover_target = self._float_triplet_parameter("hover_target_ned")
        self.hover_hold_sec = float(self.get_parameter("hover_hold_sec").value)
        self.target_wait_sec = float(self.get_parameter("target_wait_sec").value)
        self.endpoint_hold_sec = float(self.get_parameter("endpoint_hold_sec").value)
        self.task_timeout_sec = float(self.get_parameter("task_timeout_sec").value)
        self.standoff_distance_m = float(
            self.get_parameter("standoff_distance_m").value
        )
        self.max_flight_error_m = float(
            self.get_parameter("max_flight_error_m").value
        )
        self.max_final_endpoint_error_m = float(
            self.get_parameter("max_final_endpoint_error_m").value
        )
        self.min_target_visible_ratio = float(
            self.get_parameter("min_target_visible_ratio").value
        )
        self.joint_min_positions = self._float_list_parameter("joint_min_positions")
        self.joint_max_positions = self._float_list_parameter("joint_max_positions")

        self.latest_position: Optional[Vector3] = None
        self.latest_target_in_uav: Optional[Vector3] = None
        self.latest_observation: Optional[SystemObservation] = None
        self.events: List[Dict[str, Any]] = []
        self.flight_errors: List[float] = []
        self.target_samples = 0
        self.visible_samples = 0
        self.joint_violations = 0
        self.final_endpoint_error = math.inf
        self.contact_detected = False
        self.start_time = time.monotonic()

        self.uav_target_pub = self.create_publisher(Point, "/uav/target_position", 10)
        self.status_pub = self.create_publisher(TaskStatus, "/task/status", 10)
        self.create_subscription(
            PointStamped, "/uav/current_position", self.position_callback, 10
        )
        self.create_subscription(
            PoseStamped,
            "/vision/target_pose_in_uav_frame",
            self.target_callback,
            10,
        )
        self.create_subscription(
            SystemObservation,
            "/system/observation",
            self.observation_callback,
            10,
        )
        self.approach_client = ActionClient(self, Approach, "/approach")

    def position_callback(self, msg: PointStamped) -> None:
        self.latest_position = (float(msg.point.x), float(msg.point.y), float(msg.point.z))

    def target_callback(self, msg: PoseStamped) -> None:
        self.latest_target_in_uav = (
            float(msg.pose.position.x),
            float(msg.pose.position.y),
            float(msg.pose.position.z),
        )

    def observation_callback(self, msg: SystemObservation) -> None:
        self.latest_observation = msg
        self.target_samples += 1
        visible = bool(msg.target_visible) or self.latest_target_in_uav is not None
        if visible:
            self.visible_samples += 1
        self.contact_detected = self.contact_detected or bool(msg.arm.contact_detected)
        for index, value in enumerate(msg.arm.joint_positions):
            if index >= len(self.joint_min_positions):
                break
            if value < self.joint_min_positions[index] or value > self.joint_max_positions[index]:
                self.joint_violations += 1

    def run(self) -> int:
        self._event("stable_hover", "commanding initial hover target")
        if not self._hold_hover():
            return self._finish("FAIL", "stable hover was not reached")

        self._event("tag_detection", "waiting for target pose")
        if not self._wait_for_target():
            return self._finish("FAIL", "target was not visible before timeout")

        target_ned = self._target_ned_from_latest()
        self._event("coordinated_approach", "sending /approach goal")
        if target_ned is None or not self._run_approach(target_ned):
            return self._finish("FAIL", "coordinated approach failed")

        self._event("endpoint_hold", "holding endpoint near target")
        self._hold_endpoint(target_ned)
        return self._finish("PASS", "ok")

    def _hold_hover(self) -> bool:
        hold_start: Optional[float] = None
        deadline = time.monotonic() + self.task_timeout_sec
        while rclpy.ok() and time.monotonic() < deadline:
            self._publish_hover_target()
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_position is None:
                hold_start = None
                continue
            error = self._distance_tuple(self.latest_position, self.hover_target)
            self.flight_errors.append(error)
            if error <= self.max_flight_error_m:
                hold_start = hold_start or time.monotonic()
                if time.monotonic() - hold_start >= self.hover_hold_sec:
                    return True
            else:
                hold_start = None
        return False

    def _wait_for_target(self) -> bool:
        deadline = time.monotonic() + self.target_wait_sec
        while rclpy.ok() and time.monotonic() < deadline:
            self._publish_hover_target()
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.latest_target_in_uav is not None:
                return True
        return False

    def _run_approach(self, target_ned: Vector3) -> bool:
        if not self.approach_client.wait_for_server(timeout_sec=5.0):
            self._event("coordinated_approach", "/approach action server unavailable")
            return False

        goal = Approach.Goal()
        goal.target_pose.header.stamp = self.get_clock().now().to_msg()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.pose.position.x = target_ned[0]
        goal.target_pose.pose.position.y = target_ned[1]
        goal.target_pose.pose.position.z = target_ned[2]
        goal.target_pose.pose.orientation.w = 1.0
        goal.standoff_distance_m = self.standoff_distance_m
        goal.timeout_sec = self.task_timeout_sec

        send_future = self.approach_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future, timeout_sec=10.0)
        if not send_future.done():
            return False
        goal_handle = send_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return False
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=self.task_timeout_sec)
        if not result_future.done():
            return False
        result = result_future.result()
        if result is None:
            return False
        return int(result.result.status.status) == int(TaskStatus.STATUS_SUCCEEDED)

    def _hold_endpoint(self, target_ned: Vector3) -> None:
        deadline = time.monotonic() + self.endpoint_hold_sec
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            endpoint = self._endpoint_ned()
            if endpoint is not None:
                self.final_endpoint_error = self._distance_tuple(endpoint, target_ned)

    def _finish(self, proposed_result: str, reason: str) -> int:
        duration = time.monotonic() - self.start_time
        timed_out = duration > self.task_timeout_sec
        visible_ratio = self.visible_samples / self.target_samples if self.target_samples else 0.0
        max_flight_error = max(self.flight_errors) if self.flight_errors else math.inf
        failures: List[str] = []
        if proposed_result != "PASS":
            failures.append(reason)
        if max_flight_error > self.max_flight_error_m:
            failures.append("flight error exceeds limit")
        if self.joint_violations:
            failures.append("joint limit violation")
        if visible_ratio < self.min_target_visible_ratio:
            failures.append("target visibility below limit")
        if timed_out:
            failures.append("task timeout")
        if self.final_endpoint_error > self.max_final_endpoint_error_m:
            failures.append("final endpoint error exceeds limit")

        result = "PASS" if not failures else "FAIL"
        final_reason = "ok" if not failures else "; ".join(failures)
        metrics = {
            "schema_version": "demo10_air_reach_metrics_v1",
            "demo": "demo10_air_reach",
            "timestamp": self.output_dir.name,
            "mode": "live",
            "sequence": [
                "stable_hover",
                "tag_detection",
                "coordinated_approach",
                "endpoint_hold",
            ],
            "flight_error": {
                "max_m": max_flight_error,
                "avg_m": sum(self.flight_errors) / len(self.flight_errors)
                if self.flight_errors
                else math.inf,
                "limit_m": self.max_flight_error_m,
            },
            "joint_limits": {
                "violations": self.joint_violations,
                "limits_rad": list(zip(self.joint_min_positions, self.joint_max_positions)),
            },
            "target_visibility": {
                "visible_samples": self.visible_samples,
                "total_samples": self.target_samples,
                "visible_ratio": visible_ratio,
                "min_visible_ratio": self.min_target_visible_ratio,
            },
            "task_timeout": {
                "duration_sec": duration,
                "limit_sec": self.task_timeout_sec,
                "timed_out": timed_out,
            },
            "final_endpoint_error": {
                "error_m": self.final_endpoint_error,
                "limit_m": self.max_final_endpoint_error_m,
                "contact_detected": self.contact_detected,
            },
            "result": result,
            "reason": final_reason,
        }
        self._write_outputs(metrics)
        self._publish_status(result, final_reason)
        return 0 if result == "PASS" else 1

    def _write_outputs(self, metrics: Dict[str, Any]) -> None:
        with (self.output_dir / "sequence_events.jsonl").open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
        (self.output_dir / "metrics.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (self.output_dir / "result.txt").write_text(
            f"RESULT={metrics['result']} reason={metrics['reason']}\n",
            encoding="utf-8",
        )
        (self.output_dir / "summary.md").write_text(
            "\n".join(
                [
                    "# Demo 10 Air Reach Summary",
                    "",
                    f"RESULT={metrics['result']} reason={metrics['reason']}",
                    f"mode: {metrics['mode']}",
                    f"max_flight_error_m: {metrics['flight_error']['max_m']:.3f}",
                    f"target_visible_ratio: {metrics['target_visibility']['visible_ratio']:.3f}",
                    f"joint_limit_violations: {metrics['joint_limits']['violations']}",
                    f"duration_sec: {metrics['task_timeout']['duration_sec']:.3f}",
                    f"final_endpoint_error_m: {metrics['final_endpoint_error']['error_m']:.3f}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def _target_ned_from_latest(self) -> Optional[Vector3]:
        if self.latest_position is None or self.latest_target_in_uav is None:
            return None
        rel = self.latest_target_in_uav
        return (
            self.latest_position[0] + rel[0],
            self.latest_position[1] - rel[1],
            self.latest_position[2] - rel[2],
        )

    def _endpoint_ned(self) -> Optional[Vector3]:
        if self.latest_observation is None:
            return None
        platform = self.latest_observation.platform.position_ned
        endpoint = self.latest_observation.arm.end_effector_pose.pose.position
        return (
            float(platform.x) + float(endpoint.x),
            float(platform.y) - float(endpoint.y),
            float(platform.z) - float(endpoint.z),
        )

    def _publish_hover_target(self) -> None:
        msg = Point()
        msg.x, msg.y, msg.z = self.hover_target
        self.uav_target_pub.publish(msg)

    def _publish_status(self, result: str, message: str) -> None:
        msg = TaskStatus()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "air_reach_demo"
        msg.task_id = "demo10_air_reach"
        msg.status = (
            TaskStatus.STATUS_SUCCEEDED if result == "PASS" else TaskStatus.STATUS_FAILED
        )
        msg.message = message
        msg.progress = 1.0
        self.status_pub.publish(msg)

    def _event(self, phase: str, message: str) -> None:
        self.events.append(
            {
                "t_sec": time.monotonic() - self.start_time,
                "event": "phase_start",
                "phase": phase,
                "message": message,
            }
        )
        self.get_logger().info(f"{phase}: {message}")

    def _float_triplet_parameter(self, name: str) -> Vector3:
        values = self._float_list_parameter(name)
        if len(values) != 3:
            raise ValueError(f"{name} must contain three values")
        return values[0], values[1], values[2]

    def _float_list_parameter(self, name: str) -> List[float]:
        value = self.get_parameter(name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{name} must be a list")
        return [float(item) for item in value]

    @staticmethod
    def _distance_tuple(left: Vector3, right: Vector3) -> float:
        return math.sqrt(
            (left[0] - right[0]) ** 2
            + (left[1] - right[1]) ** 2
            + (left[2] - right[2]) ** 2
        )


def main(args=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parsed, remaining = parser.parse_known_args(args)

    rclpy.init(args=remaining)
    node = AirReachDemo(Path(parsed.output_dir))
    exit_code = 1
    try:
        exit_code = node.run()
    except (KeyboardInterrupt, ExternalShutdownException):
        exit_code = node._finish("FAIL", "interrupted")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
