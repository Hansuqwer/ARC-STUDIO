"""Tests: R85 arc context suggest/attach (Phases 305-306)."""

from __future__ import annotations
import json
import pytest
from typer.testing import CliRunner
from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


@pytest.fixture
def indexed_ws(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("def process_prompt():\n    pass\n")
    monkeypatch.setenv("ARC_INDEX_DIR", str(tmp_path / ".idx"))
    runner.invoke(app, ["index", "build", "--workspace", str(tmp_path)])
    return tmp_path


def test_suggest_empty_index(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_INDEX_DIR", str(tmp_path / ".idx"))
    result = runner.invoke(app, ["context", "suggest", "hello", "--workspace", str(tmp_path)])
    assert result.exit_code == 1


def test_suggest_json(indexed_ws, monkeypatch):
    result = runner.invoke(
        app, ["context", "suggest", "process", "--json", "--workspace", str(indexed_ws)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert isinstance(data["suggestions"], list)


def test_attach_and_list(tmp_path):
    result = runner.invoke(
        app, ["context", "attach", "main.py", "utils.py", "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 0
    result2 = runner.invoke(app, ["context", "list", "--json", "--workspace", str(tmp_path)])
    data = json.loads(result2.output)
    assert "main.py" in data["attached"]
    assert "utils.py" in data["attached"]


def test_attach_json(tmp_path):
    result = runner.invoke(
        app, ["context", "attach", "a.py", "--json", "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True


def test_clear(tmp_path):
    runner.invoke(app, ["context", "attach", "x.py", "--workspace", str(tmp_path)])
    result = runner.invoke(app, ["context", "clear", "--json", "--workspace", str(tmp_path)])
    data = json.loads(result.output)
    assert data["cleared"] is True
    result2 = runner.invoke(app, ["context", "list", "--json", "--workspace", str(tmp_path)])
    assert json.loads(result2.output)["attached"] == []
