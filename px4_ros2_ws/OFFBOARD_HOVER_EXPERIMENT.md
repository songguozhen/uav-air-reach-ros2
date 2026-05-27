# PX4 Offboard Hover Experiment

This workspace contains a reproducible PX4 SITL + Micro XRCE-DDS + ROS 2
Offboard hover experiment for `gz_x500`.

## Build

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

## Run

```bash
cd /home/clcwork/UAV_capture/px4_ros2_ws
./scripts/run_hover_experiment.sh
```

The experiment starts or reuses:

- `tmux` session `px4_gz_x500`
- `tmux` session `micro_xrce_agent`
- `tmux` session `px4_offboard_hover`

By default the script restarts the PX4 and Agent sessions first
(`RESET_STACK=1`) so each run begins from a clean SITL state. Use
`RESET_STACK=0 ./scripts/run_hover_experiment.sh` only when deliberately
reusing an already-running stack.

It verifies that the vehicle is armed, in Offboard mode, and hovering near
NED `z=-2.0 m` with low velocity. Logs are written under
`logs/offboard_hover/<timestamp>/`.

## Useful Commands

```bash
tmux attach -t px4_gz_x500
tmux attach -t micro_xrce_agent
tmux attach -t px4_offboard_hover
./scripts/stop_stack.sh
```
