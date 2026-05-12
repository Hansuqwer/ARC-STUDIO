"""Exercise the `runs` family if it exists. Each test skips cleanly when
the corresponding subcommand isn't present, so the suite stays green on
CLIs that don't (yet) expose every command."""
import json

import pytest


def _has(cli_app, name: str) -> bool:
    if hasattr(cli_app, "commands"):
        return name in cli_app.commands
    if cli_app.__class__.__name__ == "Typer":
        return any(c.name == name for c in cli_app.registered_commands)
    return False


@pytest.fixture(autouse=True)
def _skip_if_missing(cli_app, request):
    needed = request.node.get_closest_marker("needs")
    if needed:
        for n in needed.args:
            if not _has(cli_app, n):
                pytest.skip(f"CLI does not expose {n!r}")


@pytest.mark.needs("runs")
def test_runs_lists_empty_workspace(run_cli, workspace):
    r = run_cli("runs")
    assert r.exit_code == 0


@pytest.mark.needs("runs")
def test_runs_get_unknown_returns_nonzero(run_cli, workspace):
    r = run_cli(["runs", "get", "deadbeefdead"])
    assert r.exit_code != 0


@pytest.mark.needs("runs")
def test_runs_trace_unknown_returns_nonzero(run_cli, workspace):
    r = run_cli(["runs", "trace", "deadbeefdead"])
    assert r.exit_code != 0


@pytest.mark.needs("runs")
def test_runs_with_populated_workspace_lists(run_cli, workspace):
    # Seed one .jsonl trace; the CLI's runs listing should surface it.
    rid = "aaaaaaaaaaaa"
    p = workspace / ".arc" / "traces" / f"{rid}.jsonl"
    p.write_text(
        json.dumps({"type": "RUN_STARTED", "runId": rid, "timestamp": 1}) + "\n"
        + json.dumps({"type": "RUN_FINISHED", "runId": rid, "timestamp": 2}) + "\n"
    )
    r = run_cli("runs")
    assert r.exit_code == 0
    assert rid in r.stdout or rid[:8] in r.stdout
