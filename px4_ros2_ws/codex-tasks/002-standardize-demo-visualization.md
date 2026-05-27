# Task 002: Standardize Demo Visualization

## Task goal

- 检查 Demo 1-4 是否都能生成：
  - `trajectory.csv`
  - `trajectory_3d.png`
  - `xy_path.png`
  - `height_curve.png`
  - `speed_curve.png`
- 如果已有脚本能完成，不重复实现。
- 如果命名不统一，只做轻量标准化。
- 增加 `docs/VISUALIZATION_GUIDE.md`，说明如何查看和复制结果到 Mac。

## Allowed changes

- `scripts/` 下的可视化相关脚本。
- `docs/VISUALIZATION_GUIDE.md`。
- 不允许修改 `hover.py`、PX4 控制核心逻辑，除非只是为了增加非侵入式日志输出。
- 不允许删除已有 `logs/`、`log/`、`visualizations/` 中的实验结果。

## Required commands

将命令输出保存到 `codex-logs/002-standardize-demo-visualization.log`：

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
python3 -m compileall src scripts
# 至少对一个已有 logs 或 visualizations 目录运行可视化相关检查或脚本，验证能生成或已存在 PNG。
find logs -name "*.png" | head
find visualizations -name "*.png" | head
```

如果项目中已有可视化输出但没有独立离线重绘脚本，可以通过检查最近一次 `visualizations/<demo>/<timestamp>/` 中的 PNG 文件满足本任务验证目标，并在最终报告中说明。

## Deliverables

- `docs/VISUALIZATION_GUIDE.md`
- 标准化后的可视化脚本，若有必要
- `codex-logs/002-standardize-demo-visualization.log`

## Final report requirements

最终报告必须说明：

- 每个 Demo 的输出文件命名。
- Mac 端如何通过 `scp` 拉取结果。
- 当前还缺哪些可视化指标。
- `changed files`
- `commands run`
- `test result`
- `known risks`
