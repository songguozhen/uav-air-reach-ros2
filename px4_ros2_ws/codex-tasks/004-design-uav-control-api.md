# Task 004: Design UAV Control API

## Task goal

- 设计 UAV Control API，使后续视觉模块、LeRobot、任务规划器可以通过统一 ROS2 topic 控制无人机。
- 重点是接口文档，不是大改代码。
- 输出 `docs/UAV_CONTROL_API.md`。

## Suggested interfaces

建议覆盖以下 ROS2 topic：

- `/uav/target_position`
- `/uav/target_pose`
- `/uav/current_position`
- `/uav/current_target`
- `/uav/reached_target`
- `/uav/control_state`
- `/uav/emergency_stop`

## Documentation requirements

`docs/UAV_CONTROL_API.md` 必须说明：

- 每个 topic 的类型。
- 坐标系采用 NED 还是 ENU。
- 高度 `altitude` 与 PX4 `z=-altitude` 的转换关系。
- 如何映射到 `/fmu/in/trajectory_setpoint`。
- 安全限制：最大高度、最大水平范围、最大速度、目标跳变限制。
- 为什么 LeRobot 不应该直接发布 `/fmu/in/*`。
- 后续如何接入机械臂与视觉模块。

## Allowed changes

- 只新增 `docs/UAV_CONTROL_API.md`。
- 可新增 `examples/publish_target_position.sh` 作为示例。
- 不允许修改当前 Offboard 控制代码。

## Required commands

将命令输出保存到 `codex-logs/004-design-uav-control-api.log`：

```bash
mkdir -p docs examples
if [ -f examples/publish_target_position.sh ]; then bash -n examples/publish_target_position.sh; fi
```

## Deliverables

- `docs/UAV_CONTROL_API.md`
- `examples/publish_target_position.sh`，可选
- `codex-logs/004-design-uav-control-api.log`

## Final report requirements

最终报告必须说明：

- 推荐采用哪些 topic。
- 坐标系如何约定。
- 哪些接口后续需要真正实现。
- `changed files`
- `commands run`
- `test result`
- `known risks`
