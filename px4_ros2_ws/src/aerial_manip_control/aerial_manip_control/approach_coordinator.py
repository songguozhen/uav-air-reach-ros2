import math
import time
from typing import List, Optional, Sequence, Tuple

from aerial_manip_msgs.action import Approach
from aerial_manip_msgs.msg import ArmCommand, SystemObservation, TaskStatus
from geometry_msgs.msg import Point
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool


Vector3 = Tuple[float, float, float]


class ApproachCoordinator(Node):
    """Rule-based high-level coordinator for UAV coarse approach and arm trim."""

    def __init__(self) -> None:
        super().__init__("approach_coordinator")

        self.declare_parameter("control_period", 0.1)
        self.declare_parameter("uav_command_min_interval", 0.2)
        self.declare_parameter("arm_command_min_interval", 0.2)
        self.declare_parameter("observation_timeout", 1.0)
        self.declare_parameter("default_timeout", 20.0)
        self.declare_parameter("default_standoff_distance_m", 0.7)
        self.declare_parameter("min_standoff_distance_m", 0.25)
        self.declare_parameter("max_standoff_distance_m", 3.0)
        self.declare_parameter("max_horizontal_range", 8.0)
        self.declare_parameter("min_altitude", 0.4)
        self.declare_parameter("max_altitude", 5.0)
        self.declare_parameter("max_uav_target_step", 0.5)
        self.declare_parameter("coarse_xy_tolerance", 0.25)
        self.declare_parameter("coarse_z_tolerance", 0.20)
        self.declare_parameter("arm_reach_tolerance", 0.18)
        self.declare_parameter("arm_hold_time", 0.5)
        self.declare_parameter("joint_names", ["joint1", "joint2", "joint3"])
        self.declare_parameter("arm_stow_on_cancel", True)
        self.declare_parameter("arm_home_positions", [0.0, 0.0, 0.0])
        self.declare_parameter("min_joint_positions", [-1.57, -1.57, -1.57])
        self.declare_parameter("max_joint_positions", [1.57, 1.57, 1.57])
        self.declare_parameter("max_arm_joint_step", 0.20)
        self.declare_parameter("arm_forward_gain", 0.35)
        self.declare_parameter("arm_lateral_gain", 0.45)
        self.declare_parameter("arm_vertical_gain", -0.35)

        self.control_period = float(self.get_parameter("control_period").value)
        self.uav_command_min_interval = float(
            self.get_parameter("uav_command_min_interval").value
        )
        self.arm_command_min_interval = float(
            self.get_parameter("arm_command_min_interval").value
        )
        self.observation_timeout = float(
            self.get_parameter("observation_timeout").value
        )
        self.default_timeout = float(self.get_parameter("default_timeout").value)
        self.default_standoff_distance_m = float(
            self.get_parameter("default_standoff_distance_m").value
        )
        self.min_standoff_distance_m = float(
            self.get_parameter("min_standoff_distance_m").value
        )
        self.max_standoff_distance_m = float(
            self.get_parameter("max_standoff_distance_m").value
        )
        self.max_horizontal_range = float(
            self.get_parameter("max_horizontal_range").value
        )
        self.min_altitude = float(self.get_parameter("min_altitude").value)
        self.max_altitude = float(self.get_parameter("max_altitude").value)
        self.max_uav_target_step = float(
            self.get_parameter("max_uav_target_step").value
        )
        self.coarse_xy_tolerance = float(
            self.get_parameter("coarse_xy_tolerance").value
        )
        self.coarse_z_tolerance = float(self.get_parameter("coarse_z_tolerance").value)
        self.arm_reach_tolerance = float(
            self.get_parameter("arm_reach_tolerance").value
        )
        self.arm_hold_time = float(self.get_parameter("arm_hold_time").value)
        self.joint_names = self._string_list_parameter("joint_names")
        self.arm_stow_on_cancel = bool(self.get_parameter("arm_stow_on_cancel").value)
        self.arm_home_positions = self._float_list_parameter("arm_home_positions")
        self.min_joint_positions = self._float_list_parameter("min_joint_positions")
        self.max_joint_positions = self._float_list_parameter("max_joint_positions")
        self.max_arm_joint_step = float(self.get_parameter("max_arm_joint_step").value)
        self.arm_forward_gain = float(self.get_parameter("arm_forward_gain").value)
        self.arm_lateral_gain = float(self.get_parameter("arm_lateral_gain").value)
        self.arm_vertical_gain = float(self.get_parameter("arm_vertical_gain").value)

        self._validate_config()

        self.latest_observation: Optional[SystemObservation] = None
        self.last_observation_time = 0.0
        self.last_uav_command_time = 0.0
        self.last_arm_command_time = 0.0
        self.last_uav_target: Optional[Vector3] = None
        self.stop_requested = False

        self.callback_group = ReentrantCallbackGroup()
        self.uav_target_pub = self.create_publisher(Point, "/uav/target_position", 10)
        self.arm_target_pub = self.create_publisher(ArmCommand, "/arm/target_joints", 10)
        self.create_subscription(
            SystemObservation,
            "/system/observation",
            self.observation_callback,
            10,
            callback_group=self.callback_group,
        )
        self.create_subscription(
            Bool,
            "/approach_coordinator/stop",
            self.stop_callback,
            10,
            callback_group=self.callback_group,
        )
        self.action_server = ActionServer(
            self,
            Approach,
            "/approach",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group,
        )
        self.get_logger().info(
            "Approach coordinator ready on /approach; commands are limited to "
            "/uav/target_position and /arm/target_joints"
        )

    def goal_callback(self, goal_request: Approach.Goal) -> GoalResponse:
        target = self._pose_to_xyz(goal_request.target_pose.pose.position)
        standoff = self._requested_standoff(goal_request.standoff_distance_m)
        error = self._validate_workspace_target(target, standoff)
        if error is not None:
            self.get_logger().warn(f"Rejected /approach goal: {error}")
            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    def cancel_callback(self, _goal_handle) -> CancelResponse:
        self.stop_requested = True
        self._publish_stop_commands()
        return CancelResponse.ACCEPT

    def stop_callback(self, msg: Bool) -> None:
        if not msg.data:
            return
        self.stop_requested = True
        self._publish_stop_commands()
        self.get_logger().warn("Stop requested on /approach_coordinator/stop")

    def observation_callback(self, msg: SystemObservation) -> None:
        self.latest_observation = msg
        self.last_observation_time = time.monotonic()

    def execute_callback(self, goal_handle):
        self.stop_requested = False
        goal = goal_handle.request
        target = self._pose_to_xyz(goal.target_pose.pose.position)
        standoff = self._requested_standoff(goal.standoff_distance_m)
        timeout = self._requested_timeout(goal.timeout_sec)
        start_time = time.monotonic()
        hold_start: Optional[float] = None
        phase = "WAITING_FOR_STATE"
        message = "waiting for /system/observation"

        while rclpy.ok():
            now = time.monotonic()
            elapsed = now - start_time
            observation = self._fresh_observation(now)

            if self.stop_requested or goal_handle.is_cancel_requested:
                self._publish_stop_commands()
                goal_handle.canceled()
                return self._result(
                    TaskStatus.STATUS_ABORTED,
                    "approach canceled or stopped",
                    observation,
                )

            if elapsed > timeout:
                self._publish_stop_commands()
                goal_handle.abort()
                return self._result(
                    TaskStatus.STATUS_FAILED,
                    f"approach timed out after {timeout:.1f}s",
                    observation,
                )

            if observation is None:
                self._publish_feedback(
                    goal_handle, TaskStatus.STATUS_RUNNING, message, 0.0, 0.0, None
                )
                time.sleep(self.control_period)
                continue

            current = self._pose_to_xyz(observation.platform.position_ned)
            coarse_target = self._coarse_uav_target(current, target, standoff)
            coarse_error = self._distance(current, coarse_target)
            coarse_reached = self._coarse_reached(current, coarse_target)

            if not coarse_reached:
                phase = "COARSE_UAV_APPROACH"
                message = "commanding coarse UAV standoff target"
                self._publish_uav_target(coarse_target, now)
                hold_start = None
            else:
                phase = "LOCAL_ARM_ADJUST"
                residual = self._subtract(target, current)
                arm_target = self._arm_target_from_residual(observation, residual)
                self._publish_uav_target(coarse_target, now)
                self._publish_arm_target(arm_target, now)
                local_error = self._arm_local_error(residual, standoff)
                message = "commanding local arm adjustment"
                if local_error <= self.arm_reach_tolerance:
                    if hold_start is None:
                        hold_start = now
                    if now - hold_start >= self.arm_hold_time:
                        goal_handle.succeed()
                        return self._result(
                            TaskStatus.STATUS_SUCCEEDED,
                            "approach target reached",
                            observation,
                        )
                else:
                    hold_start = None

            remaining = self._remaining_distance(observation, target, standoff)
            progress = self._progress(elapsed, timeout, coarse_error)
            self._publish_feedback(
                goal_handle,
                TaskStatus.STATUS_RUNNING,
                f"{phase}: {message}",
                progress,
                remaining,
                observation,
            )
            time.sleep(self.control_period)

        goal_handle.abort()
        return self._result(
            TaskStatus.STATUS_FAILED,
            "rclpy shutdown during approach",
            self.latest_observation,
        )

    def _coarse_uav_target(
        self, current: Vector3, target: Vector3, standoff: float
    ) -> Vector3:
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        horizontal = math.hypot(dx, dy)
        if horizontal > 1.0e-6:
            ux = dx / horizontal
            uy = dy / horizontal
        else:
            ux = 1.0
            uy = 0.0

        raw_target = (
            target[0] - ux * standoff,
            target[1] - uy * standoff,
            target[2],
        )
        stepped_target = self._limit_step(current, raw_target, self.max_uav_target_step)
        return self._clamp_uav_workspace(stepped_target)

    def _arm_target_from_residual(
        self, observation: SystemObservation, residual: Vector3
    ) -> List[float]:
        current = list(observation.arm.joint_positions)
        if len(current) != len(self.joint_names):
            current = list(self.arm_home_positions)

        target = list(current)
        if len(target) >= 1:
            target[0] += self.arm_lateral_gain * residual[1]
        if len(target) >= 2:
            target[1] += self.arm_forward_gain * residual[0]
        if len(target) >= 3:
            target[2] += self.arm_vertical_gain * residual[2]

        stepped = [
            current_value
            + max(
                -self.max_arm_joint_step,
                min(self.max_arm_joint_step, target_value - current_value),
            )
            for current_value, target_value in zip(current, target)
        ]
        return [
            max(min_limit, min(max_limit, value))
            for value, min_limit, max_limit in zip(
                stepped, self.min_joint_positions, self.max_joint_positions
            )
        ]

    def _publish_uav_target(self, target: Vector3, now: float) -> None:
        if now - self.last_uav_command_time < self.uav_command_min_interval:
            return

        msg = Point()
        msg.x = target[0]
        msg.y = target[1]
        msg.z = target[2]
        self.uav_target_pub.publish(msg)
        self.last_uav_target = target
        self.last_uav_command_time = now

    def _publish_arm_target(self, joint_positions: Sequence[float], now: float) -> None:
        if now - self.last_arm_command_time < self.arm_command_min_interval:
            return

        msg = ArmCommand()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "arm_base"
        msg.command_mode = ArmCommand.MODE_JOINT_POSITION
        msg.joint_names = list(self.joint_names)
        msg.joint_positions = [float(value) for value in joint_positions]
        msg.joint_velocities = [0.0] * len(self.joint_names)
        msg.joint_efforts = [0.0] * len(self.joint_names)
        self.arm_target_pub.publish(msg)
        self.last_arm_command_time = now

    def _publish_stop_commands(self) -> None:
        observation = self.latest_observation
        if observation is not None:
            current = observation.platform.position_ned
            hold = self._clamp_uav_workspace((current.x, current.y, current.z))
            msg = Point()
            msg.x, msg.y, msg.z = hold
            self.uav_target_pub.publish(msg)

        arm_msg = ArmCommand()
        arm_msg.header.stamp = self.get_clock().now().to_msg()
        arm_msg.header.frame_id = "arm_base"
        arm_msg.command_mode = (
            ArmCommand.MODE_STOW if self.arm_stow_on_cancel else ArmCommand.MODE_HOLD
        )
        arm_msg.joint_names = list(self.joint_names)
        arm_msg.joint_positions = []
        arm_msg.joint_velocities = []
        arm_msg.joint_efforts = []
        self.arm_target_pub.publish(arm_msg)

    def _publish_feedback(
        self,
        goal_handle,
        status_code: int,
        message: str,
        progress: float,
        remaining_distance: float,
        observation: Optional[SystemObservation],
    ) -> None:
        feedback = Approach.Feedback()
        feedback.status = self._task_status(status_code, message, progress)
        if observation is not None:
            feedback.current_observation = observation
        feedback.remaining_distance_m = float(max(0.0, remaining_distance))
        goal_handle.publish_feedback(feedback)

    def _result(
        self,
        status_code: int,
        message: str,
        observation: Optional[SystemObservation],
    ) -> Approach.Result:
        result = Approach.Result()
        result.status = self._task_status(status_code, message, 1.0)
        if observation is not None:
            result.final_observation = observation
        return result

    def _task_status(self, status_code: int, message: str, progress: float) -> TaskStatus:
        status = TaskStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = "approach_coordinator"
        status.task_id = "approach"
        status.status = status_code
        status.message = message
        status.progress = float(max(0.0, min(1.0, progress)))
        return status

    def _fresh_observation(self, now: float) -> Optional[SystemObservation]:
        if self.latest_observation is None:
            return None
        if now - self.last_observation_time > self.observation_timeout:
            return None
        return self.latest_observation

    def _remaining_distance(
        self, observation: SystemObservation, target: Vector3, standoff: float
    ) -> float:
        current = self._pose_to_xyz(observation.platform.position_ned)
        coarse = self._coarse_uav_target(current, target, standoff)
        if not self._coarse_reached(current, coarse):
            return self._distance(current, coarse)
        residual = self._subtract(target, current)
        return self._arm_local_error(residual, standoff)

    def _arm_local_error(self, residual: Vector3, standoff: float) -> float:
        expected = max(0.0, math.hypot(residual[0], residual[1]) - standoff)
        return math.sqrt(expected * expected + residual[2] * residual[2])

    def _progress(self, elapsed: float, timeout: float, coarse_error: float) -> float:
        time_progress = min(0.95, elapsed / max(timeout, 1.0))
        coarse_progress = 1.0 / (1.0 + max(0.0, coarse_error))
        return max(0.0, min(0.95, 0.5 * time_progress + 0.5 * coarse_progress))

    def _coarse_reached(self, current: Vector3, target: Vector3) -> bool:
        horizontal_error = math.hypot(current[0] - target[0], current[1] - target[1])
        z_error = abs(current[2] - target[2])
        return (
            horizontal_error <= self.coarse_xy_tolerance
            and z_error <= self.coarse_z_tolerance
        )

    def _validate_workspace_target(
        self, target: Vector3, standoff: float
    ) -> Optional[str]:
        if not all(math.isfinite(value) for value in target):
            return "target pose contains non-finite values"
        if standoff < self.min_standoff_distance_m:
            return "standoff_distance_m is below min_standoff_distance_m"
        if standoff > self.max_standoff_distance_m:
            return "standoff_distance_m exceeds max_standoff_distance_m"
        horizontal = math.hypot(target[0], target[1])
        if horizontal > self.max_horizontal_range:
            return "target pose exceeds max_horizontal_range"
        altitude = -target[2]
        if altitude < self.min_altitude or altitude > self.max_altitude:
            return "target pose altitude is outside configured limits"
        return None

    def _clamp_uav_workspace(self, point: Vector3) -> Vector3:
        x, y, z = point
        horizontal = math.hypot(x, y)
        if horizontal > self.max_horizontal_range:
            scale = self.max_horizontal_range / horizontal
            x *= scale
            y *= scale
        altitude = max(self.min_altitude, min(self.max_altitude, -z))
        return x, y, -altitude

    @staticmethod
    def _limit_step(current: Vector3, target: Vector3, limit: float) -> Vector3:
        delta = (
            target[0] - current[0],
            target[1] - current[1],
            target[2] - current[2],
        )
        distance = math.sqrt(delta[0] ** 2 + delta[1] ** 2 + delta[2] ** 2)
        if distance <= limit or distance <= 1.0e-9:
            return target
        scale = limit / distance
        return (
            current[0] + delta[0] * scale,
            current[1] + delta[1] * scale,
            current[2] + delta[2] * scale,
        )

    def _requested_standoff(self, requested: float) -> float:
        if requested > 0.0 and math.isfinite(requested):
            return float(requested)
        return self.default_standoff_distance_m

    def _requested_timeout(self, requested: float) -> float:
        if requested > 0.0 and math.isfinite(requested):
            return float(requested)
        return self.default_timeout

    def _validate_config(self) -> None:
        positive_parameters = {
            "control_period": self.control_period,
            "uav_command_min_interval": self.uav_command_min_interval,
            "arm_command_min_interval": self.arm_command_min_interval,
            "observation_timeout": self.observation_timeout,
            "default_timeout": self.default_timeout,
            "default_standoff_distance_m": self.default_standoff_distance_m,
            "min_standoff_distance_m": self.min_standoff_distance_m,
            "max_standoff_distance_m": self.max_standoff_distance_m,
            "max_horizontal_range": self.max_horizontal_range,
            "min_altitude": self.min_altitude,
            "max_altitude": self.max_altitude,
            "max_uav_target_step": self.max_uav_target_step,
            "coarse_xy_tolerance": self.coarse_xy_tolerance,
            "coarse_z_tolerance": self.coarse_z_tolerance,
            "arm_reach_tolerance": self.arm_reach_tolerance,
            "arm_hold_time": self.arm_hold_time,
            "max_arm_joint_step": self.max_arm_joint_step,
        }
        for name, value in positive_parameters.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive")

        if self.min_standoff_distance_m > self.max_standoff_distance_m:
            raise ValueError("min_standoff_distance_m exceeds max")
        if self.min_altitude > self.max_altitude:
            raise ValueError("min_altitude exceeds max_altitude")
        if not self.joint_names:
            raise ValueError("joint_names must not be empty")
        if len(set(self.joint_names)) != len(self.joint_names):
            raise ValueError("joint_names must be unique")
        expected = len(self.joint_names)
        for name, values in (
            ("arm_home_positions", self.arm_home_positions),
            ("min_joint_positions", self.min_joint_positions),
            ("max_joint_positions", self.max_joint_positions),
        ):
            if len(values) != expected:
                raise ValueError(f"{name} length must match joint_names")
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"{name} contains non-finite values")
        for joint, min_value, max_value in zip(
            self.joint_names, self.min_joint_positions, self.max_joint_positions
        ):
            if min_value > max_value:
                raise ValueError(f"{joint} min_joint_position exceeds max")

    def _string_list_parameter(self, parameter_name: str) -> List[str]:
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{parameter_name} must be a list")
        return [str(item) for item in value]

    def _float_list_parameter(self, parameter_name: str) -> List[float]:
        value = self.get_parameter(parameter_name).value
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{parameter_name} must be a list")
        return [float(item) for item in value]

    @staticmethod
    def _pose_to_xyz(point) -> Vector3:
        return float(point.x), float(point.y), float(point.z)

    @staticmethod
    def _subtract(left: Vector3, right: Vector3) -> Vector3:
        return left[0] - right[0], left[1] - right[1], left[2] - right[2]

    @staticmethod
    def _distance(left: Vector3, right: Vector3) -> float:
        return math.sqrt(
            (left[0] - right[0]) ** 2
            + (left[1] - right[1]) ** 2
            + (left[2] - right[2]) ** 2
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ApproachCoordinator()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
