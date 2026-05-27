import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aerial_manip_msgs.msg import ArmCommand, SystemObservation, TaskStatus
from geometry_msgs.msg import Point
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image


class JsonlWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = path.open("a", encoding="utf-8")

    def write(self, record: Dict[str, Any]) -> None:
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


class EpisodeRecorder(Node):
    """Record stage-2 ROS evidence for later LeRobot-style export."""

    def __init__(self) -> None:
        super().__init__("episode_recorder")

        self.declare_parameter("demo_name", "stage2_air_reach")
        self.declare_parameter("episode_id", "")
        self.declare_parameter("task_label", "air_reach")
        self.declare_parameter("task_id", "")
        self.declare_parameter("logs_root", "logs")
        self.declare_parameter("timestamp", "")
        self.declare_parameter("image_topics", ["/camera/image_raw"])
        self.declare_parameter("max_image_bytes", 0)

        self.demo_name = str(self.get_parameter("demo_name").value)
        self.task_label = str(self.get_parameter("task_label").value)
        self.task_id = str(self.get_parameter("task_id").value)
        logs_root = Path(str(self.get_parameter("logs_root").value))
        timestamp = str(self.get_parameter("timestamp").value) or time.strftime(
            "%Y%m%d_%H%M%S"
        )
        self.episode_id = str(self.get_parameter("episode_id").value) or timestamp
        self.max_image_bytes = int(self.get_parameter("max_image_bytes").value)
        self.image_topics = self._string_list_parameter("image_topics")

        if not self.demo_name:
            raise ValueError("demo_name must not be empty")
        if self.max_image_bytes < 0:
            raise ValueError("max_image_bytes must be non-negative")

        self.run_dir = logs_root / self.demo_name / timestamp
        self.episode_dir = self.run_dir / "episodes" / self.episode_id
        self.image_dir = self.episode_dir / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

        self.started_wall_time = time.time()
        self.last_status: Optional[TaskStatus] = None
        self.image_counts: Dict[str, int] = {}
        self.writers = {
            "observations": JsonlWriter(self.episode_dir / "observations.jsonl"),
            "actions": JsonlWriter(self.episode_dir / "actions.jsonl"),
            "task_status": JsonlWriter(self.episode_dir / "task_status.jsonl"),
            "images": JsonlWriter(self.episode_dir / "images.jsonl"),
        }
        self._write_metadata()

        self.create_subscription(
            SystemObservation,
            "/system/observation",
            self.observation_callback,
            10,
        )
        self.create_subscription(Point, "/uav/target_position", self.uav_callback, 10)
        self.create_subscription(
            ArmCommand, "/arm/target_joints", self.arm_callback, 10
        )
        self.create_subscription(TaskStatus, "/task/status", self.status_callback, 10)

        for topic in self.image_topics:
            self.image_counts[topic] = 0
            self.create_subscription(
                Image,
                topic,
                lambda msg, topic_name=topic: self.image_callback(topic_name, msg),
                10,
            )

        self.get_logger().info(
            f"Recording episode {self.episode_id} under {self.episode_dir}"
        )

    def observation_callback(self, msg: SystemObservation) -> None:
        self.writers["observations"].write(
            {
                "receipt_time_sec": time.time(),
                "stamp_sec": self._stamp_to_float(msg.header.stamp),
                "frame_id": msg.header.frame_id,
                "task_label": self.task_label,
                "task_id": self.task_id,
                "phase": msg.phase,
                "platform": {
                    "position_ned": self._point(msg.platform.position_ned),
                    "velocity_ned": self._vector3(msg.platform.velocity_ned),
                    "yaw_rad": float(msg.platform.yaw_rad),
                    "armed": bool(msg.platform.armed),
                    "nav_state": msg.platform.nav_state,
                },
                "arm": {
                    "joint_names": list(msg.arm.joint_names),
                    "joint_positions": list(msg.arm.joint_positions),
                    "joint_velocities": list(msg.arm.joint_velocities),
                    "joint_efforts": list(msg.arm.joint_efforts),
                    "end_effector_position": self._point(
                        msg.arm.end_effector_pose.pose.position
                    ),
                    "contact_detected": bool(msg.arm.contact_detected),
                    "state": msg.arm.state,
                },
                "target": {
                    "visible": bool(msg.target_visible),
                    "position": self._point(msg.target_pose.pose.position),
                },
            }
        )

    def uav_callback(self, msg: Point) -> None:
        self.writers["actions"].write(
            {
                "receipt_time_sec": time.time(),
                "source_topic": "/uav/target_position",
                "action_type": "uav_target_position_ned",
                "task_label": self.task_label,
                "task_id": self.task_id,
                "target_position_ned": self._point(msg),
            }
        )

    def arm_callback(self, msg: ArmCommand) -> None:
        self.writers["actions"].write(
            {
                "receipt_time_sec": time.time(),
                "stamp_sec": self._stamp_to_float(msg.header.stamp),
                "source_topic": "/arm/target_joints",
                "action_type": "arm_command",
                "task_label": self.task_label,
                "task_id": self.task_id,
                "command_mode": msg.command_mode,
                "joint_names": list(msg.joint_names),
                "joint_positions": list(msg.joint_positions),
                "joint_velocities": list(msg.joint_velocities),
                "joint_efforts": list(msg.joint_efforts),
            }
        )

    def status_callback(self, msg: TaskStatus) -> None:
        self.last_status = msg
        self.writers["task_status"].write(self._task_status_record(msg))
        if msg.status in (
            TaskStatus.STATUS_SUCCEEDED,
            TaskStatus.STATUS_FAILED,
            TaskStatus.STATUS_ABORTED,
        ):
            self._write_result(msg)

    def image_callback(self, topic: str, msg: Image) -> None:
        index = self.image_counts[topic]
        self.image_counts[topic] = index + 1
        topic_slug = self._slug(topic)
        suffix = self._image_suffix(msg.encoding)
        relative_path = Path("images") / topic_slug / f"{index:06d}{suffix}"
        image_path = self.episode_dir / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)

        raw = bytes(msg.data)
        truncated = False
        if self.max_image_bytes and len(raw) > self.max_image_bytes:
            raw = raw[: self.max_image_bytes]
            truncated = True
        image_path.write_bytes(raw)

        self.writers["images"].write(
            {
                "receipt_time_sec": time.time(),
                "stamp_sec": self._stamp_to_float(msg.header.stamp),
                "source_topic": topic,
                "relative_path": relative_path.as_posix(),
                "height": int(msg.height),
                "width": int(msg.width),
                "encoding": msg.encoding,
                "is_bigendian": int(msg.is_bigendian),
                "step": int(msg.step),
                "bytes": len(raw),
                "truncated": truncated,
            }
        )

    def destroy_node(self) -> bool:
        if self.last_status is None:
            self._write_result(None)
        for writer in self.writers.values():
            writer.close()
        return super().destroy_node()

    def _write_metadata(self) -> None:
        metadata = {
            "schema_version": "air_reach_episode_v1",
            "episode_id": self.episode_id,
            "demo_name": self.demo_name,
            "task_label": self.task_label,
            "task_id": self.task_id,
            "started_wall_time_sec": self.started_wall_time,
            "topics": {
                "observation": "/system/observation",
                "uav_action": "/uav/target_position",
                "arm_action": "/arm/target_joints",
                "task_status": "/task/status",
                "images": self.image_topics,
            },
            "coordinate_frame": "PX4 local NED for UAV positions; z is down",
        }
        (self.episode_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_result(self, msg: Optional[TaskStatus]) -> None:
        if msg is None:
            result = {
                "status": "unknown",
                "status_code": int(TaskStatus.STATUS_UNKNOWN),
                "message": "recorder stopped before terminal task status",
                "progress": 0.0,
                "task_id": self.task_id,
                "task_label": self.task_label,
                "finished_wall_time_sec": time.time(),
            }
        else:
            result = self._task_status_record(msg)
            result["finished_wall_time_sec"] = time.time()
        (self.episode_dir / "result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _task_status_record(self, msg: TaskStatus) -> Dict[str, Any]:
        return {
            "receipt_time_sec": time.time(),
            "stamp_sec": self._stamp_to_float(msg.header.stamp),
            "task_id": msg.task_id or self.task_id,
            "task_label": self.task_label,
            "status": self._status_name(msg.status),
            "status_code": int(msg.status),
            "message": msg.message,
            "progress": float(msg.progress),
        }

    def _string_list_parameter(self, name: str) -> List[str]:
        value = self.get_parameter(name).value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(item) for item in value]

    @staticmethod
    def _stamp_to_float(stamp) -> float:
        return float(stamp.sec) + float(stamp.nanosec) / 1_000_000_000.0

    @staticmethod
    def _point(point) -> Dict[str, float]:
        return {"x": float(point.x), "y": float(point.y), "z": float(point.z)}

    @staticmethod
    def _vector3(vector) -> Dict[str, float]:
        return {"x": float(vector.x), "y": float(vector.y), "z": float(vector.z)}

    @staticmethod
    def _status_name(status: int) -> str:
        names = {
            TaskStatus.STATUS_UNKNOWN: "unknown",
            TaskStatus.STATUS_RUNNING: "running",
            TaskStatus.STATUS_SUCCEEDED: "succeeded",
            TaskStatus.STATUS_FAILED: "failed",
            TaskStatus.STATUS_ABORTED: "aborted",
        }
        return names.get(int(status), f"status_{int(status)}")

    @staticmethod
    def _slug(topic: str) -> str:
        return topic.strip("/").replace("/", "__") or "image"

    @staticmethod
    def _image_suffix(encoding: str) -> str:
        if encoding.lower() in {"jpeg", "jpg"}:
            return ".jpg"
        if encoding.lower() == "png":
            return ".png"
        return ".raw"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EpisodeRecorder()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
