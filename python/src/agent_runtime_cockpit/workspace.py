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


def iter_workspace_files(
    workspace: Path,
    suffixes: tuple[str, ...],
    *,
    max_files: int = 1000,
    max_bytes: int = 10 * 1024 * 1024,
) -> list[Path]:
    """Return workspace files while excluding env, cache, dependency, build dirs.

    Symlinks are skipped and total scan size is capped to keep inspection safe
    for generated workspaces and accidental dependency caches.
    """
    results: list[Path] = []
    total_bytes = 0
    for path in workspace.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(workspace).parts[:-1]):
            continue
        if path.suffix in suffixes:
            try:
                total_bytes += path.stat().st_size
            except OSError:
                continue
            if len(results) >= max_files or total_bytes > max_bytes:
                break
            results.append(path)
    return results
