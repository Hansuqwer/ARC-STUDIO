import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def _payload(result):
    return json.loads(result.output)


def test_workspace_inventory_basic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "data.json").write_text('{"key": "value"}')
    (tmp_path / "README.md").write_text("# Project")

    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["workspace"] == str(tmp_path)
    assert data["files"]["count"] >= 3
    suffixes = {f["suffix"] for f in data["files"]["entries"]}
    assert ".py" in suffixes
    assert ".json" in suffixes
    assert ".md" in suffixes
    assert data["git"]["present"] is False


def test_workspace_inventory_custom_suffix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "data.ts").write_text("const x = 1")
    (tmp_path / "notes.txt").write_text("ignored")

    result = CliRunner().invoke(app, ["workspace", "inventory", "--json", "--suffix", ".py,.ts"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    suffixes = {f["suffix"] for f in data["files"]["entries"]}
    assert ".py" in suffixes
    assert ".ts" in suffixes
    assert ".txt" not in suffixes


def test_workspace_inventory_with_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True, check=True
    )
    (tmp_path / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)

    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["git"]["present"] is not False
    assert data["git"]["branch"] is not None
    assert data["git"]["commit"] is not None
    assert data["git"]["dirty"] is False


def test_workspace_inventory_with_traces(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    traces_dir = tmp_path / ".arc" / "traces"
    traces_dir.mkdir(parents=True)
    (traces_dir / "run_001.jsonl").write_text('{"event": "test"}')

    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["traces"]["count"] == 1
    assert data["traces"]["entries"][0]["name"] == "run_001.jsonl"


def test_workspace_inventory_mcp_degraded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert "mcp_resources" in data
    assert data["mcp_resources"][0]["present"] is False


def test_workspace_inventory_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text("print('hello')")

    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    entry = data["files"]["entries"][0]
    assert entry["provenance"] == "workspace_file"


def test_workspace_inventory_no_fabrication(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["workspace", "inventory", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["files"]["count"] == 0
    assert data["git"]["present"] is False
