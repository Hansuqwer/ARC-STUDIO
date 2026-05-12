"""Detect AG2 (AutoGen) projects in a workspace."""
from __future__ import annotations

import pathlib
import re

_PATTERNS = [re.compile(r"\bfrom\s+autogen\b"), re.compile(r"\bGroupChatManager\b")]


def is_ag2_workspace(workspace: pathlib.Path) -> bool:
    py = (workspace / "pyproject.toml")
    if py.exists() and "autogen" in py.read_text(errors="ignore").lower():
        return True
    for p in workspace.rglob("*.py"):
        if any(part in {".venv", "site-packages"} for part in p.parts):
            continue
        try:
            src = p.read_text(errors="ignore")
        except OSError:
            continue
        if any(pat.search(src) for pat in _PATTERNS):
            return True
    return False
