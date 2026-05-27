import math
from typing import Optional, Tuple

import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class TagTargetPoseNode(Node):
    """Estimate a fixed ArUco target pose from the front camera stream."""

    def __init__(self) -> None:
        super().__init__("tag_target_pose_node")

        self.declare_parameter("image_topic", "/vision/front/image_raw")
        self.declare_parameter("camera_info_topic", "/vision/front/camera_info")
        self.declare_parameter("target_pose_topic", "/vision/target_pose")
        self.declare_parameter(
            "target_pose_uav_topic", "/vision/target_pose_in_uav_frame"
        )
        self.declare_parameter("camera_frame", "uav/camera_link")
        self.declare_parameter("uav_frame", "uav/base_link")
        self.declare_parameter("marker_id", 23)
        self.declare_parameter("marker_size_m", 0.5)
        self.declare_parameter("camera_xyz_in_uav_frame", [0.12, 0.0, 0.242])
        self.declare_parameter("publish_placeholder", False)
        self.declare_parameter("placeholder_period", 0.5)
        self.declare_parameter("placeholder_xyz_in_uav_frame", [2.0, 0.0, 0.5])

        self.image_topic = str(self.get_parameter("image_topic").value)
        self.camera_info_topic = str(self.get_parameter("camera_info_topic").value)
        self.target_pose_topic = str(self.get_parameter("target_pose_topic").value)
        self.target_pose_uav_topic = str(
            self.get_parameter("target_pose_uav_topic").value
        )
        self.camera_frame = str(self.get_parameter("camera_frame").value)
        self.uav_frame = str(self.get_parameter("uav_frame").value)
        self.marker_id = int(self.get_parameter("marker_id").value)
        self.marker_size_m = float(self.get_parameter("marker_size_m").value)
        self.camera_xyz_in_uav_frame = self._float_triplet_parameter(
            "camera_xyz_in_uav_frame"
        )
        self.publish_placeholder = bool(
            self.get_parameter("publish_placeholder").value
        )
        self.placeholder_period = float(self.get_parameter("placeholder_period").value)
        self.placeholder_xyz_in_uav_frame = self._float_triplet_parameter(
            "placeholder_xyz_in_uav_frame"
        )

        if self.marker_size_m <= 0.0:
            raise ValueError("marker_size_m must be positive")
        if self.placeholder_period <= 0.0:
            raise ValueError("placeholder_period must be positive")

        self.bridge = CvBridge()
        self.camera_matrix: Optional[np.ndarray] = None
        self.distortion: Optional[np.ndarray] = None
        self.detector_available = self._aruco_available()
        self.dictionary = None
        self.detector_parameters = None
        if self.detector_available:
            self.dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
            self.detector_parameters = cv2.aruco.DetectorParameters_create()

        self.target_pose_pub = self.create_publisher(
            PoseStamped, self.target_pose_topic, 10
        )
        self.target_pose_uav_pub = self.create_publisher(
            PoseStamped, self.target_pose_uav_topic, 10
        )
        self.create_subscription(
            CameraInfo, self.camera_info_topic, self.camera_info_callback, 10
        )
        self.create_subscription(Image, self.image_topic, self.image_callback, 10)

        if self.publish_placeholder:
            self.create_timer(self.placeholder_period, self.publish_placeholder_pose)

        if self.detector_available:
            self.get_logger().info(
                "Using OpenCV ArUco DICT_4X4_50 detector for marker "
                f"id={self.marker_id} size={self.marker_size_m:.3f} m"
            )
        else:
            self.get_logger().warning(
                "OpenCV ArUco detector is unavailable; enable "
                "publish_placeholder:=true to publish the documented static target."
            )

    def camera_info_callback(self, msg: CameraInfo) -> None:
        self.camera_matrix = np.array(msg.k, dtype=np.float64).reshape((3, 3))
        self.distortion = np.array(msg.d, dtype=np.float64)

    def image_callback(self, msg: Image) -> None:
        if not self.detector_available:
            return
        if self.camera_matrix is None or self.distortion is None:
            self.get_logger().debug("Waiting for camera info before tag detection.")
            return

        image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="mono8")
        corners, ids, _ = cv2.aruco.detectMarkers(
            image, self.dictionary, parameters=self.detector_parameters
        )
        if ids is None:
            return

        marker_index = self._find_marker_index(ids, self.marker_id)
        if marker_index is None:
            return

        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
            [corners[marker_index]],
            self.marker_size_m,
            self.camera_matrix,
            self.distortion,
        )
        rvec = np.asarray(rvecs[0][0], dtype=np.float64)
        tvec = np.asarray(tvecs[0][0], dtype=np.float64)
        stamp = msg.header.stamp
        self.publish_detected_pose(stamp, rvec, tvec)

    def publish_detected_pose(self, stamp, rvec: np.ndarray, tvec: np.ndarray) -> None:
        rotation_camera_target, _ = cv2.Rodrigues(rvec)
        camera_pose = PoseStamped()
        camera_pose.header.stamp = stamp
        camera_pose.header.frame_id = self.camera_frame
        camera_pose.pose.position.x = float(tvec[0])
        camera_pose.pose.position.y = float(tvec[1])
        camera_pose.pose.position.z = float(tvec[2])
        self._assign_quaternion(camera_pose, rotation_camera_target)
        self.target_pose_pub.publish(camera_pose)

        uav_pose = PoseStamped()
        uav_pose.header.stamp = stamp
        uav_pose.header.frame_id = self.uav_frame
        uav_xyz = self._camera_optical_xyz_to_uav_flu_xyz(tvec)
        uav_pose.pose.position.x = self.camera_xyz_in_uav_frame[0] + uav_xyz[0]
        uav_pose.pose.position.y = self.camera_xyz_in_uav_frame[1] + uav_xyz[1]
        uav_pose.pose.position.z = self.camera_xyz_in_uav_frame[2] + uav_xyz[2]
        rotation_uav_target = self._camera_optical_to_uav_rotation().dot(
            rotation_camera_target
        )
        self._assign_quaternion(uav_pose, rotation_uav_target)
        self.target_pose_uav_pub.publish(uav_pose)

    def publish_placeholder_pose(self) -> None:
        stamp = self.get_clock().now().to_msg()
        uav_pose = PoseStamped()
        uav_pose.header.stamp = stamp
        uav_pose.header.frame_id = self.uav_frame
        uav_pose.pose.position.x = self.placeholder_xyz_in_uav_frame[0]
        uav_pose.pose.position.y = self.placeholder_xyz_in_uav_frame[1]
        uav_pose.pose.position.z = self.placeholder_xyz_in_uav_frame[2]
        uav_pose.pose.orientation.w = 1.0
        self.target_pose_uav_pub.publish(uav_pose)

        relative = np.array(
            [
                uav_pose.pose.position.x - self.camera_xyz_in_uav_frame[0],
                uav_pose.pose.position.y - self.camera_xyz_in_uav_frame[1],
                uav_pose.pose.position.z - self.camera_xyz_in_uav_frame[2],
            ],
            dtype=np.float64,
        )
        camera_xyz = self._uav_flu_xyz_to_camera_optical_xyz(relative)
        camera_pose = PoseStamped()
        camera_pose.header.stamp = stamp
        camera_pose.header.frame_id = self.camera_frame
        camera_pose.pose.position.x = float(camera_xyz[0])
        camera_pose.pose.position.y = float(camera_xyz[1])
        camera_pose.pose.position.z = float(camera_xyz[2])
        camera_pose.pose.orientation.w = 1.0
        self.target_pose_pub.publish(camera_pose)

    @staticmethod
    def _aruco_available() -> bool:
        return all(
            hasattr(cv2, "aruco") and hasattr(cv2.aruco, name)
            for name in (
                "DICT_4X4_50",
                "Dictionary_get",
                "DetectorParameters_create",
                "detectMarkers",
                "estimatePoseSingleMarkers",
            )
        )

    @staticmethod
    def _find_marker_index(ids: np.ndarray, marker_id: int) -> Optional[int]:
        for index, value in enumerate(ids.flatten().tolist()):
            if int(value) == marker_id:
                return index
        return None

    @staticmethod
    def _camera_optical_xyz_to_uav_flu_xyz(xyz: np.ndarray) -> Tuple[float, float, float]:
        return float(xyz[2]), float(-xyz[0]), float(-xyz[1])

    @staticmethod
    def _uav_flu_xyz_to_camera_optical_xyz(xyz: np.ndarray) -> Tuple[float, float, float]:
        return float(-xyz[1]), float(-xyz[2]), float(xyz[0])

    @staticmethod
    def _camera_optical_to_uav_rotation() -> np.ndarray:
        return np.array(
            [
                [0.0, 0.0, 1.0],
                [-1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
            ],
            dtype=np.float64,
        )

    @staticmethod
    def _assign_quaternion(msg: PoseStamped, rotation: np.ndarray) -> None:
        x, y, z, w = _rotation_matrix_to_quaternion(rotation)
        msg.pose.orientation.x = x
        msg.pose.orientation.y = y
        msg.pose.orientation.z = z
        msg.pose.orientation.w = w

    def _float_triplet_parameter(self, parameter_name: str):
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValueError(f"{parameter_name} must be a length-3 list")
        return [float(item) for item in value]


def _rotation_matrix_to_quaternion(rotation: np.ndarray) -> Tuple[float, float, float, float]:
    trace = float(np.trace(rotation))
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * scale
        x = (rotation[2, 1] - rotation[1, 2]) / scale
        y = (rotation[0, 2] - rotation[2, 0]) / scale
        z = (rotation[1, 0] - rotation[0, 1]) / scale
    elif rotation[0, 0] > rotation[1, 1] and rotation[0, 0] > rotation[2, 2]:
        scale = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
        w = (rotation[2, 1] - rotation[1, 2]) / scale
        x = 0.25 * scale
        y = (rotation[0, 1] + rotation[1, 0]) / scale
        z = (rotation[0, 2] + rotation[2, 0]) / scale
    elif rotation[1, 1] > rotation[2, 2]:
        scale = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
        w = (rotation[0, 2] - rotation[2, 0]) / scale
        x = (rotation[0, 1] + rotation[1, 0]) / scale
        y = 0.25 * scale
        z = (rotation[1, 2] + rotation[2, 1]) / scale
    else:
        scale = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
        w = (rotation[1, 0] - rotation[0, 1]) / scale
        x = (rotation[0, 2] + rotation[2, 0]) / scale
        y = (rotation[1, 2] + rotation[2, 1]) / scale
        z = 0.25 * scale

    norm = math.sqrt(x * x + y * y + z * z + w * w)
    return x / norm, y / norm, z / norm, w / norm


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TagTargetPoseNode()
    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
