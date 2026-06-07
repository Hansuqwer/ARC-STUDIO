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


def _search_json(ws: Path, query: str) -> dict:
    import json

    result = runner.invoke(app, ["workspace", "search", query, "--json", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    return envelope.get("data", envelope)


def test_workspace_search_excludes_sensitive_files(tmp_path):
    ws = _ws(tmp_path)
    (ws / "notes.txt").write_text("the SECRETPATTERN is here\n")
    (ws / ".env").write_text("API_KEY=SECRETPATTERN\n")
    (ws / "credentials.json").write_text('{"k": "SECRETPATTERN"}\n')
    data = _search_json(ws, "SECRETPATTERN")
    files = {r["file"] for r in data["results"]}
    assert any("notes.txt" in f for f in files)
    assert not any(".env" in f for f in files), f"secret file leaked: {files}"
    assert not any("credentials.json" in f for f in files), f"secret file leaked: {files}"


def test_workspace_search_excludes_ignored_dirs(tmp_path):
    ws = _ws(tmp_path)
    (ws / "real.txt").write_text("FINDME here\n")
    nm = ws / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "dep.txt").write_text("FINDME in a dependency\n")
    data = _search_json(ws, "FINDME")
    files = {r["file"] for r in data["results"]}
    assert any("real.txt" in f for f in files)
    assert not any("node_modules" in f for f in files), f"ignored dir leaked: {files}"


def test_workspace_search_caps_results(tmp_path):
    ws = _ws(tmp_path)
    # 1500 matching lines > the 1000 result cap.
    (ws / "many.txt").write_text("\n".join("MATCHLINE" for _ in range(1500)) + "\n")
    data = _search_json(ws, "MATCHLINE")
    assert len(data["results"]) <= 1000
    assert data["truncated"] is True
