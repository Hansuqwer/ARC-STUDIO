import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def _payload(result):
    return json.loads(result.output)


def test_testbench_detect_package_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["count"] >= 1
    sources = {d["source"] for d in data["detected"]}
    assert "package.json" in sources


def test_testbench_detect_pyproject(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["count"] >= 1
    assert any(d["source"] == "pyproject.toml" for d in data["detected"])


def test_testbench_detect_makefile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Makefile").write_text("test:\n\tpython -m pytest\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["count"] >= 1
    assert any(d["source"] == "Makefile" for d in data["detected"])


def test_testbench_detect_explicit_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["testbench", "detect", "--json", "--command", "pytest tests/"]
    )
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["count"] == 1
    assert data["detected"][0]["command"] == "pytest tests/"
    assert data["detected"][0]["source"] == "explicit_override"


def test_testbench_detect_empty_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["count"] == 0


def test_testbench_run_read_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["testbench", "run", "--json", "--policy", "local-safe", "--", "pwd"]
    )
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is True
    assert data["classification"] == "read_only"
    assert data["stdout"] is not None


def test_testbench_run_network_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app, ["testbench", "run", "--json", "--", "curl", "https://example.com"]
    )
    assert result.exit_code == 3, result.output
    data = _payload(result)["data"]
    assert data["decision"]["allowed"] is False
    assert data["classification"] == "network"


def test_testbench_run_destructive_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["testbench", "run", "--json", "--", "rm", "-rf", "."])
    assert result.exit_code == 3, result.output
    data = _payload(result)["data"]
    assert data["classification"] == "destructive"


def test_testbench_run_missing_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["testbench", "run", "--json"])
    assert result.exit_code == 2, result.output
    data = _payload(result)
    assert data["ok"] is False
