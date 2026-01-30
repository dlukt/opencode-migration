#!/usr/bin/env python3
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
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


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def backup_path(backup_root: Path, target: Path) -> Path:
    relative = target.relative_to(HOME)
    return backup_root / relative


def maybe_backup(backup_root: Path, target: Path) -> None:
    if not target.exists():
        return
    backup = backup_path(backup_root, target)
    ensure_parent(backup)
    shutil.copy2(target, backup)


def copy_with_backup(backup_root: Path, rel_path: str) -> None:
    src = SRC_DIR / rel_path
    dst = HOME / rel_path
    if not src.is_file():
        raise FileNotFoundError(f"Missing source file: {src}")
    maybe_backup(backup_root, dst)
    ensure_parent(dst)
    shutil.copy2(src, dst)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def merge_config(target: dict, source: dict) -> dict:
    if "$schema" not in target and "$schema" in source:
        target["$schema"] = source["$schema"]

    source_agents = source.get("agent", {})
    if source_agents and not isinstance(source_agents, dict):
        raise ValueError("Source opencode.json has a non-object 'agent' field.")

    if "agent" not in target:
        target["agent"] = {}
    if not isinstance(target["agent"], dict):
        raise ValueError("Target opencode.json has a non-object 'agent' field.")

    for name, spec in source_agents.items():
        target["agent"][name] = spec

    return target


def main() -> int:
    if not SRC_DIR.exists():
        print(f"Missing migration folder: {SRC_DIR}")
        return 1

    backup_root = (
        ROOT / "opencode-migration" / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
    )

    source_config = SRC_DIR / "opencode.json"
    if not source_config.is_file():
        print(f"Missing source config: {source_config}")
        return 1

    target_config = load_json(TARGET_CONFIG)
    source_data = load_json(source_config)
    maybe_backup(backup_root, TARGET_CONFIG)
    merged = merge_config(target_config, source_data)
    save_json(TARGET_CONFIG, merged)

    for rel_path in PROMPT_FILES:
        copy_with_backup(backup_root, rel_path)

    print("Reapplied OpenCode prompt migration files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
