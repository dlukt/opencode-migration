#!/usr/bin/env python3
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = ROOT / "opencode-migration" / "backups"
SRC_DIR = ROOT / "opencode-migration" / "files"
HOME = Path.home()
TARGET_CONFIG = HOME / ".config" / "opencode" / "opencode.json"

PROMPT_FILES = [
    ".opencode/prompts/build-gpt-5.2-codex.md",
    ".opencode/prompts/plan-gpt-5.2-codex.md",
    ".opencode/prompts/build-gpt-5.2.md",
    ".opencode/prompts/plan-gpt-5.2.md",
    ".opencode/prompts/core.md",
    ".opencode/prompts/gpt-5.2-codex.md",
    ".opencode/prompts/gpt-5.2.md",
    ".opencode/prompts/templates/model_instructions/gpt-5.2-codex_instructions_template.md",
    ".opencode/prompts/personalities/gpt-5.2-codex_friendly.md",
    ".opencode/prompts/personalities/gpt-5.2-codex_pragmatic.md",
]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def remove_empty_dirs(path: Path, stop: Path) -> None:
    current = path
    while current != stop and current != current.parent:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def latest_backup_dir() -> Path | None:
    if not BACKUP_ROOT.exists():
        return None
    candidates = [p for p in BACKUP_ROOT.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def restore_from_backup(backup_dir: Path, rel_path: str) -> None:
    backup_path = backup_dir / rel_path
    target = HOME / rel_path
    if backup_path.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)
    elif target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        remove_empty_dirs(target.parent, HOME)


def remove_agents_from_config(agent_names: set[str]) -> None:
    if not agent_names or not TARGET_CONFIG.exists():
        return

    target_data = load_json(TARGET_CONFIG)
    agents = target_data.get("agent", {})
    if not isinstance(agents, dict):
        return

    changed = False
    for name in agent_names:
        if name in agents:
            del agents[name]
            changed = True

    if changed:
        if not agents:
            target_data.pop("agent", None)
        if not target_data:
            TARGET_CONFIG.unlink(missing_ok=True)
            remove_empty_dirs(TARGET_CONFIG.parent, HOME)
        else:
            save_json(TARGET_CONFIG, target_data)


def main() -> int:
    source_config = SRC_DIR / "opencode.json"
    source_data = load_json(source_config)
    agent_names = set(source_data.get("agent", {}).keys())

    backup_dir = latest_backup_dir()
    if backup_dir:
        backup_config = backup_dir / ".config/opencode/opencode.json"
        if backup_config.exists():
            restore_from_backup(backup_dir, ".config/opencode/opencode.json")
        else:
            remove_agents_from_config(agent_names)
        for rel_path in PROMPT_FILES:
            restore_from_backup(backup_dir, rel_path)
        print(f"Restored from backup: {backup_dir}")
        return 0

    remove_agents_from_config(agent_names)
    for rel_path in PROMPT_FILES:
        target = HOME / rel_path
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            remove_empty_dirs(target.parent, HOME)
    print("Removed managed OpenCode migration files (no backups found).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
