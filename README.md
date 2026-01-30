# OpenCode Prompt Migration

This folder contains the migrated OpenCode prompt files and a small script to reapply them if the working `.opencode` contents are modified.

Configured agents:
- `build-gpt-5.2-codex`, `plan-gpt-5.2-codex`, `build-gpt-5.2`, `plan-gpt-5.2`

## Apply

From the repo root (`codex-to-opencode/`):

```bash
./opencode-migration/apply.py
```

This copies the tracked files in `opencode-migration/files/` into `~/.opencode/` and merges the agent entries into `~/.config/opencode/opencode.json`. Backups are written to `opencode-migration/backups/` when targets already exist.

## Unapply

```bash
./opencode-migration/unapply.py
```

If backups exist, this restores the most recent backup. If no backups are found, it removes the managed prompt files and removes the migrated agents from `~/.config/opencode/opencode.json`.
