# Codex project rules

These rules apply to the ROS2/PX4/LeRobot UAV simulation workspace at:

```text
/home/clcwork/UAV_capture/px4_ros2_ws
```

## Scope and workflow

- 每次 Codex 运行都必须先读取并遵守 `codex.md`。`codex.md` 是当前项目状态、路径管理、日志记录和每次运行流程的主记录。
- 修改前先理解项目结构，不要盲目改文件。
- 每个任务只做当前 `codex-tasks/` 中对应 task 文件里的要求，不主动扩大范围。
- 优先修改当前 ROS2 工作区 `/home/clcwork/UAV_capture/px4_ros2_ws` 下的脚本、文档和自定义包。
- 不要随意更改 PX4-Autopilot 源码，除非任务文件明确要求。
- 不要破坏已成功通过的 Demo 1-4：
  - Demo 01 Offboard Hover
  - Demo 02 Waypoint Flight
  - Demo 03 Circle Trajectory
  - Demo 04 External Setpoint Interface
- 如果需要长时间运行实验，优先使用已有脚本和 tmux，不要随意新建后台进程。
- 对于 PX4/Gazebo/Micro XRCE-DDS 相关任务，优先使用已有 `start_stack.sh`、`stop_stack.sh`、`run_*_experiment.sh` 和 `run_demo*.sh` 脚本。

## Safety rules

- 不要删除用户数据、日志、实验结果、模型 checkpoint、rosbag、`trajectory.csv`、可视化图片或视频。
- 不要删除或改动 `.env`、secrets、production 配置、SSH key、token、代理配置、系统级配置。
- 不要运行破坏性命令，例如 `git reset --hard`、批量删除日志或清空实验目录，除非任务文件明确要求且用户确认。
- 如果工作区已有未提交修改，必须保留并绕开无关修改，不要回滚用户改动。

## Validation requirements

- 修改代码后必须运行相关测试、检查脚本或最小可复现实验。
- 修改 shell 脚本后必须确保可执行权限正确，并至少运行 `bash -n <script>`。
- 修改 Python 节点后必须至少运行 `python3 -m compileall`、`python3 -m py_compile` 或相关 pytest。
- 如果测试失败，先尝试修复；仍失败则在最终报告里写清楚原因。
- 每次执行任务应把输出日志保存到 `codex-logs/`。

## Demo and visualization rules

- 对于可视化任务，优先复用现有 `trajectory.csv`、日志和 plotting/recorder 脚本，不要重复造轮子。
- Demo 1-4 的展示输出应保持稳定命名：
  - `trajectory.csv`
  - `trajectory_3d.png`
  - `xy_path.png`
  - `height_curve.png`
  - `speed_curve.png`
  - `tracking_error.png`
  - `trajectory.mp4`
  - `summary.md`
  - `result.txt`
- 不要删除或覆盖已有 `visualizations/<demo>/<timestamp>/` 结果目录。

## UAV high-level control bridge rules

- 后续视觉、任务规划、LeRobot 和机械臂相关任务必须优先通过 `/uav/*` 高层 ROS2 topic 接入无人机控制。
- 不要让外部模块直接发布 `/fmu/in/offboard_control_mode`、`/fmu/in/trajectory_setpoint` 或 `/fmu/in/vehicle_command`。
- PX4 `/fmu/in/*` 发布逻辑应集中在一个可审计的 UAV bridge 或现有 Offboard 控制基类内。
- 新增 UAV bridge 节点时必须至少包含：
  - 参数化安全限制，例如最大高度、最小高度、最大水平范围、目标跳变限制和目标超时。
  - 当前安全目标和控制状态输出。
  - 明确的 NED 坐标系说明，正高度输入必须转换为 PX4 `z=-altitude` 后再发给 PX4。
  - `python3 -m compileall` 或等价 Python 检查。
- Demo 04 可以继续作为外部目标点接口示例，但新的回归任务应优先验证通过 UAV bridge 跑通的路径。

## LeRobot and UAV-arm rules

- 对于后续 LeRobot 接入任务，不要让 LeRobot 直接控制 PX4 底层电机或姿态，只允许通过高层接口或机械臂操作策略接入。
- LeRobot、视觉模块或任务规划器应优先通过 `/uav/target_position` 等高层 ROS2 topic 接入。
- 对于 UAV-arm 任务，先设计 2-DOF/3-DOF 简化机械臂仿真，不要直接引入复杂 6-DOF 重机械臂。
- PX4 Offboard 保持飞行平台稳定，机械臂执行局部操作；不要把机械臂策略和 PX4 飞控底层控制混在一起。

## Final report format

每个任务结束时必须总结：

- `changed files`: 改了哪些文件。
- `commands run`: 跑了什么命令。
- `test result`: 结果如何，PASS/FAIL。
- `known risks`: 还有什么风险或未验证项。
