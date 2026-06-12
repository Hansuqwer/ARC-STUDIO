"""Tests for R-PERF1: generator-based streaming workspace inventory."""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.workspace import iter_workspace_files


# R-PERF1: generator-based scan; OOM gate; real 100K timing is M4-local indicative only


def test_populated_tree(tmp_path: Path) -> None:
    """iter_workspace_files yields all matching files across subdirectories."""
    # R-PERF1: generator-based scan; OOM gate; real 100K timing is M4-local indicative only
    subdirs = [tmp_path / f"sub{i}" for i in range(10)]
    for d in subdirs:
        d.mkdir()

    expected: set[Path] = set()
    for i, d in enumerate(subdirs):
        for j in range(20):
            f = d / f"file_{i}_{j}.py"
            f.write_text(f"x = {j}\n")
            expected.add(f)

    # max_files default is 1000 — well above 200, max_bytes well above tiny test files
    result = set(
        iter_workspace_files(tmp_path, (".py",), max_files=1000, max_bytes=50 * 1024 * 1024)
    )
    assert result == expected, f"Missing: {expected - result}, extra: {result - expected}"


def test_empty_workspace(tmp_path: Path) -> None:
    """iter_workspace_files on an empty workspace returns no files without error."""
    # R-PERF1: generator-based scan; OOM gate; real 100K timing is M4-local indicative only
    result = list(iter_workspace_files(tmp_path, (".py", ".ts", ".json")))
    assert result == []
