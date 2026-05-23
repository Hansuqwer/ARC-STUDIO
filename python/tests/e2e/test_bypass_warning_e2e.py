"""
E2E smoke test for PolicyBypassWarning (Phase 22.1).

Tests the full end-to-end flow: emit → replay → query.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.security.enforcement import emit_policy_bypass_warning
from agent_runtime_cockpit.protocol._bypass import PolicyBypassReason
from agent_runtime_cockpit.audit.key_manager import sign_audit_record
from agent_runtime_cockpit.audit.streaming_verifier import (
    StreamingAuditVerifier,
    GENESIS,
)


def test_bypass_warning_e2e_emit_replay_query(tmp_path: Path):
    """
    E2E smoke test: emit → replay → query.

    Tests the full end-to-end flow:
    1. Emit a PolicyBypassWarning using emit_policy_bypass_warning()
    2. Write it to an audit chain with HMAC signing
    3. Replay the chain through the streaming verifier
    4. Query the warning using arc audit query command
    5. Verify the warning is returned correctly
    """
    run_id = "run_e2e_test_123"
    chain_path = tmp_path / ".arc" / "audit" / f"{run_id}.audit.jsonl"
    chain_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Emit a PolicyBypassWarning
    emitted_events = []

    def capture_event(run_id: str, event_type: str, data: dict) -> None:
        emitted_events.append((run_id, event_type, data))

    result = emit_policy_bypass_warning(
        run_id=run_id,
        sequence=0,
        policy_id="trust_gate",
        bypass_reason=PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN,
        surface="provider_call",
        surface_identifier="custom_provider.execute",
        suggested_remediation="Instrument the custom provider with enforcement hooks",
        emit_event=capture_event,
    )

    assert result is True, "Warning should be emitted"
    assert len(emitted_events) == 1, "Should emit exactly 1 event"
    assert emitted_events[0][1] == "POLICY_BYPASS_WARNING"

    # Step 2: Write to audit chain with HMAC signing
    key = b"test-hmac-key-32-bytes-long!!"
    prev_hash = GENESIS

    event = emitted_events[0][2]  # Get the emitted event data
    record_hash, signature = sign_audit_record(event, key, prev_hash)
    record = {
        "seq": 0,
        "event": event,
        "prev_hash": prev_hash,
        "record_hash": record_hash,
        "signature": signature,
    }

    with open(chain_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    # Step 3: Replay through streaming verifier
    verifier = StreamingAuditVerifier(max_memory_mb=100)
    verify_result = verifier.verify_hmac(chain_path, key)

    assert verify_result.ok is True, f"HMAC verification failed: {verify_result.reason}"
    assert verify_result.records_checked == 1, "Should verify 1 record"

    # Step 4: Query using arc audit query command
    runner = CliRunner()
    query_result = runner.invoke(
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

    assert query_result.exit_code == 0, f"Query command failed: {query_result.stdout}"

    # Step 5: Verify the warning is returned correctly
    output = json.loads(query_result.stdout)
    assert output["ok"] is True
    assert output["data"]["run_id"] == run_id
    assert output["data"]["matched_count"] == 1
    assert len(output["data"]["events"]) == 1

    returned_event = output["data"]["events"][0]
    assert returned_event["type"] == "POLICY_BYPASS_WARNING"
    assert returned_event["run_id"] == run_id
    assert returned_event["data"]["policy_id"] == "trust_gate"
    assert (
        returned_event["data"]["bypass_reason"] == PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN.value
    )
    assert returned_event["data"]["surface"] == "provider_call"
    assert returned_event["data"]["surface_identifier"] == "custom_provider.execute"
    assert "Instrument the custom provider" in returned_event["data"]["suggested_remediation"]

    print("✓ E2E smoke test passed: emit → replay → query")
    print("✓ Emitted 1 PolicyBypassWarning event")
    print("✓ HMAC verification passed")
    print("✓ Query returned 1 matching event")
