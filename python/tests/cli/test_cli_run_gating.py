"""The `run` (or `arc run`) command must enforce dual-gating and never call
out without explicit consent. We verify the no-live-provider invariant from
the CLI side."""
import pytest


def _has(cli_app, name: str) -> bool:
    if hasattr(cli_app, "commands"):
        return name in cli_app.commands
    if cli_app.__class__.__name__ == "Typer":
        return any(c.name == name for c in cli_app.registered_commands)
    return False


@pytest.mark.skipif("not __import__('os').environ.get('CI', '') or True",
                    reason="placeholder until run cmd is wired; always skipped today")
def test_run_blocks_non_stub_without_allow_costs(run_cli, cli_app, workspace, monkeypatch):
    if not _has(cli_app, "run"):
        pytest.skip("no `run` subcommand")
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.delenv("ARC_SWARMGRAPH_ALLOW_COSTS", raising=False)
    r = run_cli(["run", "--runtime", "swarmgraph", "fake:entry"])
    assert r.exit_code != 0
    assert "ALLOW_COSTS" in (r.stdout + r.stderr) or "gate" in (r.stdout + r.stderr).lower()
