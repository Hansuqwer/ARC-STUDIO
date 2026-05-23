"""Shared CLI test plumbing.

The CLI implementation may be Click, Typer, or argparse. We discover the
entry point at test-collection time and adapt accordingly. This keeps the
test file free of hard-coded import paths and survives renames.
"""

from __future__ import annotations

import importlib
import io
import os
import shlex
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any, Iterable

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Regenerate golden snapshot files",
    )


CANDIDATE_MODULES: Iterable[str] = (
    "agent_runtime_cockpit.cli.main",
    "agent_runtime_cockpit.cli",
    "agent_runtime_cockpit.__main__",
)


@dataclass
class CLIResult:
    exit_code: int
    stdout: str
    stderr: str


@pytest.fixture(scope="session")
def cli_app() -> Any:
    """Returns whatever the CLI entry point exposes: Click group, Typer
    app, or a callable `main(argv: list[str]) -> int`."""
    for name in CANDIDATE_MODULES:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        for attr in ("app", "cli", "main"):
            obj = getattr(mod, attr, None)
            if obj is not None:
                return obj
    pytest.skip("no CLI entry point found in candidate modules")


@pytest.fixture
def run_cli(cli_app, tmp_path, monkeypatch):
    """Invoke the CLI with isolation: pwd = tmp_path, no inherited env keys."""
    # Strip any provider gates so tests can't accidentally hit a live backend.
    for key in list(os.environ):
        if key.startswith("ARC_") and ("ALLOW_COSTS" in key or "RUN_BACKEND" in key):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)

    def _invoke(argv: str | list[str]) -> CLIResult:
        args = shlex.split(argv) if isinstance(argv, str) else list(argv)

        # Typer (Click underneath)
        if cli_app.__class__.__name__ == "Typer":
            from typer.testing import CliRunner  # type: ignore

            runner = CliRunner()
            result = runner.invoke(cli_app, args)
            return CLIResult(result.exit_code, result.stdout, result.stderr or "")

        # Click
        if hasattr(cli_app, "main") and hasattr(cli_app, "commands"):
            from click.testing import CliRunner  # type: ignore

            runner = CliRunner()
            result = runner.invoke(cli_app, args, catch_exceptions=False)
            return CLIResult(result.exit_code, result.stdout, result.stderr or "")

        # Plain callable
        out, err = io.StringIO(), io.StringIO()
        code = 0
        try:
            with redirect_stdout(out), redirect_stderr(err):
                rv = cli_app(args)
            if isinstance(rv, int):
                code = rv
        except SystemExit as e:
            code = int(e.code or 0)
        return CLIResult(code, out.getvalue(), err.getvalue())

    return _invoke


@pytest.fixture
def workspace(tmp_path):
    """A minimal workspace dir with .arc/ pre-created."""
    (tmp_path / ".arc" / "traces").mkdir(parents=True)
    (tmp_path / ".arc" / "audit").mkdir(parents=True)
    return tmp_path
