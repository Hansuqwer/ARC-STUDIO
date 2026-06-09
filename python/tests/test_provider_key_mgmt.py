"""Tests for R80 (providers set-key/get-key/delete-key/export-env)
and R81 (doctor providers) — Phase 271/272."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(result) -> dict:
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def _auth_patch(tmp_path: Path):
    """Patch auth/manager paths to an isolated temp store."""
    auth_path = tmp_path / "auth.json"
    key_path = tmp_path / ".auth-key"
    return patch.multiple(
        "agent_runtime_cockpit.auth.manager",
        AUTH_PATH=auth_path,
        KEY_PATH=key_path,
    )


# ---------------------------------------------------------------------------
# R80 — set-key / get-key / delete-key / export-env
# ---------------------------------------------------------------------------


def test_set_key_stores_and_get_key_retrieves(tmp_path):
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["providers", "set-key", "openai", "sk-test123", "--json"])
        d = _ok(r)
        assert d["data"]["stored"] is True
        assert d["data"]["provider_id"] == "openai"

        r2 = runner.invoke(app, ["providers", "get-key", "openai", "--json"])
        d2 = _ok(r2)
        assert d2["data"]["provider_id"] == "openai"
        assert d2["data"]["has_credential"] is True


def test_get_key_missing_provider_exits_1(tmp_path):
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["providers", "get-key", "no-such-provider", "--json"])
        assert r.exit_code == 1
        d = json.loads(r.output)
        assert d["ok"] is False


def test_delete_key_removes_stored_key(tmp_path):
    with _auth_patch(tmp_path):
        runner.invoke(app, ["providers", "set-key", "anthropic", "sk-ant-test", "--json"])
        r = runner.invoke(app, ["providers", "delete-key", "anthropic", "--json"])
        d = _ok(r)
        assert d["data"]["deleted"] is True

        # Now get-key should return error
        r2 = runner.invoke(app, ["providers", "get-key", "anthropic", "--json"])
        assert r2.exit_code == 1


def test_delete_key_missing_exits_1(tmp_path):
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["providers", "delete-key", "no-such", "--json"])
        assert r.exit_code == 1


def test_export_env_json_masked(tmp_path):
    with _auth_patch(tmp_path):
        runner.invoke(app, ["providers", "set-key", "openai", "sk-real-key", "--json"])
        r = runner.invoke(app, ["providers", "export-env", "--json"])
        d = _ok(r)
        exports = d["data"]["exports"]
        assert any(e["provider_id"] == "openai" for e in exports)
        # Default: values are masked
        openai_entry = next(e for e in exports if e["provider_id"] == "openai")
        assert openai_entry["value"] == "***"
        assert "OPENAI" in openai_entry["env_var"]


def test_export_env_json_reveal(tmp_path):
    with _auth_patch(tmp_path):
        runner.invoke(app, ["providers", "set-key", "openai", "sk-real-key", "--json"])
        r = runner.invoke(app, ["providers", "export-env", "--reveal", "--json"])
        d = _ok(r)
        openai_entry = next(e for e in d["data"]["exports"] if e["provider_id"] == "openai")
        assert openai_entry["value"] == "sk-real-key"


# ---------------------------------------------------------------------------
# R81 — doctor providers
# ---------------------------------------------------------------------------


def test_doctor_providers_returns_all_providers(tmp_path):
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["doctor", "providers", "--json"])
        d = _ok(r)
        assert d["data"]["total"] > 0
        providers = d["data"]["providers"]
        ids = [p["provider_id"] for p in providers]
        assert "openai" in ids


def test_doctor_providers_local_is_free_tier(tmp_path):
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["doctor", "providers", "--json"])
        d = _ok(r)
        providers = d["data"]["providers"]
        local = [p for p in providers if p["is_free_tier"]]
        assert len(local) > 0
        for p in local:
            assert p["key_source"] == "local"
            assert p["configured"] is True


def test_doctor_providers_stored_key_shows_source(tmp_path):
    with _auth_patch(tmp_path):
        runner.invoke(app, ["providers", "set-key", "anthropic", "sk-ant-test", "--json"])
        r = runner.invoke(app, ["doctor", "providers", "--json"])
        d = _ok(r)
        ant = next(p for p in d["data"]["providers"] if p["provider_id"] == "anthropic")
        assert ant["key_source"] == "stored"
        assert ant["configured"] is True


def test_doctor_providers_env_key_shows_env_source(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-test")
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["doctor", "providers", "--json"])
        d = _ok(r)
        openai = next(p for p in d["data"]["providers"] if p["provider_id"] == "openai")
        assert openai["key_source"] == "env"
        assert openai["configured"] is True


def test_doctor_providers_no_key_shows_none(tmp_path, monkeypatch):
    # Remove any OPENAI env var
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with _auth_patch(tmp_path):
        r = runner.invoke(app, ["doctor", "providers", "--json"])
        d = _ok(r)
        openai = next(p for p in d["data"]["providers"] if p["provider_id"] == "openai")
        assert openai["key_source"] == "none"
        assert openai["configured"] is False
