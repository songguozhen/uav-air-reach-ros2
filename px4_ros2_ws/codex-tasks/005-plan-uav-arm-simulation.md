# Task 005: Plan UAV Arm Simulation

## Task goal

- 输出 `docs/UAV_ARM_SIMULATION_PLAN.md`。
- 不实现机械臂，只做技术规划。
- 规划从 x500 + 2-DOF/3-DOF arm 开始，而不是直接上复杂 6-DOF 机械臂。

## Documentation requirements

`docs/UAV_ARM_SIMULATION_PLAN.md` 必须包括：

- 为什么先用 2-DOF/3-DOF 简化机械臂。
- 机械臂应该挂载在无人机什么位置。
- URDF/SDF 建模路线。
- 关节控制方案：`ros2_control`、简单 joint command 或 Gazebo plugin。
- 第一阶段任务：悬停状态下机械臂伸出。
- 第二阶段任务：末端触碰固定目标。
- 第三阶段任务：空中按钮按压。
- 与 PX4 Offboard 的关系：PX4 保持平台稳定，机械臂执行局部操作。
- 与 LeRobot 的关系：LeRobot 未来只学习机械臂末端操作策略，不直接控制 PX4 飞控。
- 风险清单：质心变化、惯量扰动、坐标系、接触不稳定、仿真精度。
- 最小 Demo 05 定义：Aerial Target Touch 或 Aerial Button Press。

## Allowed changes

- 只新增 `docs/UAV_ARM_SIMULATION_PLAN.md`。
- 不改源码。

## Required commands

将命令输出保存到 `codex-logs/005-plan-uav-arm-simulation.log`：

```bash
mkdir -p docs
ls docs
```

## Deliverables

- `docs/UAV_ARM_SIMULATION_PLAN.md`
- `codex-logs/005-plan-uav-arm-simulation.log`

## Final report requirements

最终报告必须说明：

- Demo 05 推荐目标。
- 技术路线。
- 当前项目还缺哪些依赖。
- `changed files`
- `commands run`
- `test result`
- `known risks`
