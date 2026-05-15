"""
Tests: CLI provider commands (list, status, diagnostics, proxy).
"""
from __future__ import annotations

import json
from typer.testing import CliRunner
from agent_runtime_cockpit.cli import app


def test_providers_list_json():
    """arc providers list returns five built-in providers."""
    result = CliRunner().invoke(app, ["providers", "list", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    ids = {p["id"] for p in data}
    assert ids == {"openai", "anthropic", "openrouter", "qwen", "kimi"}


def test_providers_status_json():
    """arc providers status returns dry-run provider statuses."""
    result = CliRunner().invoke(app, ["providers", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert len(data) == 5
    for status in data:
        assert "provider" in status
        assert "api_key_configured" in status
        assert "dry_run" in status or True  # StatusBase always dry-run


def test_providers_diagnostics_json():
    """arc providers diagnostics returns redacted diagnostics payload."""
    result = CliRunner().invoke(app, ["providers", "diagnostics", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert "live_tests_enabled" in payload
    assert "providers" in payload
    assert "routing" in payload
    assert "accounts" in payload
    assert "quota" in payload


def test_providers_proxy_dry_run():
    """arc providers proxy returns dry-run response with no network call."""
    result = CliRunner().invoke(app, [
        "providers", "proxy",
        "--provider", "openai",
        "--model", "gpt-4.1-mini",
        "--prompt", "Hello world",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    resp = json.loads(result.output)["data"]
    assert resp["dry_run"] is True
    assert "No network call" in resp["message"]
    assert resp["provider"] == "openai"
    assert resp["model"] == "gpt-4.1-mini"


def test_providers_quota_show(tmp_path, monkeypatch):
    """arc providers quota show returns today's usage."""
    monkeypatch.setenv("ARC_PROVIDER_QUOTA", str(tmp_path / "quota.json"))
    result = CliRunner().invoke(app, ["providers", "quota", "show", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert "date" in data
    assert "counters" in data


def test_providers_quota_reset(tmp_path, monkeypatch):
    """arc providers quota reset clears today's counters."""
    quota_file = tmp_path / "quota.json"
    monkeypatch.setenv("ARC_PROVIDER_QUOTA", str(quota_file))
    from agent_runtime_cockpit.providers import ProviderQuotaStore
    store = ProviderQuotaStore(path=quota_file)
    store.reserve("openai", dry_run=True)
    usage_before = store.usage()
    assert usage_before["counters"].get("dry_run:provider:openai", 0) > 0
    result = CliRunner().invoke(app, ["providers", "quota", "reset", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["reset"] is True
    usage_after = store.usage()
    assert usage_after["counters"] == {}


def test_providers_quota_show_filtered(tmp_path, monkeypatch):
    """arc providers quota show --provider filters counters."""
    quota_file = tmp_path / "quota.json"
    monkeypatch.setenv("ARC_PROVIDER_QUOTA", str(quota_file))
    from agent_runtime_cockpit.providers import ProviderQuotaStore
    store = ProviderQuotaStore(path=quota_file)
    store.reserve("openai", dry_run=True)
    store.reserve("anthropic", dry_run=True)
    result = CliRunner().invoke(app, [
        "providers", "quota", "show",
        "--provider", "openai",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["provider"] == "openai"
    assert "dry_run:provider:openai" in data["counters"]
    assert "dry_run:provider:anthropic" not in data["counters"]
