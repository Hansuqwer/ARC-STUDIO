"""SKILL.md catalog — read-only discovery and parsing.

Reads SKILL.md files from workspace, parses YAML frontmatter.
Does NOT execute anything.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_EXCLUDED_DIRS = frozenset(
    ["node_modules", ".git", "dist", "build", "coverage", ".venv", "__pycache__"]
)


@dataclass(frozen=True)
class SkillEntry:
    """A discovered SKILL.md file with parsed frontmatter."""

    path: Path
    sha256: str
    size_bytes: int
    frontmatter: dict[str, Any]
    body: str
    name: str
    description: str


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in _EXCLUDED_DIRS:
            return True
    return False


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown text."""
    match = _FRONTMATTER_RE.match(text)
    if not match or yaml is None:
        return {}, text
    raw_yaml = match.group(1)
    try:
        fm = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        return {}, text
    body = text[match.end() :]
    return fm, body


def discovery(workspace: Path) -> list[SkillEntry]:
    """Discover all SKILL.md files in workspace tree."""
    entries: list[SkillEntry] = []
    for md_path in sorted(workspace.rglob("SKILL.md")):
        rel = md_path.relative_to(workspace)
        if _is_excluded(rel):
            continue
        content = md_path.read_bytes()
        text = content.decode("utf-8", errors="replace")
        fm, body = _parse_frontmatter(text)
        entries.append(
            SkillEntry(
                path=md_path,
                sha256=_sha256(content),
                size_bytes=len(content),
                frontmatter=fm,
                body=body,
                name=fm.get("name", md_path.parent.name),
                description=fm.get("description", ""),
            )
        )
    return entries
