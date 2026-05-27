# Task 011: Audit Stage 2 Environment

## Task goal

- Verify the local PX4/Gazebo/ROS 2/LeRobot environment before adding aerial manipulation packages.
- Do not change runtime behavior in this task.

## Allowed changes

- `docs/STAGE2_ENVIRONMENT_AUDIT.md`
- `codex-logs/011-audit-stage2-environment.log`

## Implementation requirements

- Check availability and versions for ROS 2, Gazebo, `ros_gz_bridge`, `gz_ros2_control`, `controller_manager`, and LeRobot.
- Confirm local PX4 model files exist for `x500`, `x500_mono_cam`, `mono_cam`, and `arucotag`.
- Record missing dependencies as risks instead of installing packages unless explicitly requested by a later task.

## Required commands

Save output to `codex-logs/011-audit-stage2-environment.log`:

```bash
pwd
ros2 --help >/dev/null && echo ROS2_OK
gz sim --versions || true
ros2 pkg list | grep -E 'ros_gz_bridge|gz_ros2_control|controller_manager|joint_state_broadcaster|forward_command_controller|joint_trajectory_controller' || true
python3 - <<'PY' || true
import importlib.util
print("lerobot", "OK" if importlib.util.find_spec("lerobot") else "MISSING")
PY
test -s /home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500/model.sdf
test -s /home/clcwork/UAV_capture/px4_ws/PX4-Autopilot/Tools/simulation/gz/models/x500_mono_cam/model.sdf
```

## Deliverables

- Environment audit document with PASS/WARN items and concrete missing packages, if any.
- `codex-logs/011-audit-stage2-environment.log`.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
