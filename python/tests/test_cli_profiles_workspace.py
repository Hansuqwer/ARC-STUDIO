"""Tests: CLI profiles and workspace config commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def test_profiles_list_json():
    """Arc profiles list returns built-in profiles."""
    result = CliRunner().invoke(app, ["profiles", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    ids = {p["id"] for p in data}
    assert "stub" in ids
    assert "local-safe" in ids
    assert "local-paid" in ids
    assert "gateway" in ids


def test_profiles_list_table():
    """Arc profiles list renders a table."""
    result = CliRunner().invoke(app, ["profiles", "list"])
    assert result.exit_code == 0, result.output
    assert "Run Profiles" in result.output
    assert "stub" in result.output


def test_profiles_show_stub():
    """Arc profiles show stub returns stub profile details."""
    result = CliRunner().invoke(app, ["profiles", "show", "stub", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["id"] == "stub"
    assert data["backend"] == "stub"
    assert data["allow_paid_calls"] is False


def test_profiles_show_paid():
    """Arc profiles show local-paid returns paid profile details."""
    result = CliRunner().invoke(app, ["profiles", "show", "local-paid", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["id"] == "local-paid"
    assert data["allow_paid_calls"] is True
    assert data["allow_network"] is True


def test_profiles_show_unknown_fails_closed():
    """Arc profiles show unknown-id fails closed."""
    result = CliRunner().invoke(app, ["profiles", "show", "nonexistent", "--json"])
    assert result.exit_code == 2
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["details"]["code"] == "UNKNOWN_PROFILE"


def test_profiles_create_persists_outside_workspace(monkeypatch, tmp_path: Path):
    """Arc profiles create writes env-ref metadata outside the workspace."""
    store = tmp_path / "home" / "profiles.json"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("ARC_PROFILE_CONFIG", str(store))
    result = CliRunner().invoke(
        app,
        [
            "profiles",
            "create",
            "ci-paid",
            "--allow-paid-calls",
            "--provider",
            "openai",
            "--default-model",
            "gpt-test",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert store.exists()
    assert not (workspace / ".arc" / "profiles.json").exists()
    payload = json.loads(store.read_text())
    serialized = json.dumps(payload)
    assert "ci-paid" in serialized
    assert "sk-" not in serialized
    assert "OPENAI_API_KEY" not in serialized

    shown = CliRunner().invoke(app, ["profiles", "show", "ci-paid", "--json"])
    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output)["data"]["allow_paid_calls"] is True


def test_workspace_init_creates_config(tmp_path: Path):
    """Arc workspace init creates .arc/config.yaml."""
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "init",
            "--workspace",
            str(tmp_path),
            "--name",
            "test-workspace",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["created"].endswith(".arc/config.yaml")
    config_path = tmp_path / ".arc" / "config.yaml"
    assert config_path.exists()
    import yaml

    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["version"] == 2
    assert cfg["workspace"]["name"] == "test-workspace"


def test_workspace_init_already_exists(tmp_path: Path):
    """Arc workspace init fails if config already exists."""
    config_path = tmp_path / ".arc" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("version: 1\n")
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "init",
            "--workspace",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_workspace_info(tmp_path: Path):
    """Arc workspace info returns workspace metadata."""
    config_path = tmp_path / ".arc" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("version: 1\nworkspace:\n  name: my-ws\n")
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "info",
            "--workspace",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["workspace"] == str(tmp_path)
    assert data["name"] == "my-ws"
    assert data["config_exists"] is True
    assert "trust_level" in data
    assert "trust_reason" in data


def test_workspace_config_show(tmp_path: Path):
    """Arc workspace config shows flattened config."""
    config_path = tmp_path / ".arc" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("version: 1\nruntime:\n  default: swarmgraph\n")
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "config",
            "--workspace",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["version"] == 2
    assert data["runtime.default"] == "swarmgraph"


def test_workspace_config_set(tmp_path: Path):
    """Arc workspace config --key --value updates config."""
    config_path = tmp_path / ".arc" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("version: 1\n")
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "config",
            "--workspace",
            str(tmp_path),
            "--key",
            "runtime.default",
            "--value",
            "langgraph",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["updated"] == "runtime.default"
    assert data["value"] == "langgraph"
    import yaml

    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["runtime"]["default"] == "langgraph"


def test_workspace_config_set_no_config(tmp_path: Path):
    """Arc workspace config --key fails if no config file exists."""
    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "config",
            "--workspace",
            str(tmp_path),
            "--key",
            "runtime.default",
            "--value",
            "langgraph",
            "--json",
        ],
    )
    assert result.exit_code == 1
    assert "not found" in result.output
