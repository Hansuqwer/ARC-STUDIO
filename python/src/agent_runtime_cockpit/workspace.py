"""Workspace file scanning helpers."""
from __future__ import annotations

from pathlib import Path

IGNORED_DIRS = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv2",
    "__pycache__",
    "dist",
    "lib",
    "node_modules",
    "src-gen",
}


def iter_workspace_files(workspace: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Return workspace files while excluding env, cache, dependency, build dirs."""
    results: list[Path] = []
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(workspace).parts[:-1]):
            continue
        if path.suffix in suffixes:
            results.append(path)
    return results
