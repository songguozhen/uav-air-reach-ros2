# Task 021: Add LeRobot Baseline Training and Policy Bridge

## Task goal

- Add the first LeRobot training and inference bridge around high-level actions.

## Allowed changes

- `src/aerial_manip_policy/**`
- `docs/STAGE2_LEROBOT_POLICY.md`
- `codex-logs/021-add-lerobot-baseline-training-and-policy-bridge.log`

## Implementation requirements

- Start with an imitation-learning baseline or documented wrapper around LeRobot's available ACT/SmolVLA tooling.
- Inference must output high-level action chunks only; it must not write PX4 `/fmu/in/*`.
- Include timeout/fallback behavior if inference stalls or disconnects.

## Required commands

```bash
python3 -m compileall src/aerial_manip_policy
python3 - <<'PY' || true
import importlib.util
print("lerobot", "OK" if importlib.util.find_spec("lerobot") else "MISSING")
PY
```

## Deliverables

- Training entry point or documented command wrapper.
- Policy bridge node/client.
- Policy documentation with latency and safety assumptions.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
