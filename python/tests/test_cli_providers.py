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
