# PX4 ROS 2 Offboard 工具与脚本理解指南



启动 PX4 SITL/Gazebo

启动 Micro XRCE-DDS Agent

启动 [hover.py](http://hover.py) 控制节点

运行 verify_[hover.py](http://hover.py) 验证器

保存日志

自动降落



这份文档解释当前工作区里的工具脚本、ROS 2 节点和判断方法。目标不是背命令，而是理解每个组件在链路里的位置：谁启动仿真、谁打通 DDS、谁发送控制、谁判断控制是否成功。

## 总体链路

当前实验链路是：

```text
PX4 SITL + Gazebo
    |
    | PX4 内置 uxrce_dds_client，UDP 127.0.0.1:8888
    v
Micro XRCE-DDS Agent
    |
    | DDS / ROS 2 topic
    v
ROS 2 px4_msgs + px4_offboard_hover
```

关键点：

- PX4 SITL 是飞控本体，Gazebo 是物理仿真环境。
- Micro XRCE-DDS Agent 是 PX4 和 ROS 2 之间的桥。
- `px4_msgs` 提供 ROS 2 能理解的 PX4 消息类型。
- `px4_offboard_hover` 是我们写的控制与验证包。
- `tmux` 用来让 PX4、Agent、Offboard 节点在后台持续运行。

## 一键实验

最常用命令：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_hover_experiment.sh
```

这个命令会完成：

1. 重启或启动 PX4 SITL + Gazebo。
2. 重启或启动 Micro XRCE-DDS Agent。
3. 启动 Offboard 起飞/悬停节点。
4. 运行验证器判断是否真的悬停成功。
5. 保存本次实验日志。
6. 到达悬停时长后自动降落。

成功时会看到：

```text
RESULT=PASS
logs=/home/clcwork/UAV_capture/px4_ros2_ws/logs/offboard_hover/<timestamp>
```

## scripts/start_stack.sh

作用：启动 PX4 SITL + Gazebo 和 Micro XRCE-DDS Agent。

它做了这些事：

- 启动 `tmux` 会话 `px4_gz_x500`。
- 在 PX4 仓库里运行：

```bash
HEADLESS=1 make px4_sitl gz_x500
```

- 启动 `tmux` 会话 `micro_xrce_agent`。
- 在 Agent 构建目录里运行：

```bash
./MicroXRCEAgent udp4 -p 8888
```

- 等 PX4 控制台出现 `pxh>` 后，设置：

```bash
param set NAV_DLL_ACT 0
commander check
```

为什么设置 `NAV_DLL_ACT=0`：

- 当前实验不依赖 QGroundControl。
- 如果 `NAV_DLL_ACT=2`，PX4 会因为没有 GCS 连接而阻止预检通过。
- 这个设置只针对 SITL 实验环境，目的是允许纯 ROS 2 Offboard 实验。

重要环境变量：

```bash
RESET_STACK=1 ./scripts/start_stack.sh
```

含义：先杀掉旧的 PX4、Agent、Offboard tmux 会话，再重新启动。可复现实验默认使用这个方式。
它也会清理本项目 PX4 仿真 world 对应的残留 `gz sim` 进程，避免旧 Gazebo
服务跨轮次污染预检、姿态或模型状态。

判断它是否成功：

```bash
tmux ls
```

应该看到：

```text
px4_gz_x500
micro_xrce_agent
```

还可以看日志：

```bash
tail -80 /tmp/px4_gz_x500_tmux.log
tail -80 /tmp/micro_xrce_agent.log
```

成功信号：

- PX4 日志出现 `Gazebo world is ready`。
- PX4 日志出现 `uxrce_dds_client`。
- Agent 日志出现 `session established`。
- PX4 日志出现 `Ready for takeoff!` 或 `Preflight check: OK`。

## scripts/run_hover_experiment.sh

作用：一键运行完整 Offboard 悬停实验。

它是最重要的复现实验入口。内部步骤是：

1. 设置实验参数。
2. 创建日志目录。
3. 调用 `scripts/start_stack.sh`。
4. source ROS 2 和当前工作区环境。
5. 启动 `px4_offboard_hover hover` 节点。
6. 等 4 秒，让 Offboard 节点先发 setpoint 并请求解锁。
7. 启动 `px4_offboard_hover verify_hover` 验证悬停。
8. 保存 PX4 和 Agent 日志尾部。

默认参数：

```bash
ALTITUDE=2.0
VERIFY_DURATION=25
HOVER_DURATION=45.0
RESET_STACK=1
```

含义：

- `ALTITUDE=2.0`：目标悬停高度 2 米。
- `VERIFY_DURATION=25`：验证器采样 25 秒。
- `HOVER_DURATION=45.0`：Offboard 节点运行约 45 秒后请求降落。
- `RESET_STACK=1`：每次实验都重启仿真链路，避免旧状态污染结果。

修改高度示例：

```bash
ALTITUDE=3.0 HOVER_DURATION=60.0 ./scripts/run_hover_experiment.sh
```

不要写成 `HOVER_DURATION=60`，建议写 `60.0`，因为 ROS 2 参数类型里这是 double。

判断它是否成功：

看终端输出：

```text
RESULT=PASS
```

典型成功输出类似：

```text
last arming_state=2 nav_state=14 x=-0.004 y=-0.020 z=-1.985
stable z_avg=-1.984
stable speed_max=0.029
stable offboard_count=50 armed_count=50
RESULT=PASS
```

这些字段的意思：

- `arming_state=2`：PX4 已解锁。
- `nav_state=14`：PX4 当前是 Offboard 模式。
- `z=-1.985`：NED 坐标系下高度约 1.985 m。PX4 本地坐标里向上是负 z，所以 2m 高度对应 `z=-2.0`。
- `stable z_avg=-1.984`：稳定窗口内平均高度接近目标高度。
- `speed_max=0.029`：稳定窗口内速度很低，说明不是掠过目标点，而是在悬停。
- `offboard_count=50 armed_count=50`：最后 50 个样本全部处于 Offboard 且 armed。

日志目录：

```text
logs/offboard_hover/<timestamp>/
```

里面有：

- `hover.log`：Offboard 控制节点日志。
- `verify.log`：验证器输出。
- `px4_tail.log`：PX4 日志尾部。
- `agent_tail.log`：Agent 日志尾部。

## scripts/stop_stack.sh

作用：停止所有后台实验会话。

它会 kill：

- `px4_offboard_hover`
- `px4_demo02_waypoint_flight`
- `px4_demo03_circle_trajectory`
- `px4_demo04_external_setpoint`
- `px4_uav_control_bridge`
- `px4_demo04_target_sequence`
- `px4_trajectory_recorder`
- `micro_xrce_agent`
- `px4_gz_x500`
- 本项目 PX4 Gazebo `default.sdf` world 对应的 `gz sim` 进程

使用：

```bash
./scripts/stop_stack.sh
```

什么时候用：

- 实验完成后想清理后台进程。
- PX4/Gazebo 状态混乱，想重新来。
- 端口 8888 被旧 Agent 占用。

注意：它会停止仿真，不会删除代码或日志。

## ROS 2 节点：hover

入口：

```bash
ros2 run px4_offboard_hover hover
```

脚本文件：

```text
src/px4_offboard_hover/px4_offboard_hover/hover.py
```

作用：实际控制飞机起飞、进入 Offboard、悬停、可选自动降落。

它发布三个核心话题：

```text
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
```

控制逻辑：

1. 每 0.1 秒发布一次 Offboard 控制模式。
2. 每 0.1 秒发布一次目标位置。
3. 默认先发 20 次 setpoint，也就是约 2 秒预热。
4. 预热后发送：

```text
VEHICLE_CMD_DO_SET_MODE
VEHICLE_CMD_COMPONENT_ARM_DISARM
```

1. 飞机进入 Offboard 并解锁后，飞到目标点：

```text
x=0, y=0, z=-altitude
```

1. 如果 `land_on_exit=true` 且到达 `hover_duration`，发送 `VEHICLE_CMD_NAV_LAND`。
2. 请求降落后停止 Offboard setpoint 流。

手动运行示例：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run px4_offboard_hover hover --ros-args \
  -p altitude:=2.0 \
  -p hover_duration:=45.0 \
  -p land_on_exit:=true
```

关键参数：

- `altitude`：悬停高度，单位米。
- `x`、`y`：本地 NED 坐标目标位置。
- `yaw`：目标航向角，单位 rad。
- `setpoint_warmup_cycles`：切 Offboard 前先发多少次 setpoint。
- `hover_duration`：悬停多久后触发降落。
- `land_on_exit`：是否自动降落。

如何理解控制：

- Offboard 模式不是一次性命令，而是持续控制流。
- PX4 要求进入 Offboard 前已经持续收到 setpoint。
- 如果 setpoint 中断，PX4 会触发 Offboard loss failsafe。
- 所以 `hover.py` 的核心不是“发一个起飞命令”，而是“持续给 PX4 一个位置控制目标”。

## 基础控制 Demo 脚本

4 个基础控制展示 demo 的详细说明见：

```text
BASIC_CONTROL_DEMOS.md
```

脚本入口：

```text
scripts/run_demo01_hover.sh
scripts/run_demo02_waypoint_flight.sh
scripts/run_demo03_circle_trajectory.sh
scripts/run_demo04_external_setpoint.sh
```

每个 demo 都会：

1. 调用 `scripts/start_stack.sh` 启动或重启 PX4 SITL 和 Micro XRCE-DDS Agent。
2. 创建本次日志目录：

```text
logs/<demo>/<timestamp>/
```

3. 创建本次可视化目录：

```text
visualizations/<demo>/<timestamp>/
```

4. 在 tmux 中启动对应控制节点。
5. 在 tmux 中启动 `trajectory_recorder`，等待记录结束后打印输出文件绝对路径，自动生成：

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

`result.txt` 和 `summary.md` 会包含 `RESULT=PASS` 或 `RESULT=FAIL`。默认判定标准按 demo 区分：Hover 看稳定段高度/速度/误差，Waypoint 看航点和跟踪误差，Circle 看期望圆 vs 实际轨迹，External Setpoint 看外部目标点变化与实际跟踪。

`trajectory.mp4` 使用 conda 的 LeRobot 环境里的 ffmpeg。脚本不会整体切换到 conda Python，只会把下面目录加到 `PATH`：

```text
/home/clcwork/miniconda3/envs/lerobot/bin
```

这样做是为了让 ROS 2 节点继续使用当前工作区可用的 Python/ROS 环境，同时使用 LeRobot 环境提供的视频编码器。

如果 conda 路径变化：

```bash
CONDA_ENV_DIR=/path/to/conda/env ./scripts/run_demo01_hover.sh
```

### 展示成果与实测结果

完整记录见：

```text
BASIC_CONTROL_DEMOS.md
```

当前 demo 能实现：

- Demo01 Hover：自动起飞到目标高度并悬停，输出高度曲线、速度曲线和悬停稳定性误差。
- Demo02 Waypoint：按固定航点飞行，输出 XY 航点轨迹图和 3D 轨迹图。
- Demo03 Circle：固定高度绕圆飞行，输出期望圆轨迹 vs 实际轨迹。
- Demo04 External Setpoint：默认通过 `uav_control_bridge` 订阅 `/uav/target_position`，输出外部目标点变化与实际跟踪曲线；也保留 legacy 直连示例模式。

运行方式：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_demo01_hover.sh
./scripts/run_demo02_waypoint_flight.sh
./scripts/run_demo03_circle_trajectory.sh
./scripts/run_demo04_external_setpoint.sh
```

Demo04 默认模式等价于：

```bash
DEMO04_MODE=bridge ./scripts/run_demo04_external_setpoint.sh
```

该模式会启动 `ros2 run px4_offboard_hover uav_control_bridge`，并把方形目标序列发布到 `/uav/target_position`。目标点使用 PX4 本地 NED 坐标，`z` 是 down 方向；2 m 正高度必须发布为 `z=-2.0`，不能发布为 `z=2.0`。

手动发布一个安全目标示例：

```bash
ros2 topic pub --once /uav/target_position geometry_msgs/msg/Point \
  '{x: 0.0, y: 0.0, z: -2.0}'
```

当前 `uav_control_bridge` 已实现的话题：

```text
/uav/target_position
/uav/current_position
/uav/current_target
/uav/reached_target
/uav/control_state
```

仍属于后续工作的高层话题：

```text
/uav/target_pose
/uav/emergency_stop
```

桥节点安全参数默认值：

```text
target_timeout=1.0
max_altitude=5.0
min_altitude=0.5
max_horizontal_range=5.0
target_jump_limit=1.5
reach_xy_tolerance=0.30
reach_z_tolerance=0.20
reach_hold_time=1.0
```

Demo04 bridge runner 为了让现有方形序列稳定运行，会覆盖其中两个参数：

```text
BRIDGE_TARGET_TIMEOUT=25.0
BRIDGE_TARGET_JUMP_LIMIT=2.5
```

不启动仿真、只查看 Demo04 bridge 命令链路：

```bash
DRY_RUN=1 ./scripts/run_demo04_external_setpoint.sh
```

旧的 Demo04 直连示例仅用于对比：

```bash
DEMO04_MODE=legacy ./scripts/run_demo04_external_setpoint.sh
```

每个脚本结束时会打印本次结果的绝对路径。2026-05-26 的最新实测结果全部为 `RESULT=PASS`，视频路径如下：

```text
/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo01_hover/20260526_221722/trajectory.mp4
/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo02_waypoint_flight/20260526_222121/trajectory.mp4
/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo03_circle_trajectory/20260526_222313/trajectory.mp4
/home/clcwork/UAV_capture/px4_ros2_ws/visualizations/demo04_external_setpoint/20260526_222502/trajectory.mp4
```

## ROS 2 节点：offboard_base

脚本文件：

```text
src/px4_offboard_hover/px4_offboard_hover/offboard_base.py
```

作用：Demo 02、Demo 03、Demo 04 共享的 PX4 Offboard 位置控制基类。

它发布：

```text
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
```

关键实现点：

- `/fmu/in/*` 发布端显式使用 `BEST_EFFORT` QoS，匹配 PX4 DDS 订阅端。
- 切 Offboard 前先持续发布 setpoint。
- 预热完成后连续多次发送 Offboard mode 和 arm 命令，避免单次 command 丢包。
- 请求降落时重复发送 `VEHICLE_CMD_NAV_LAND`，然后停止 setpoint 流。

判断 Offboard 控制是否真的生效：

```bash
ros2 topic echo --once /fmu/out/vehicle_status_v4 px4_msgs/msg/VehicleStatus
```

关键字段：

```text
arming_state: 2
nav_state: 14
accepts_offboard_setpoints: true
```

位置确认：

```bash
ros2 topic echo --once /fmu/out/vehicle_local_position_v1 px4_msgs/msg/VehicleLocalPosition
```

## ROS 2 节点：verify_hover

入口：

```bash
ros2 run px4_offboard_hover verify_hover
```

脚本文件：

```text
src/px4_offboard_hover/px4_offboard_hover/verify_hover.py
```

作用：判断 Offboard 悬停是否真的成功。

它订阅两个 PX4 输出话题：

```text
/fmu/out/vehicle_status_v4
/fmu/out/vehicle_local_position_v1
```

注意：话题名带 `_v4`、`_v1`，但 ROS 消息类型是：

```text
px4_msgs/msg/VehicleStatus
px4_msgs/msg/VehicleLocalPosition
```

验证条件：

- 最后状态必须是 armed。
- 最后状态必须是 Offboard。
- 稳定窗口内所有样本都必须 armed。
- 稳定窗口内所有样本都必须 Offboard。
- 平均高度必须接近目标高度。
- 最大速度必须低于阈值。

默认阈值：

```text
target-z=-2.0
z-tolerance=0.35
max-speed=0.8
window=50
duration=25
```

手动验证示例：

```bash
ros2 run px4_offboard_hover verify_hover \
  --duration 25 \
  --target-z -2.0 \
  --z-tolerance 0.35 \
  --max-speed 0.8
```

为什么要用这个验证器：

- 只看到飞机动了，不代表 Offboard 控制成功。
- 只看到 topic list，也不代表能控制。
- 真正成功至少要同时满足：已解锁、Offboard 模式、位置接近目标、速度低。

## tmux 会话怎么理解

当前脚本使用三个 tmux 会话：

```text
px4_gz_x500
micro_xrce_agent
px4_offboard_hover
```

查看会话：

```bash
tmux ls
```

进入会话：

```bash
tmux attach -t px4_gz_x500
tmux attach -t micro_xrce_agent
tmux attach -t px4_offboard_hover
```

退出但不停止：

```text
Ctrl-b 然后按 d
```

理解方式：

- `px4_gz_x500` 是飞控和 Gazebo 的后台终端。
- `micro_xrce_agent` 是 DDS 桥的后台终端。
- `px4_offboard_hover` 是控制节点的后台终端。

## 如何判断链路是否正常

### 1. PX4 和 Gazebo 是否启动

```bash
tail -80 /tmp/px4_gz_x500_tmux.log
```

正常信号：

```text
Gazebo world is ready
PX4_SIM_MODEL=gz_x500
pxh>
Ready for takeoff!
```

### 2. Agent 是否连接 PX4

```bash
tail -80 /tmp/micro_xrce_agent.log
```

正常信号：

```text
running... | port: 8888
session established
participant created
```

### 3. ROS 2 是否看到 PX4 话题

```bash
source /opt/ros/jazzy/setup.bash
source /home/clcwork/UAV_capture/px4_ros2_ws/install/setup.bash
ros2 topic list | grep /fmu/
```

正常会看到：

```text
/fmu/in/offboard_control_mode
/fmu/in/trajectory_setpoint
/fmu/in/vehicle_command
/fmu/out/vehicle_status_v4
/fmu/out/vehicle_local_position_v1
```

### 4. ROS 2 是否能解码消息

```bash
ros2 topic echo --once /fmu/out/vehicle_status_v4 px4_msgs/msg/VehicleStatus
```

如果能看到 `arming_state`、`nav_state` 等字段，说明 `px4_msgs` 可用。

## 如何判断控制是否成功

最可靠方式：

```bash
ros2 run px4_offboard_hover verify_hover
```

或者直接看一键实验输出：

```text
RESULT=PASS
```

人工判断时重点看这些字段：

```text
arming_state=2
nav_state=14
z 接近 -2.0
speed_max 很小
offboard_count == stable_window
armed_count == stable_window
```

字段解释：

- `arming_state=1`：未解锁。
- `arming_state=2`：已解锁。
- `nav_state=14`：Offboard。
- `z=-2.0`：在 NED 坐标系中，上方 2 米。
- `speed_max` 越接近 0，越像稳定悬停。

## 常见失败与排查

### RESULT=FAIL reason=no_samples

含义：验证器没有收到 PX4 状态或位置消息。

检查：

```bash
tmux ls
tail -80 /tmp/micro_xrce_agent.log
ros2 topic list | grep /fmu/
```

常见原因：

- Agent 没启动。
- PX4 没和 Agent 建立 session。
- 没 source 工作区。

### arming_state=1

含义：没有解锁。

检查 PX4 日志：

```bash
tail -120 /tmp/px4_gz_x500_tmux.log
```

常见原因：

- 预检失败。
- Offboard 节点没启动。
- 参数类型错误导致节点启动后退出。

### nav_state 不是 14

含义：没有进入 Offboard。

常见原因：

- 进入 Offboard 前 setpoint 预热不足。
- `/fmu/in/offboard_control_mode` 或 `/fmu/in/trajectory_setpoint` 没有持续发布。
- DDS 链路中断。

### z 不接近目标高度

含义：可能起飞还没完成，或目标参数不对。

检查：

```bash
cat logs/offboard_hover/<timestamp>/verify.log
cat logs/offboard_hover/<timestamp>/hover.log
```

如果刚启动就验证，可能需要增大 `VERIFY_DURATION`。

### 起飞后触发 failsafe

检查 PX4 日志：

```bash
tail -160 /tmp/px4_gz_x500_tmux.log
```

常见原因：

- Offboard setpoint 中断。
- 控制节点崩溃。
- 降落命令和持续 setpoint 逻辑冲突。

当前 `hover.py` 已处理：请求 land 后停止 Offboard setpoint 流。

## 推荐工作流

第一次或状态不确定时：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/stop_stack.sh
./scripts/run_hover_experiment.sh
```

只想看后台状态：

```bash
tmux ls
tail -80 /tmp/px4_gz_x500_tmux.log
tail -80 /tmp/micro_xrce_agent.log
```

只想重新验证当前悬停：

```bash
source /opt/ros/jazzy/setup.bash
source /home/clcwork/UAV_capture/px4_ros2_ws/install/setup.bash
ros2 run px4_offboard_hover verify_hover
```

实验结束清理：

```bash
./scripts/stop_stack.sh
```

## 如何改控制目标

修改高度：

```bash
ALTITUDE=3.0 ./scripts/run_hover_experiment.sh
```

修改悬停时长：

```bash
HOVER_DURATION=60.0 ./scripts/run_hover_experiment.sh
```

修改验证时间：

```bash
VERIFY_DURATION=35 ./scripts/run_hover_experiment.sh
```

手动运行不同位置：

```bash
ros2 run px4_offboard_hover hover --ros-args \
  -p x:=1.0 \
  -p y:=0.5 \
  -p altitude:=2.0 \
  -p hover_duration:=45.0 \
  -p land_on_exit:=true
```

注意：

- PX4 本地坐标是 NED。
- `x` 正方向通常是 North。
- `y` 正方向通常是 East。
- `z` 向下为正，所以向上 2 米是 `z=-2.0`。

## 你应该如何理解这些工具

可以把它们分成三层：

### 第一层：基础设施

- `start_stack.sh`
- `stop_stack.sh`
- `tmux`
- PX4 SITL
- Gazebo
- Micro XRCE-DDS Agent

这一层负责“系统是否跑起来”。

### 第二层：控制

- `hover.py`
- ROS 2 input topics `/fmu/in/*`

这一层负责“给 PX4 发什么控制目标”。

### 第三层：验证

- `verify_hover.py`
- ROS 2 output topics `/fmu/out/*`
- `logs/offboard_hover/<timestamp>`

这一层负责“控制是否真的发生且稳定”。

判断实验不要只看一层。完整判断应该是：

```text
基础设施正常
    + 控制节点正常发命令
    + PX4 状态显示 armed/offboard
    + 位置和速度数据符合目标
    = 控制真实成功
```
