"""Detect CrewAI projects in a workspace."""
from __future__ import annotations

import pathlib
import re

_PATTERNS = [
    re.compile(r"\bfrom\s+crewai\b"),
    re.compile(r"\bimport\s+crewai\b"),
    re.compile(r"\bCrew\s*\("),
]


def is_crewai_workspace(workspace: pathlib.Path) -> bool:
    if (workspace / "pyproject.toml").exists():
        text = (workspace / "pyproject.toml").read_text(errors="ignore")
        if "crewai" in text.lower():
            return True
    for p in workspace.rglob("*.py"):
        if any(part in {".venv", "site-packages", "node_modules"} for part in p.parts):
            continue
        try:
            src = p.read_text(errors="ignore")
        except OSError:
            continue
        if any(pat.search(src) for pat in _PATTERNS):
            return True
    return False
