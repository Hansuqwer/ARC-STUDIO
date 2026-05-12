import json

from typer.testing import CliRunner

from agent_runtime_cockpit import cli
from agent_runtime_cockpit.cli import app


def test_doctor_swarmgraph_reports_available_arc(monkeypatch, tmp_path):
    arc = tmp_path / "arc"
    arc.write_text("#!/usr/bin/env sh\nprintf '%s\n' 'arc run help'\n")
    arc.chmod(arc.stat().st_mode | 0o111)
    monkeypatch.setattr(cli.shutil, "which", lambda command: str(arc) if command == "arc" else None)

    result = CliRunner().invoke(app, ["doctor", "swarmgraph", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["ok"] is True
    assert payload["checks"][-1]["command"] == "arc"


def test_doctor_swarmgraph_exits_one_when_missing(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda _command: None)

    result = CliRunner().invoke(app, ["doctor", "swarmgraph", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)["data"]
    assert payload["ok"] is False
