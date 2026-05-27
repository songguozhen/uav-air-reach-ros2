# 第二阶段 Codex 任务说明

记录时间：2026-05-27

本文档用中文概述 `codex-tasks/010` 到 `codex-tasks/022` 每个任务要完成的事情，供后续执行 Codex 队列前快速确认。

## Task 010：下载第二阶段资料

把第二阶段需要参考的官方文档、关键论文和本地 PX4 Gazebo 模型快照归档到 `references/stage2/`。该任务只整理资料，不实现功能。完成后应有资料索引 `manifest.yaml`、下载脚本、官方 HTML 文档、论文 PDF 和本地模型快照。

## Task 011：审计第二阶段本地环境

检查当前机器是否具备后续开发所需环境，包括 ROS 2、Gazebo、`ros_gz_bridge`、`gz_ros2_control`、`controller_manager`、LeRobot 以及 PX4 模型文件。该任务只做环境盘点和风险记录，不安装依赖、不改功能代码。

## Task 012：建立空中操作 ROS 2 包骨架

在 `src/` 下创建第二阶段需要的新 ROS 2 包，包括消息包、Gazebo 包、控制包、视觉包、策略包和评估包。这个任务只建立骨架、最小接口和文档，为后续模型、控制、视觉和策略任务打基础。

## Task 013：新增 `x500_arm_2dof` 最小模型

基于 PX4 官方 `x500` 模型新增一个挂载轻量 2 自由度机械臂的 Gazebo 模型。重点是复用官方飞行基座、保持质量和惯量保守、不要修改 PX4-Autopilot 原始模型文件。

## Task 014：打通机械臂 `ros2_control` 闭环

把 `x500_arm_2dof` 的两个机械臂关节接入 `gz_ros2_control` 和 ROS 2 控制器体系。第一版只要求关节状态能回读、简单位置或 forward command 能下发，不做复杂轨迹规划。

## Task 015：实现 `arm_control_bridge`

新增机械臂高层控制桥，风格对齐现有 `uav_control_bridge`。外部模块以后通过 `/arm/*` 高层接口控制机械臂，不直接面对底层 controller topic。该桥需要包含关节限位、速度限制、命令超时和目标跳变检查。

## Task 016：建立统一状态聚合与 TF 基线

新增状态聚合节点，统一输出 UAV、机械臂和后续视觉模块需要的系统状态。该任务要明确 TF 树和坐标边界，尤其是 NED/ENU、FRD/FLU 转换只能集中在边界节点中处理，不能散落到各个模块。

## Task 017：挂载前视相机并桥接到 ROS 2

在 `x500_arm_2dof` 上添加前视 RGB 相机，并通过 `ros_gz_bridge` 把 Gazebo 图像和 camera info 桥接到 ROS 2。第一版只做一个 RGB 相机，先确保图像话题稳定输出。

## Task 018：实现标记目标位姿估计

在仿真环境中放置 AprilTag 或 ArUco 目标，并实现第一版可验证目标位姿输出。目标是发布 `/vision/target_pose` 和 `/vision/target_pose_in_uav_frame`，为后续协同接近控制提供可靠感知输入。

## Task 019：实现 UAV-机械臂协同接近控制器

新增规则式协同控制器，实现“UAV 粗定位 + 机械臂局部精调”的接近流程。该任务必须坚持安全边界：只能通过 `/uav/*` 和 `/arm/*` 高层接口发命令，不能直接发布 PX4 `/fmu/in/*` 底层话题。

## Task 020：实现 episode 录制与 LeRobot 数据导出

为每次仿真 episode 同时保存回归证据和学习数据。原始证据保存到 `logs/<demo>/<timestamp>/`，学习数据导出到 `datasets/air_reach_v1/`。导出格式参考 LeRobotDataset v3，但基础录制逻辑不能强依赖 LeRobot 已安装。

## Task 021：建立 LeRobot 基线训练与推理桥

新增 LeRobot 训练入口和策略推理桥。第一版策略只输出低频高层动作块，由现有 UAV/机械臂控制桥执行；推理桥需要处理延迟、超时和掉线，不允许直接控制 PX4 底层接口。

## Task 022：实现 Air Reach 任务级 Demo 与回归测试

把前面所有模块收敛成一个可重复执行的任务级 demo：稳定悬停、识别标记、协同接近、末端接近或轻触目标。该任务需要定义 PASS/FAIL 指标，包括飞行误差、关节限位、目标可见性、任务时长和末端误差。

## 推荐执行方式

从第二阶段环境审计开始继续跑：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./run_codex_queue.sh --from 011
```

如果只想重跑资料下载任务：

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./run_codex_queue.sh --task codex-tasks/010-download-stage2-materials.md
```
