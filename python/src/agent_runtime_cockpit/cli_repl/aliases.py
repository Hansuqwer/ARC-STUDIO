from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from agent_runtime_cockpit.storage.atomic import write_text_atomic

ALIAS_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


@dataclass(frozen=True)
class AliasRecord:
    name: str
    command: str
    scope: str


def user_alias_path() -> Path:
    return Path.home() / ".arc" / "aliases.json"


def workspace_alias_path(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()).resolve() / ".arc" / "aliases.json"


def _path_for_scope(scope: str, workspace: Path | None = None) -> Path:
    if scope == "user":
        override = os.environ.get("ARC_STUDIO_ALIASES_FILE")
        return Path(override).expanduser() if override else user_alias_path()
    if scope == "workspace":
        return workspace_alias_path(workspace)
    raise ValueError("scope must be user or workspace")


def _read_aliases(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases = data.get("aliases", data)
    if not isinstance(aliases, dict):
        return {}
    return {str(key): str(value) for key, value in aliases.items()}


def _write_aliases(path: Path, aliases: dict[str, str]) -> None:
    payload = {"version": 1, "aliases": dict(sorted(aliases.items()))}
    write_text_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def validate_alias(name: str, command: str | None = None) -> None:
    if not ALIAS_NAME_RE.match(name):
        raise ValueError(
            "alias name must start with a letter and contain only letters, digits, . _ : -"
        )
    if command is not None and not command.strip():
        raise ValueError("alias command must not be empty")


def list_aliases(workspace: Path | None = None) -> list[AliasRecord]:
    records: dict[str, AliasRecord] = {}
    for scope in ("user", "workspace"):
        path = _path_for_scope(scope, workspace)
        for name, command in _read_aliases(path).items():
            records[name] = AliasRecord(name=name, command=command, scope=scope)
    return sorted(records.values(), key=lambda item: item.name)


def get_alias(name: str, workspace: Path | None = None) -> AliasRecord | None:
    for scope in ("workspace", "user"):
        aliases = _read_aliases(_path_for_scope(scope, workspace))
        if name in aliases:
            return AliasRecord(name=name, command=aliases[name], scope=scope)
    return None


def set_alias(
    name: str, command: str, scope: str = "workspace", workspace: Path | None = None
) -> AliasRecord:
    validate_alias(name, command)
    path = _path_for_scope(scope, workspace)
    aliases = _read_aliases(path)
    aliases[name] = command.strip()
    _write_aliases(path, aliases)
    return AliasRecord(name=name, command=aliases[name], scope=scope)


def remove_alias(name: str, scope: str = "workspace", workspace: Path | None = None) -> bool:
    validate_alias(name)
    path = _path_for_scope(scope, workspace)
    aliases = _read_aliases(path)
    removed = aliases.pop(name, None) is not None
    _write_aliases(path, aliases)
    return removed
