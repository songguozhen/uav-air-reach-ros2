# PX4 ROS 2 Basic Control Demos

本文档对应 4 个基础控制展示 demo：

```text
Demo 01 Hover
Demo 02 Waypoint Flight
Demo 03 Circle Trajectory
Demo 04 External Setpoint Interface
```

脚本目录：

```text
/home/clcwork/UAV_capture/px4_ros2_ws/scripts/
```

ROS 2 节点目录：

```text
src/px4_offboard_hover/px4_offboard_hover/
```

## Build

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Unified Outputs

每次执行 demo 都会创建独立的时间戳目录：

```text
logs/<demo>/<timestamp>/
visualizations/<demo>/<timestamp>/
```

每个 demo 自动输出：

```text
trajectory.csv
trajectory_3d.png
xy_path.png
height_curve.png
speed_curve.png
tracking_error.png
trajectory.mp4
summary.md
result.txt
```

`result.txt` 和 `summary.md` 都会写入：

```text
RESULT=PASS
```

或：

```text
RESULT=FAIL
```

视频使用 conda 的 LeRobot 环境里的 ffmpeg。脚本只把下面目录加入 `PATH`，不会切换 ROS Python：

```text
/home/clcwork/miniconda3/envs/lerobot/bin
```

如果 conda 路径变化：

```bash
CONDA_ENV_DIR=/path/to/conda/env ./scripts/run_demo01_hover.sh
```

## Implementation Record

本次把基础控制 demo 从“只运行控制逻辑”整理成“可展示成果”：

- Demo01-04 都接入统一的 `trajectory_recorder`。
- 每次运行单独创建 `visualizations/<demo>/<timestamp>/`，不会覆盖上一次结果。
- 每个 demo 都自动生成 CSV、5 张分析图、1 个 MP4 视频、`summary.md` 和 `result.txt`。
- `result.txt` 提供机器可读的 `RESULT=PASS/FAIL`，`summary.md` 提供面向展示和复盘的指标摘要。
- Demo04 保留 `/uav/target_position` 外部目标点接口，同时展示脚本会自动发布一组目标点，方便直接演示外部任务规划器接入效果。

能实现的能力：

- PX4 SITL 中自动起飞、进入 Offboard、执行位置控制并降落。
- 用图表展示无人机实际做了什么，而不只看终端日志。
- 对高度、速度、轨迹跟踪误差、航点覆盖、圆轨迹误差、外部目标点跟踪效果做自动评估。
- 给 LeRobot 或任务规划器提供一个简单接口：只发布 `/uav/target_position`，不需要直接操作 PX4 `/fmu/in/*` 话题。

## Run All Demos

先构建：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select px4_offboard_hover
source install/setup.bash
```

逐个运行：

```bash
./scripts/run_demo01_hover.sh
./scripts/run_demo02_waypoint_flight.sh
./scripts/run_demo03_circle_trajectory.sh
./scripts/run_demo04_external_setpoint.sh
```

每个脚本会自动启动 PX4 SITL、Micro XRCE-DDS Agent、控制节点和轨迹记录器。脚本结束时会打印本次生成文件的绝对路径，包括：

```text
trajectory_csv=<absolute path>/trajectory.csv
trajectory_3d=<absolute path>/trajectory_3d.png
xy_path=<absolute path>/xy_path.png
height_curve=<absolute path>/height_curve.png
speed_curve=<absolute path>/speed_curve.png
tracking_error=<absolute path>/tracking_error.png
video=<absolute path>/trajectory.mp4
summary=<absolute path>/summary.md
result=<absolute path>/result.txt
```

实验完成后清理后台会话：

```bash
./scripts/stop_stack.sh
```

## Latest Verified Run

验证日期：2026-05-26。

这次已经实际运行 Demo01-04，全部生成完整展示文件并得到 `RESULT=PASS`。

Demo01 Hover：

```text
visuals=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo01_hover/20260526_221722
video=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo01_hover/20260526_221722/trajectory.mp4
RESULT=PASS reason=ok
samples=1369
max_speed_mps=1.07
stable_avg_error_3d_m=0.02
stable_avg_height_error_m=0.01
stable_max_speed_mps=0.03
```

效果：无人机起飞到约 2 米高度后悬停，`height_curve.png` 能看到高度稳定在目标附近，`speed_curve.png` 和 `tracking_error.png` 能看到稳定段速度和误差都很低。

Demo02 Waypoint Flight：

```text
visuals=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo02_waypoint_flight/20260526_222121
video=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo02_waypoint_flight/20260526_222121/trajectory.mp4
RESULT=PASS reason=ok
samples=3784
max_speed_mps=2.05
flight_avg_error_3d_m=0.58
flight_avg_error_xy_m=0.45
flight_avg_height_error_m=0.16
target_point_count=4
```

效果：无人机按 `(0,0,-2) -> (2,0,-2) -> (2,2,-2) -> (0,0,-2)` 飞行，`xy_path.png` 展示航点折线和实际轨迹，`trajectory_3d.png` 展示三维飞行路径。

Demo03 Circle Trajectory：

```text
visuals=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo03_circle_trajectory/20260526_222313
video=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo03_circle_trajectory/20260526_222313/trajectory.mp4
RESULT=PASS reason=ok
samples=3493
max_speed_mps=2.06
flight_avg_error_3d_m=0.55
flight_avg_error_xy_m=0.53
flight_avg_height_error_m=0.06
flight_circle_radius_error_avg_m=0.06
```

效果：无人机在固定高度绕圆飞行，`xy_path.png` 中可以对比期望圆轨迹和实际轨迹，`tracking_error.png` 展示圆轨迹跟踪误差。

Demo04 External Setpoint Interface：

```text
visuals=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo04_external_setpoint/20260526_222502
video=/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo04_external_setpoint/20260526_222502/trajectory.mp4
RESULT=PASS reason=ok
samples=5727
max_speed_mps=1.47
avg_error_3d_m=0.20
final_error_3d_m=0.01
flight_avg_error_3d_m=0.12
target_point_count=5
```

效果：脚本自动向 `/uav/target_position` 发布目标点序列，无人机跟随外部目标移动。后续 LeRobot 或任务规划器只需要发布这个 topic，就可以驱动无人机目标位置变化。

## Demo 01: Hover

展示目标：

- 高度曲线：目标高度 vs 实际高度。
- 速度曲线：悬停过程速度变化。
- 悬停稳定性：`tracking_error.png` 展示相对悬停点的误差。

运行：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo01_hover.sh
```

默认参数：

```text
ALTITUDE=2.0
VIS_DURATION=30.0
HOVER_DURATION=35.0
```

PASS 默认判定：

- 有足够有效定位样本。
- 稳定段平均高度误差不超过 `0.35 m`。
- 稳定段平均 3D 跟踪误差不超过 `0.8 m`。
- 最大速度不超过 `3.0 m/s`。

## Demo 02: Waypoint Flight

目标航点使用 PX4 本地 NED 坐标：

```text
(0,0,-2) -> (2,0,-2) -> (2,2,-2) -> (0,0,-2)
```

展示目标：

- `xy_path.png`：XY 航点折线和实际轨迹。
- `trajectory_3d.png`：3D 航点轨迹和实际飞行轨迹。

运行：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo02_waypoint_flight.sh
```

PASS 默认判定：

- 有足够有效定位样本。
- 记录到 4 个目标航点。
- 平均 3D 跟踪误差不超过 `0.8 m`。
- 最大速度不超过 `3.0 m/s`。

## Demo 03: Circle Trajectory

无人机在固定高度绕圆飞行。默认参数：

```text
center=(0,0)
radius=1.5 m
altitude=2.0 m, NED z=-2.0
angular_speed=0.35 rad/s
duration=60.0 s
```

展示目标：

- `xy_path.png`：期望圆轨迹 vs 实际轨迹。
- `trajectory_3d.png`：固定高度绕圆的 3D 轨迹。
- `tracking_error.png`：圆轨迹跟踪误差。

运行：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo03_circle_trajectory.sh
```

可调参数：

```bash
RADIUS=2.0 ALTITUDE=2.5 DURATION=90.0 ANGULAR_SPEED=0.25 \
  ./scripts/run_demo03_circle_trajectory.sh
```

PASS 默认判定：

- 有足够有效定位样本。
- 平均圆半径误差不超过 `0.6 m`。
- 平均高度误差不超过 `0.35 m`。
- 最大速度不超过 `3.0 m/s`。

## Demo 04: External Setpoint Interface

该 demo 把目标点封装成 ROS 2 topic：

```text
/uav/target_position
```

消息类型：

```text
geometry_msgs/msg/Point
```

字段含义是 PX4 本地 NED 坐标：

```text
x: forward, meter
y: right, meter
z: down, meter
```

高度 2 米对应：

```text
z=-2.0
```

运行：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo04_external_setpoint.sh
```

展示脚本会自动发布一组外部目标点：

```text
(0,0,-2) -> (2,0,-2) -> (2,2,-2) -> (0,2,-2) -> (0,0,-2)
```

LeRobot 或任务规划器后续只需要发布同一个 topic：

```bash
source /opt/ros/jazzy/setup.bash
source /home/clcwork/UAV_capture/px4_ros2_ws/install/setup.bash

ros2 topic pub --once /uav/target_position geometry_msgs/msg/Point \
  "{x: 2.0, y: 0.0, z: -2.0}"
```

PASS 默认判定：

- 有足够有效定位样本。
- 记录到至少 4 个外部目标点变化。
- 最终位置距离最终目标不超过 `0.6 m`。
- 平均 3D 跟踪误差不超过 `0.9 m`。
- 最大速度不超过 `3.0 m/s`。

## Recorder Parameters

通用记录脚本：

```text
scripts/run_trajectory_recorder.sh
```

关键环境变量：

```text
VIS_DIR              输出目录，必填
VIS_DURATION         记录时长
VIS_TITLE            图表标题
VIS_DEMO_ID          demo01/demo02/demo03/demo04
MAX_SPEED_PASS       最大速度阈值
AVG_ERROR_PASS       平均跟踪误差阈值
HEIGHT_ERROR_PASS    高度误差阈值
FINAL_ERROR_PASS     最终目标误差阈值
CONDA_ENV_DIR        提供 ffmpeg 的 conda 环境
```

## Offboard QoS And Arming

PX4 的 `/fmu/in/*` DDS 订阅端使用 `BEST_EFFORT` QoS。Demo01-04 的 Offboard 控制都使用显式 `BEST_EFFORT` 发布：

```text
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
```

进入 Offboard 的流程：

1. 先连续发布 setpoint 和 `OffboardControlMode`。
2. 预热后连续多次发送 `VEHICLE_CMD_DO_SET_MODE` 和 arm 命令。
3. 后续持续发布 setpoint，避免 PX4 触发 Offboard loss failsafe。
