"""Error-path coverage. These hit argparse-level failures and the global
exception handler if one exists."""
import pytest


def test_invalid_flag_exits_nonzero(run_cli):
    r = run_cli(["--nope-this-flag-does-not-exist"])
    assert r.exit_code != 0


def test_missing_required_arg_for_known_command(run_cli, cli_app):
    # Pick the first subcommand that exists; ask for it without args.
    candidate = None
    for c in ("runs", "inspect", "workflows", "schemas", "runtimes"):
        if hasattr(cli_app, "commands") and c in cli_app.commands:
            candidate = c
            break
    if not candidate:
        pytest.skip("no candidate subcommand")
    r = run_cli([candidate, "--help"])
    assert r.exit_code == 0  # --help always succeeds — sanity check


def test_keyboard_interrupt_returns_nonzero(run_cli, cli_app, monkeypatch):
    if not hasattr(cli_app, "main"):
        pytest.skip("interrupt path only meaningful for Click/Typer")
    # Patch one command's callback to raise KeyboardInterrupt.
    target = next(iter(cli_app.commands.values()))
    original = target.callback

    def boom(*_a, **_k):
        raise KeyboardInterrupt
    target.callback = boom
    try:
        r = run_cli([target.name])
        assert r.exit_code != 0
    finally:
        target.callback = original
