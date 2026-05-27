# Stage 2 LeRobot Policy

Task: `021-add-lerobot-baseline-training-and-policy-bridge`

## Training Wrapper

The first training entry point is a thin command wrapper around LeRobot policy
training:

```bash
ros2 run aerial_manip_policy train_lerobot_baseline \
  --dataset-repo-id datasets/air_reach_v1 \
  --output-dir outputs/lerobot_air_reach \
  --policy-type act
```

The wrapper prints the LeRobot command by default. Add `--run` to execute it in
an environment where `lerobot` is installed, for example the project conda
environment:

```bash
/home/clcwork/miniconda3/envs/lerobot/bin/python -m \
  aerial_manip_policy.train_lerobot_baseline \
  --dataset-repo-id datasets/air_reach_v1 \
  --policy-type act \
  --run
```

`--policy-type smolvla` is accepted for SmolVLA experiments. Extra LeRobot
arguments can be repeated with `--extra-arg`.

## Policy Bridge

Run the inference bridge after `/system/observation` is available:

```bash
ros2 run aerial_manip_policy policy_bridge
```

Outputs are intentionally limited to high-level project topics:

| Topic | Type | Purpose |
| --- | --- | --- |
| `/uav/target_position` | `geometry_msgs/msg/Point` | Local PX4 NED high-level UAV target. |
| `/arm/target_joints` | `aerial_manip_msgs/msg/ArmCommand` | High-level arm hold, stow, or joint command. |
| `/policy/status` | `aerial_manip_msgs/msg/TaskStatus` | Bridge state and fallback reasons. |

The bridge does not publish PX4 `/fmu/in/*` topics. UAV commands stay behind the
existing UAV bridge safety boundary.

## Inference Adapters

For deterministic smoke tests, pass a JSON action chunk file:

```bash
ros2 run aerial_manip_policy policy_bridge --ros-args \
  -p policy_json:=/path/to/policy_chunks.json
```

Example JSON:

```json
{
  "source": "example",
  "actions": [
    {
      "dt": 0.2,
      "uav_target_ned": [0.5, 0.0, -2.0],
      "arm_mode": "joint_position",
      "arm_joint_names": ["joint1", "joint2", "joint3"],
      "arm_joint_positions": [0.1, 0.0, -0.1]
    }
  ]
}
```

For a LeRobot ACT or SmolVLA inference process, use `policy_command`. The
command receives one observation JSON object on stdin and must print one action
chunk JSON object on stdout using the schema above:

```bash
ros2 run aerial_manip_policy policy_bridge --ros-args \
  -p policy_command:="/path/to/lerobot_infer_once --checkpoint outputs/policy"
```

## Latency And Safety Assumptions

Default timing parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `control_period` | `0.1` | Main bridge timer period. |
| `observation_timeout` | `1.0` | Maximum accepted age of `/system/observation`. |
| `inference_timeout` | `0.25` | Maximum time allowed for one inference call. |
| `chunk_timeout` | `1.0` | Maximum age of a buffered action chunk. |

If observations are stale, inference times out, the subprocess exits non-zero,
or a policy emits an empty or unsafe chunk, the bridge publishes a high-level
fallback: hold the current UAV target or current UAV position and send an arm
hold command.

The bridge also enforces coarse high-level limits before publishing:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `max_horizontal_range` | `8.0` | Maximum NED horizontal distance from local origin. |
| `min_altitude` | `0.4` | Minimum altitude in meters, represented as `z <= -0.4`. |
| `max_altitude` | `5.0` | Maximum altitude in meters, represented as `z >= -5.0`. |
| `max_uav_target_step` | `0.5` | Maximum 3D step between emitted UAV targets. |

Coordinate convention follows the rest of the project: `/uav/target_position`
is local PX4 NED, so 2 m positive altitude is published as `z = -2.0`.
