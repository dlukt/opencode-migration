#!/usr/bin/env python3
import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
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


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def backup_path(backup_root: Path, target: Path, home: Path) -> Path:
    relative = target.relative_to(home)
    return backup_root / relative


def maybe_backup(backup_root: Path, target: Path, home: Path) -> None:
    if not target.exists():
        return
    backup = backup_path(backup_root, target, home)
    ensure_parent(backup)
    shutil.copy2(target, backup)


def copy_with_backup(
    backup_root: Path, rel_path: str, home: Path, skip_backup: bool
) -> None:
    src = SRC_DIR / rel_path
    dst = home / rel_path
    if not src.is_file():
        raise FileNotFoundError(f"Missing source file: {src}")
    if not skip_backup:
        maybe_backup(backup_root, dst, home)
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


def resolve_prompt(prompt_value: str, home: Path) -> str:
    if not prompt_value.startswith("{file:"):
        return prompt_value
    if not prompt_value.endswith("}"):
        return prompt_value
    inner = prompt_value[len("{file:") : -1].strip()
    if inner.startswith("~"):
        resolved = Path(inner).expanduser().resolve()
        return f"{{file:{resolved.as_posix()}}}"
    inner_path = Path(inner)
    if inner_path.is_absolute():
        return prompt_value
    cleaned = inner.lstrip("./")
    resolved = (home / cleaned).resolve()
    return f"{{file:{resolved.as_posix()}}}"


def apply_prompt_paths(target: dict, source: dict, home: Path) -> None:
    source_agents = source.get("agent", {})
    if not isinstance(source_agents, dict):
        return
    target_agents = target.get("agent", {})
    if not isinstance(target_agents, dict):
        return
    for name, spec in source_agents.items():
        target_spec = target_agents.get(name)
        if not isinstance(target_spec, dict):
            continue
        prompt_value = spec.get("prompt")
        if isinstance(prompt_value, str):
            target_spec["prompt"] = resolve_prompt(prompt_value, home)


def backup_directory(backup_root: Path, target_dir: Path, home: Path) -> bool:
    if not target_dir.exists():
        return False
    backup_dir = backup_root / target_dir.relative_to(home)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target_dir, backup_dir)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply OpenCode prompt migration.")
    parser.add_argument(
        "--home",
        default=str(DEFAULT_HOME),
        help="Home directory to target (default: current user home).",
    )
    parser.add_argument(
        "--backup-dir",
        default="",
        help="Explicit backup directory to write to.",
    )
    parser.add_argument(
        "--backup-parent",
        default=str(DEFAULT_BACKUP_PARENT),
        help="Directory under which backups are created when --backup-dir is not set.",
    )
    parser.add_argument(
        "--backup-prefix",
        default=BACKUP_PREFIX,
        help="Prefix for auto-created backup directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser().resolve()
    target_config = home / ".config" / "opencode" / "opencode.json"

    if not SRC_DIR.exists():
        print(f"Missing migration folder: {SRC_DIR}")
        return 1

    if args.backup_dir:
        backup_root = Path(args.backup_dir).expanduser().resolve()
    else:
        backup_parent = Path(args.backup_parent).expanduser().resolve()
        backup_root = backup_parent / f"{args.backup_prefix}{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    source_config = SRC_DIR / "opencode.json"
    if not source_config.is_file():
        print(f"Missing source config: {source_config}")
        return 1

    backup_root.mkdir(parents=True, exist_ok=True)
    backed_up_opencode = backup_directory(backup_root, home / ".opencode", home)
    backed_up_config = backup_directory(
        backup_root, home / ".config" / "opencode", home
    )

    target_config_data = load_json(target_config)
    source_data = load_json(source_config)
    if not backed_up_config:
        maybe_backup(backup_root, target_config, home)
    merged = merge_config(target_config_data, source_data)
    apply_prompt_paths(merged, source_data, home)
    save_json(target_config, merged)

    skip_backup = backed_up_opencode
    for rel_path in PROMPT_FILES:
        copy_with_backup(backup_root, rel_path, home, skip_backup)

    print("Reapplied OpenCode prompt migration files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
