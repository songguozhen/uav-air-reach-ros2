# Task 003: Add Demo Regression Checks

## Task goal

- 增加轻量检查脚本 `scripts/check_demo_outputs.sh`。
- 检查最近一次实验输出中是否存在必要文件。
- 检查 `verify` 输出或 `result.txt` 里是否有 `RESULT=PASS`。
- 检查 `trajectory.csv` 是否存在且包含 `timestamp` 或 `t`、`x`、`y`、`z`、`vx`、`vy`、`vz` 等字段。
- 检查可视化 PNG 是否存在。

## Allowed changes

- `scripts/check_demo_outputs.sh`
- `docs/REGRESSION_CHECKS.md`
- 不允许修改控制节点。
- 不允许删除已有日志、CSV、PNG、MP4 或实验目录。

## Suggested script behavior

支持参数：日志或可视化目录路径。

用法：

```bash
./scripts/check_demo_outputs.sh logs/offboard_hover/<timestamp>
./scripts/check_demo_outputs.sh visualizations/demo01_hover/<timestamp>
```

行为：

- 如果通过，输出 `CHECK=PASS`。
- 如果失败，输出 `CHECK=FAIL` 并说明缺哪个文件或字段。
- 退出码：通过为 `0`，失败为非 `0`。

兼容性要求：

- Demo 1-4 新展示目录应优先检查：
  - `trajectory.csv`
  - `trajectory_3d.png`
  - `xy_path.png`
  - `height_curve.png`
  - `speed_curve.png`
  - `tracking_error.png`
  - `summary.md`
  - `result.txt`
- 老的 hover 验证日志可以检查 `verify.log` 中的 `RESULT=PASS`。

## Required commands

将命令输出保存到 `codex-logs/003-add-demo-regression-checks.log`：

```bash
chmod +x scripts/check_demo_outputs.sh
bash -n scripts/check_demo_outputs.sh
./scripts/check_demo_outputs.sh <一个实际存在的日志目录或可视化目录>
```

## Deliverables

- `scripts/check_demo_outputs.sh`
- `docs/REGRESSION_CHECKS.md`
- `codex-logs/003-add-demo-regression-checks.log`

## Final report requirements

最终报告必须说明：

- 检查了哪些文件。
- 哪些 Demo 目前能通过。
- 哪些检查仍是弱检查。
- `changed files`
- `commands run`
- `test result`
- `known risks`
