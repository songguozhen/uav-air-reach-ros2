# Task 001: Audit Project Structure

## Task goal

- 理解当前 `px4_ros2_ws` 的目录结构。
- 找出已有 demo 脚本、可视化脚本、ROS2 包、日志目录。
- 生成项目结构摘要文档。

## Allowed changes

- 只能新增或更新 `docs/PROJECT_STRUCTURE.md`。
- 可以创建 `docs/` 目录。
- 不允许改动任何 Python 控制节点、shell 实验脚本、PX4 配置和日志数据。

## Required commands

将命令输出保存到 `codex-logs/001-audit-project-structure.log`：

```bash
pwd
find . -maxdepth 3 -type f | sort
find . -maxdepth 3 -type d | sort
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git status --short; fi
ls scripts
ls src
if [ -d logs ]; then ls logs; fi
```

## Deliverables

- `docs/PROJECT_STRUCTURE.md`
- `codex-logs/001-audit-project-structure.log`

## Final report requirements

最终报告必须说明：

- 当前有哪些 ROS2 包。
- 当前有哪些 demo 脚本。
- 当前有哪些可视化输出。
- 哪些目录是源码，哪些目录是实验结果，哪些目录不应删除。
- `changed files`
- `commands run`
- `test result`
- `known risks`
