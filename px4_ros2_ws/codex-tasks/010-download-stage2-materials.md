# Task 010: Download Stage 2 Materials

## Task goal

- Populate `references/stage2/` with the official documents, key papers, and local PX4 model snapshots listed in `references/stage2/manifest.yaml`.
- This task is documentation/materials only. Do not implement runtime behavior.

## Allowed changes

- `references/stage2/**`
- `codex-logs/010-download-stage2-materials.log`

## Implementation requirements

- Run `bash references/stage2/scripts/download_stage2_materials.sh` from the workspace root.
- Preserve `manifest.yaml` and update it only if a URL or local filename must be corrected.
- If a remote source blocks direct download, keep the manifest entry and record the failure in the log.

## Required commands

```bash
bash references/stage2/scripts/download_stage2_materials.sh
test -s references/stage2/manifest.yaml
find references/stage2 -type f | sort
```

## Deliverables

- Downloaded official references under `references/stage2/official/`.
- Downloaded key papers under `references/stage2/papers/`.
- Local model snapshots under `references/stage2/local_px4_models/`.
- `codex-logs/010-download-stage2-materials.log`.

## Final report requirements

- `changed files`
- `commands run`
- `test result`
- `known risks`
