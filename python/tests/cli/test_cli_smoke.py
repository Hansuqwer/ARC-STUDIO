"""Smoke tests for every top-level CLI command.

Discovers commands from the CLI object itself so adding a new command
auto-extends the matrix.
"""
import pytest


def _commands(cli_app) -> list[str]:
    if hasattr(cli_app, "commands"):
        return sorted(cli_app.commands.keys())
    if cli_app.__class__.__name__ == "Typer":
        cmds = [c.name for c in cli_app.registered_commands if c.name is not None]
        return sorted(cmds)
    return []


def test_help_runs_clean(run_cli):
    r = run_cli("--help")
    assert r.exit_code == 0
    assert "usage" in r.stdout.lower() or "commands" in r.stdout.lower()


def test_no_args_prints_help_or_exits_two(run_cli):
    r = run_cli([])
    # Click/Typer commonly exit 0 (showing help) or 2 (missing subcommand).
    assert r.exit_code in (0, 2)


@pytest.fixture
def all_commands(cli_app):
    cmds = _commands(cli_app)
    if not cmds:
        pytest.skip("CLI is not Click/Typer; per-command discovery skipped")
    return cmds


def test_every_command_has_help(all_commands, run_cli):
    for cmd in all_commands:
        r = run_cli([cmd, "--help"])
        assert r.exit_code == 0, f"{cmd} --help failed: {r.stderr}"
        assert cmd in r.stdout or "usage" in r.stdout.lower()


def test_unknown_command_is_rejected(run_cli):
    r = run_cli(["definitely-not-a-real-command-xyz"])
    assert r.exit_code != 0
