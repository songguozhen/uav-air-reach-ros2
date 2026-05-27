# Task 009: Document UAV Bridge Usage

## Task goal

- Make the implemented UAV bridge easy to operate and audit.
- Update documentation only; do not add new runtime behavior in this task.

## Documentation requirements

Update documentation so it clearly explains:

- Which `/uav/*` topics are now implemented.
- Which topics remain future work.
- How to run the bridge-backed Demo 04.
- How to publish a safe target manually.
- NED coordinate convention and altitude conversion:
  - `/uav/target_position.z` is NED down.
  - Positive altitude `2.0 m` must be sent as `z=-2.0`.
- Safety parameters and defaults:
  - `target_timeout`
  - `max_altitude`
  - `min_altitude`
  - `max_horizontal_range`
  - `target_jump_limit`
  - `reach_xy_tolerance`
  - `reach_z_tolerance`
  - `reach_hold_time`
- How to run regression checks and copy visualization outputs to Mac.

## Allowed changes

- `docs/UAV_CONTROL_API.md`
- `docs/VISUALIZATION_GUIDE.md`
- `docs/REGRESSION_CHECKS.md`
- `TOOLS_AND_SCRIPTS_GUIDE.md` if it already describes demo scripts
- `codex-logs/009-document-uav-bridge-usage.log`

Do not modify code in this task unless needed to fix a documentation command typo discovered by validation.

## Required commands

Save command output to `codex-logs/009-document-uav-bridge-usage.log`:

```bash
ls docs
test -s docs/UAV_CONTROL_API.md
test -s docs/VISUALIZATION_GUIDE.md
test -s docs/REGRESSION_CHECKS.md
grep -R "uav_control_bridge" -n docs TOOLS_AND_SCRIPTS_GUIDE.md scripts || true
```

## Deliverables

- Updated bridge usage documentation.
- `codex-logs/009-document-uav-bridge-usage.log`

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`

