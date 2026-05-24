"""Tests for arc audit query command (Phase 22.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.audit.key_manager import sign_audit_record
from agent_runtime_cockpit.audit.streaming_verifier import GENESIS
from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.protocol._bypass import PolicyBypassReason


@pytest.fixture
def audit_chain_with_bypass_warnings(tmp_path: Path) -> tuple[Path, str]:
    """Create a synthetic audit chain with mixed event types including bypass warnings.

    Returns:
        Tuple of (chain_path, run_id)

    """
    run_id = "run_test_query_123"
    chain_path = tmp_path / ".arc" / "audit" / f"{run_id}.audit.jsonl"
    chain_path.parent.mkdir(parents=True, exist_ok=True)

    key = b"test-hmac-key-32-bytes-long!!"
    prev_hash = GENESIS

    # Create mixed events: bypass warnings with different surfaces, and other event types
    events = [
        # Bypass warning with provider_call surface
        {
            "schema_version": 2,
            "type": "POLICY_BYPASS_WARNING",
            "timestamp": "2026-05-23T08:00:00Z",
            "run_id": run_id,
            "sequence": 0,
            "data": {
                "policy_id": "trust_gate",
                "bypass_reason": PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN.value,
                "surface": "provider_call",
                "surface_identifier": "custom_provider.execute",
                "suggested_remediation": "Instrument the provider",
            },
        },
        # Bypass warning with tool_execution surface
        {
            "schema_version": 2,
            "type": "POLICY_BYPASS_WARNING",
            "timestamp": "2026-05-23T08:00:01Z",
            "run_id": run_id,
            "sequence": 1,
            "data": {
                "policy_id": "shell_gate",
                "bypass_reason": PolicyBypassReason.UNINSTRUMENTED_TOOL.value,
                "surface": "tool_execution",
                "surface_identifier": "custom_tool.run",
                "suggested_remediation": "Use instrumented tool",
            },
        },
        # Another bypass warning with provider_call surface
        {
            "schema_version": 2,
            "type": "POLICY_BYPASS_WARNING",
            "timestamp": "2026-05-23T08:00:02Z",
            "run_id": run_id,
            "sequence": 2,
            "data": {
                "policy_id": "network_gate",
                "bypass_reason": PolicyBypassReason.CUSTOM_HTTP_CLIENT.value,
                "surface": "provider_call",
                "surface_identifier": "custom_http.request",
                "suggested_remediation": "Use instrumented HTTP client",
            },
        },
        # Different event type (RUN_STARTED)
        {
            "schema_version": 2,
            "type": "RUN_STARTED",
            "timestamp": "2026-05-23T08:00:03Z",
            "run_id": run_id,
            "sequence": 3,
            "data": {
                "workflow_id": "test_workflow",
                "runtime": "swarmgraph",
            },
        },
    ]

    with open(chain_path, "w", encoding="utf-8") as f:
        for i, event in enumerate(events):
            record_hash, signature = sign_audit_record(event, key, prev_hash)
            record = {
                "seq": i,
                "event": event,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "signature": signature,
            }
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            prev_hash = record_hash

    return chain_path, run_id


def test_audit_query_filter_isolation(audit_chain_with_bypass_warnings, tmp_path):
    """Test 1: Filter isolation - --kind filter works correctly.

    Verifies that querying by --kind POLICY_BYPASS_WARNING returns only
    bypass warnings and excludes other event types.
    """
    chain_path, run_id = audit_chain_with_bypass_warnings
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "audit",
            "query",
            run_id,
            "--kind",
            "POLICY_BYPASS_WARNING",
            "--chain",
            str(chain_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    output = json.loads(result.stdout)
    assert output["ok"] is True
    assert output["data"]["run_id"] == run_id
    assert output["data"]["filters"]["kind"] == "POLICY_BYPASS_WARNING"
    assert output["data"]["filters"]["surface"] is None

    # Should return 3 bypass warnings (excluding the RUN_STARTED event)
    assert output["data"]["matched_count"] == 3
    assert len(output["data"]["events"]) == 3

    # All returned events should be POLICY_BYPASS_WARNING
    for event in output["data"]["events"]:
        assert event["type"] == "POLICY_BYPASS_WARNING"


def test_audit_query_filter_composition(audit_chain_with_bypass_warnings, tmp_path):
    """Test 2: Filter composition - --kind and --surface filters compose correctly.

    Verifies that combining --kind POLICY_BYPASS_WARNING with --surface provider_call
    returns only bypass warnings from provider calls (2 out of 3 bypass warnings).
    """
    chain_path, run_id = audit_chain_with_bypass_warnings
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "audit",
            "query",
            run_id,
            "--kind",
            "POLICY_BYPASS_WARNING",
            "--surface",
            "provider_call",
            "--chain",
            str(chain_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    output = json.loads(result.stdout)
    assert output["ok"] is True
    assert output["data"]["run_id"] == run_id
    assert output["data"]["filters"]["kind"] == "POLICY_BYPASS_WARNING"
    assert output["data"]["filters"]["surface"] == "provider_call"

    # Should return 2 bypass warnings with provider_call surface
    # (excluding the tool_execution one)
    assert output["data"]["matched_count"] == 2
    assert len(output["data"]["events"]) == 2

    # All returned events should be POLICY_BYPASS_WARNING with provider_call surface
    for event in output["data"]["events"]:
        assert event["type"] == "POLICY_BYPASS_WARNING"
        assert event["data"]["surface"] == "provider_call"
