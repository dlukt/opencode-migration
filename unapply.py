#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKUP_ROOT = ROOT / "backups"
SRC_DIR = ROOT / "files"
DEFAULT_HOME = Path.home()
DEFAULT_BACKUP_PARENT = ROOT / "backups"
BACKUP_PREFIX = "opencode-migration-"

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


def latest_backup_dir(parent: Path, prefix: str) -> Path | None:
    if not parent.exists():
        return None
    candidates = [
        p for p in parent.iterdir() if p.is_dir() and p.name.startswith(prefix)
    ]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def restore_from_backup(backup_dir: Path, rel_path: str, home: Path) -> None:
    backup_path = backup_dir / rel_path
    target = home / rel_path
    if backup_path.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, target)
    elif target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        remove_empty_dirs(target.parent, home)


def remove_agents_from_config(
    agent_names: set[str], target_config: Path, home: Path
) -> None:
    if not agent_names or not target_config.exists():
        return

    target_data = load_json(target_config)
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
            target_config.unlink(missing_ok=True)
            remove_empty_dirs(target_config.parent, home)
        else:
            save_json(target_config, target_data)

def restore_dir(backup_dir: Path, rel_path: str, home: Path) -> bool:
    source = backup_dir / rel_path
    target = home / rel_path
    if not source.exists():
        return False
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unapply OpenCode prompt migration.")
    parser.add_argument(
        "--home",
        default=str(DEFAULT_HOME),
        help="Home directory to target (default: current user home).",
    )
    parser.add_argument(
        "--backup-dir",
        default="",
        help="Explicit backup directory to restore from.",
    )
    parser.add_argument(
        "--backup-parent",
        default=str(DEFAULT_BACKUP_PARENT),
        help="Directory under which backups are searched when --backup-dir is not set.",
    )
    parser.add_argument(
        "--backup-prefix",
        default=BACKUP_PREFIX,
        help="Prefix used to locate backup directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser().resolve()
    target_config = home / ".config" / "opencode" / "opencode.json"

    source_config = SRC_DIR / "opencode.json"
    source_data = load_json(source_config)
    agent_names = set(source_data.get("agent", {}).keys())

    if args.backup_dir:
        backup_dir = Path(args.backup_dir).expanduser().resolve()
    else:
        backup_parent = Path(args.backup_parent).expanduser().resolve()
        backup_dir = latest_backup_dir(backup_parent, args.backup_prefix)

    if backup_dir and backup_dir.exists():
        restored_opencode = restore_dir(backup_dir, ".opencode", home)
        restored_config = restore_dir(backup_dir, ".config/opencode", home)

        if not restored_config:
            backup_config = backup_dir / ".config/opencode/opencode.json"
            if backup_config.exists():
                restore_from_backup(backup_dir, ".config/opencode/opencode.json", home)
            else:
                remove_agents_from_config(agent_names, target_config, home)

        if not restored_opencode:
            for rel_path in PROMPT_FILES:
                restore_from_backup(backup_dir, rel_path, home)

        print(f"Restored from backup: {backup_dir}")
        return 0

    remove_agents_from_config(agent_names, target_config, home)
    for rel_path in PROMPT_FILES:
        target = home / rel_path
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            remove_empty_dirs(target.parent, home)
    print("Removed managed OpenCode migration files (no backups found).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
