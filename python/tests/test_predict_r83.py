"""Tests: R83a arc predict next-edit (Phase 309)."""

from __future__ import annotations
import json
from typer.testing import CliRunner
from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


def test_predict_json_output(tmp_path):
    f = tmp_path / "foo.py"
    f.write_text("def greet():\n    pass\ngreet()\n")
    result = runner.invoke(app, ["predict", "next-edit", str(f), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["mode"] == "heuristic-stub"
    assert isinstance(data["suggestions"], list)


def test_predict_missing_file_exits_1(tmp_path):
    result = runner.invoke(app, ["predict", "next-edit", str(tmp_path / "missing.py")])
    assert result.exit_code == 1


def test_predict_suggestions_nonempty(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("foo()\nbar()\nbaz()\n")
    result = runner.invoke(app, ["predict", "next-edit", str(f), "--json", "--line", "2"])
    data = json.loads(result.output)
    assert len(data["suggestions"]) > 0
