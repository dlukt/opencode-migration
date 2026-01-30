# OpenCode Prompt Migration

This folder contains the migrated OpenCode prompt files and a small script to reapply them if the working `.opencode` contents are modified.

Configured agents:
- `build-gpt-5.2-codex`, `plan-gpt-5.2-codex`, `build-gpt-5.2`, `plan-gpt-5.2`

## Apply

From the repo root (`opencode-migration/`):

```bash
./apply.py
```

This copies the tracked files in `files/` into `~/.opencode/` and merges the agent entries into `~/.config/opencode/opencode.json`. Agent prompt paths are written as absolute `~/.opencode/...` references to avoid relative path issues. By default, backups are written under `backups/` with a prefix of `opencode-migration-`.

Optional flags:
- `--home` to target a different home directory
- `--backup-dir` to set an explicit backup location
- `--backup-parent` and `--backup-prefix` to control auto-created backup paths

## Unapply

```bash
./unapply.py
```

If backups exist, this restores the most recent backup. If no backups are found, it removes the managed prompt files and removes the migrated agents from `~/.config/opencode/opencode.json`.

Optional flags match `apply.py`.
