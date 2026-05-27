# Stage 2 Dataset Schema

Task: `020-add-episode-recorder-and-lerobot-export`

## Raw Episode Evidence

Run the recorder with:

```bash
ros2 run aerial_manip_eval episode_recorder
```

The recorder writes raw evidence under:

```text
logs/<demo_name>/<timestamp>/episodes/<episode_id>/
```

Default parameters:

| Parameter | Default | Meaning |
| --- | --- | --- |
| `demo_name` | `stage2_air_reach` | Log namespace under `logs/`. |
| `episode_id` | current timestamp | Stable episode identifier. |
| `task_label` | `air_reach` | Learning task label stored on each record. |
| `task_id` | empty | Optional external task identifier. |
| `logs_root` | `logs` | Root for raw evidence. |
| `timestamp` | current timestamp | Run directory name. |
| `image_topics` | `["/camera/image_raw"]` | `sensor_msgs/msg/Image` topics to record. |
| `max_image_bytes` | `0` | Optional cap for each image payload; `0` means no cap. |

## Recorded Topics

| File | Source | Contents |
| --- | --- | --- |
| `metadata.json` | recorder parameters | Schema version, episode id, task label, topics, frame note. |
| `observations.jsonl` | `/system/observation` | Platform NED state, arm state, target pose, phase, task labels. |
| `actions.jsonl` | `/uav/target_position`, `/arm/target_joints` | High-level UAV and arm actions only. |
| `task_status.jsonl` | `/task/status` | Task id, status code/name, message, progress. |
| `images.jsonl` | configured image topics | Image metadata and relative raw image payload path. |
| `images/<topic>/<index>.raw` | configured image topics | Raw `sensor_msgs/Image.data` bytes. |
| `result.json` | terminal `/task/status` or shutdown | Final status summary. |

The recorder does not publish to PX4 `/fmu/in/*` topics. UAV positions and UAV
targets preserve the project PX4 local NED convention: `x` north, `y` east, and
`z` down.

## LeRobot-Ready Export

Export raw evidence with:

```bash
python3 tools/export_to_lerobot.py \
  --input logs/stage2_air_reach \
  --output datasets/air_reach_v1
```

The exporter creates:

```text
datasets/air_reach_v1/
  meta/dataset.json
  episodes/<episode_id>/metadata.json
  episodes/<episode_id>/result.json
  episodes/<episode_id>/frames.jsonl
  episodes/<episode_id>/images/...
```

`frames.jsonl` is the learning table. Each row contains `episode_id`,
`frame_index`, `timestamp_sec`, `task`, the original observation record, the
nearest high-level action record, `done`, and `success`.

LeRobot is optional for this baseline. If the `lerobot` Python package is not
installed, the exporter still writes the JSONL fallback dataset and records
`lerobot_package_available=false` in `meta/dataset.json`.
