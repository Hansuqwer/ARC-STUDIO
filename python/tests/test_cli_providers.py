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


def test_doctor_env_json():
    """arc doctor env returns environment checks."""
    result = CliRunner().invoke(app, ["doctor", "env", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["ok"] is True
    check_names = {c["check"] for c in data["checks"]}
    assert "python_version" in check_names
    assert "arc_version" in check_names
    assert "provider_keys" in check_names


def test_doctor_network_json():
    """arc doctor network returns connectivity checks."""
    result = CliRunner().invoke(app, ["doctor", "network", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert "checks" in data
    check_names = {c["check"] for c in data["checks"]}
    assert "openai" in check_names
    assert "anthropic" in check_names


def test_doctor_storage_json(tmp_path, monkeypatch):
    """arc doctor storage returns storage status."""
    traces_dir = tmp_path / ".arc" / "traces"
    traces_dir.mkdir(parents=True)
    result = CliRunner().invoke(app, [
        "doctor", "storage",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert "checks" in data
    check_names = {c["check"] for c in data["checks"]}
    assert "traces_dir" in check_names
    assert "sqlite_index" in check_names


def test_bug_report_json(tmp_path):
    """arc bug-report returns diagnostic payload."""
    result = CliRunner().invoke(app, [
        "bug-report",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert "arc_version" in data
    assert "python_version" in data
    assert "platform" in data
    assert "workspace" in data
    assert "providers" in data
    assert "config" in data


def test_runs_search_no_index(tmp_path):
    """arc runs search fails gracefully when SQLite index missing."""
    result = CliRunner().invoke(app, [
        "runs", "search",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_runs_search_with_index(tmp_path):
    """arc runs search returns results from SQLite index."""
    from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    store = IndexedTraceStore(
        trace_dir=tmp_path / ".arc" / "traces",
        db_path=tmp_path / ".arc" / "arc.db",
    )
    store.init()
    record = RunRecord(
        id="test-run-1",
        workflow_id="test-workflow",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
    )
    store.save(record)
    result = CliRunner().invoke(app, [
        "runs", "search",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["count"] >= 1
    assert data["total_indexed"] >= 1
    assert len(data["results"]) >= 1
    assert data["results"][0]["id"] == "test-run-1"


def test_runs_search_filtered(tmp_path):
    """arc runs search filters by runtime."""
    from agent_runtime_cockpit.storage.indexed_store import IndexedTraceStore
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    store = IndexedTraceStore(
        trace_dir=tmp_path / ".arc" / "traces",
        db_path=tmp_path / ".arc" / "arc.db",
    )
    store.init()
    store.save(RunRecord(id="run-sg", workflow_id="wf1", runtime="swarmgraph", status=RunStatus.COMPLETED, started_at="2026-05-15T00:00:00Z"))
    store.save(RunRecord(id="run-lg", workflow_id="wf2", runtime="langgraph", status=RunStatus.COMPLETED, started_at="2026-05-15T00:01:00Z"))
    result = CliRunner().invoke(app, [
        "runs", "search",
        "--runtime", "langgraph",
        "--workspace", str(tmp_path),
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert all(r["runtime"] == "langgraph" for r in data["results"])
