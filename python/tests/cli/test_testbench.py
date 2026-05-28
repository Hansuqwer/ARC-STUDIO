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
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\nminversion = "7.0"\n')
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


def test_testbench_detect_pnpm_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pkg = tmp_path / "packages" / "foo"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text('{"scripts": {"test": "jest"}}')
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    cwds = {d.get("cwd") for d in data["detected"]}
    assert "packages/foo" in cwds


def test_testbench_detect_pyproject_pytest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\nminversion = "7.0"\n')
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert any(d["runner"] == "pytest" for d in data["detected"])


def test_testbench_detect_tox_ini(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tox.ini").write_text("[tox]\nenvlist = py39\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert any(d["runner"] == "tox" for d in data["detected"])


def test_testbench_detect_noxfile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "noxfile.py").write_text("import nox\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert any(d["runner"] == "nox" for d in data["detected"])


def test_testbench_detect_makefile_lowercase(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "makefile").write_text("test:\n\tpython -m pytest\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert any(d["runner"] == "make" for d in data["detected"])


def test_testbench_detect_gnu_makefile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "GNUmakefile").write_text("test:\n\tpython -m pytest\n")
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert any(d["runner"] == "make" for d in data["detected"])


def test_testbench_detect_monorepo_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    foo = tmp_path / "packages" / "foo"
    foo.mkdir(parents=True)
    (foo / "package.json").write_text('{"scripts": {"test": "jest --watch"}}')
    bar = tmp_path / "packages" / "bar"
    bar.mkdir(parents=True)
    (bar / "package.json").write_text('{"scripts": {"test": "vitest"}}')
    (tmp_path / "package.json").write_text('{"workspaces": ["packages/*"]}')
    result = CliRunner().invoke(app, ["testbench", "detect", "--json"])
    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    cwds = {d.get("cwd") for d in data["detected"] if d.get("cwd")}
    assert "packages/foo" in cwds
    assert "packages/bar" in cwds


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
