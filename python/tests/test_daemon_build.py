"""Tests for the daemon entry point and build script."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_daemon_main_imports() -> None:
    """Daemon main module imports without error (not frozen)."""
    # Verify the module can be imported and main() exists
    import importlib

    mod = importlib.import_module("agent_runtime_cockpit.__daemon_main__")
    assert hasattr(mod, "main"), "__daemon_main__ must expose main()"
    assert callable(mod.main)


def test_daemon_main_help(tmp_path: Path) -> None:
    """__daemon_main__ --help prints usage and exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_runtime_cockpit.__daemon_main__", "--help"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0, result.stderr
    assert "ARC Studio Daemon" in result.stdout
    assert "--port" in result.stdout
    assert "--host" in result.stdout


def test_build_script_exists() -> None:
    """The PyInstaller build script exists and is executable."""
    script = (
        Path(__file__).resolve().parent.parent
        / "scripts"
        / "build-daemon.sh"
    )
    assert script.is_file(), f"Build script not found at {script}"
    assert script.stat().st_mode & 0o111 != 0, "Build script must be executable"
