"""CLI tests for provider credential management (Phase 36.2)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.auth.manager import (
    encrypt_credential,
    save_credential,
    get_credential,
)

runner = CliRunner()


def test_providers_add_api_key(tmp_path: Path, monkeypatch):
    """arc providers add --api-key stores an encrypted credential."""
    auth_path = tmp_path / "auth.json"
    # Monkeypatch the module-level AUTH_PATH so save_credential uses our path
    import agent_runtime_cockpit.auth.manager as _auth_mgr_cli

    monkeypatch.setattr(_auth_mgr_cli, "AUTH_PATH", auth_path)
    monkeypatch.setattr(_auth_mgr_cli, "KEY_PATH", tmp_path / ".auth-key")

    result = runner.invoke(
        app,
        [
            "providers",
            "add",
            "--provider",
            "openai",
            "--api-key",
            "sk-test-cli-key-12345",
            "--json",
        ],
    )
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    data = json.loads(result.output)
    assert data["ok"]
    assert data["data"]["provider"] == "openai"
    assert data["data"]["auth_method"] == "api_key"

    # Verify the credential is stored and retrievable
    assert auth_path.exists()
    cred = get_credential("openai", auth_path)
    assert cred is not None
    assert cred.provider_id == "openai"


def test_providers_add_missing_args():
    """arc providers add without --api-key or --oauth reports error."""
    result = runner.invoke(
        app,
        ["providers", "add", "--provider", "openai", "--json"],
    )
    assert result.exit_code == 2
    data = json.loads(result.output)
    assert not data["ok"]


def test_providers_add_unknown_provider():
    """arc providers add with unknown provider reports error."""
    result = runner.invoke(
        app,
        [
            "providers",
            "add",
            "--provider",
            "nonexistent-provider",
            "--api-key",
            "sk-test",
            "--json",
        ],
    )
    assert result.exit_code == 2
    data = json.loads(result.output)
    assert not data["ok"]


def test_providers_remove_existing(tmp_path: Path, monkeypatch):
    """arc providers remove removes stored credentials."""
    import agent_runtime_cockpit.auth.manager as _auth_mgr_cli

    auth_path = tmp_path / "auth.json"
    monkeypatch.setattr(_auth_mgr_cli, "AUTH_PATH", auth_path)
    monkeypatch.setattr(_auth_mgr_cli, "KEY_PATH", tmp_path / ".auth-key")

    # First store a credential
    cred = encrypt_credential("openai", "sk-to-remove")
    save_credential(cred, auth_path)
    assert get_credential("openai", auth_path) is not None

    # Then remove it via CLI
    result = runner.invoke(
        app,
        ["providers", "remove", "openai", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"]
    assert data["data"]["removed"] is True

    # Verify it's gone
    assert get_credential("openai", auth_path) is None


def test_providers_remove_nonexistent(tmp_path: Path, monkeypatch):
    """arc providers remove on non-existent provider returns removed=False."""
    import agent_runtime_cockpit.auth.manager as _auth_mgr_cli

    auth_path = tmp_path / "auth.json"
    monkeypatch.setattr(_auth_mgr_cli, "AUTH_PATH", auth_path)

    result = runner.invoke(
        app,
        ["providers", "remove", "openai", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"]
    assert data["data"]["removed"] is False


def test_providers_remove_honors_trust(tmp_path: Path, monkeypatch):
    """arc providers remove returns removed=False when workspace is not trusted."""
    import agent_runtime_cockpit.auth.manager as _auth_mgr_cli

    auth_path = tmp_path / "auth.json"
    monkeypatch.setattr(_auth_mgr_cli, "AUTH_PATH", auth_path)
    monkeypatch.setattr(_auth_mgr_cli, "_is_workspace_trusted", lambda workspace=None: False)

    result = runner.invoke(
        app,
        ["providers", "remove", "openai", "--json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"]
    assert data["data"]["removed"] is False
