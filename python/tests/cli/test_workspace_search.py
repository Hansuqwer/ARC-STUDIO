"""Tests for arc workspace search command."""

from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


def test_workspace_search_returns_results(tmp_path):
    ws = _ws(tmp_path)
    (ws / "hello.txt").write_text("hello world\nfoo bar\n")
    result = runner.invoke(
        app, ["workspace", "search", "hello", "--path", ".", "--workspace", str(ws)]
    )
    assert result.exit_code == 0
    assert "hello" in result.output


def test_workspace_search_path_confined(tmp_path):
    ws = _ws(tmp_path)
    evil = "../../../etc"
    result = runner.invoke(
        app, ["workspace", "search", "root", "--path", evil, "--workspace", str(ws)]
    )
    # Should fail with INVALID_INPUT (path escapes workspace) or exit non-zero
    assert (
        result.exit_code != 0
        or "escapes" in result.output
        or "error" in result.output.lower()
        or "INVALID" in result.output
    )


def test_workspace_search_json_flag(tmp_path):
    import json

    ws = _ws(tmp_path)
    (ws / "code.py").write_text("def find_me():\n    pass\n")
    result = runner.invoke(
        app, ["workspace", "search", "find_me", "--json", "--workspace", str(ws)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    # Top-level arc envelope has 'ok' or 'data' key containing results
    assert data.get("ok") is True or "results" in str(data)
