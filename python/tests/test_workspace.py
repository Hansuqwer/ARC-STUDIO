"""Tests for the bounded workspace walker.

These tests document and verify the existing bounds on
iter_workspace_files. The bounds themselves were in place before this
test suite was added; see docs/SECURITY_AUDIT_REPORT.md R-0.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.workspace import IGNORED_DIRS, iter_workspace_files


def _touch(p: Path, content: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_extension_filter(tmp_path: Path) -> None:
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "b.txt")
    _touch(tmp_path / "c.py")
    result = iter_workspace_files(tmp_path, (".py",))
    names = sorted(p.name for p in result)
    assert names == ["a.py", "c.py"]


def test_skips_ignored_directories(tmp_path: Path) -> None:
    _touch(tmp_path / "real.py")
    for directory in IGNORED_DIRS:
        _touch(tmp_path / directory / "junk.py")
    result = iter_workspace_files(tmp_path, (".py",))
    names = [p.name for p in result]
    assert names == ["real.py"], f"ignored dirs leaked into results: {[str(p) for p in result]}"


def test_max_files_truncates(tmp_path: Path) -> None:
    for i in range(50):
        _touch(tmp_path / f"f{i:02d}.py")
    result = iter_workspace_files(tmp_path, (".py",), max_files=10)
    assert len(result) == 10


def test_max_bytes_truncates(tmp_path: Path) -> None:
    payload = "x" * 1024
    for i in range(3):
        _touch(tmp_path / f"f{i}.py", payload)
    result = iter_workspace_files(tmp_path, (".py",), max_bytes=2 * 1024)
    assert len(result) <= 2


def test_skips_symlinks(tmp_path: Path) -> None:
    _touch(tmp_path / "real.py")
    try:
        (tmp_path / "link.py").symlink_to(tmp_path / "real.py")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    result = iter_workspace_files(tmp_path, (".py",))
    names = [p.name for p in result]
    assert names == ["real.py"]


def test_results_deterministic(tmp_path: Path) -> None:
    for name in ["c.py", "a.py", "b.py"]:
        _touch(tmp_path / name)
    r1 = iter_workspace_files(tmp_path, (".py",))
    r2 = iter_workspace_files(tmp_path, (".py",))
    assert [str(p) for p in r1] == [str(p) for p in r2]


def test_defaults_are_conservative() -> None:
    """Guard against future loosening of the default caps."""
    import inspect

    sig = inspect.signature(iter_workspace_files)
    assert sig.parameters["max_files"].default <= 5_000
    assert sig.parameters["max_bytes"].default <= 50 * 1024 * 1024


def test_compat_shim_exposes_same_function() -> None:
    """The workspace package shim must expose the bounded walker."""
    from agent_runtime_cockpit import workspace as pkg
    from agent_runtime_cockpit.workspace import iter_workspace_files as direct

    assert pkg.iter_workspace_files is direct
