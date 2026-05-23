"""
Test audit verifier compatibility with PolicyBypassWarning events (Phase 22.1).

Verifies that the streaming audit verifier from Phase 21 can handle large traces
containing PolicyBypassWarning events without breaking memory budget constraints.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.key_manager import sign_audit_record
from agent_runtime_cockpit.audit.streaming_verifier import (
    StreamingAuditVerifier,
    GENESIS,
)
from agent_runtime_cockpit.protocol._bypass import PolicyBypassReason


@pytest.mark.slow
def test_verify_100mb_trace_with_bypass_warnings(tmp_path: Path):
    """
    Verify 100 MB trace with 10,000 PolicyBypassWarning events.

    This test ensures the streaming audit verifier from Phase 21 can handle
    traces containing the new PolicyBypassWarning event type without breaking
    memory budget constraints or HMAC validation.

    Acceptance criteria:
    - 100 MB trace with 10,000 bypass warnings
    - HMAC validation passes
    - Completes within Phase 21 budget (<30s, <500 MB RSS)
    """
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "bypass_warnings.jsonl"

    # Generate ~100 MB of audit records with PolicyBypassWarning events
    # Target: 10,000 events at ~10 KB each = 100 MB
    num_warnings = 10_000
    target_size_mb = 100
    record_size_estimate = (target_size_mb * 1024 * 1024) // num_warnings

    print(
        f"\nGenerating {num_warnings} PolicyBypassWarning events for ~{target_size_mb} MB trace..."
    )
    start_gen = time.time()

    prev_hash = GENESIS
    with open(chain_path, "w", encoding="utf-8") as f:
        for i in range(num_warnings):
            # Create PolicyBypassWarning event
            # Add padding to reach target size (~10 KB per event)
            padding_size = record_size_estimate - 500  # Reserve 500 bytes for structure
            event = {
                "schema_version": 2,
                "type": "POLICY_BYPASS_WARNING",
                "timestamp": f"2026-05-23T08:00:{i % 60:02d}Z",
                "run_id": f"run_test_{i // 100}",
                "sequence": i,
                "data": {
                    "policy_id": "trust_gate",
                    "bypass_reason": PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN.value,
                    "surface": "provider_call",
                    "surface_identifier": f"custom_provider_{i}.execute",
                    "suggested_remediation": f"Instrument the custom provider. {('x' * padding_size)}",
                    "parent_run_id": f"run_parent_{i // 100}" if i % 2 == 0 else None,
                },
            }

            # Sign and create audit record
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

            # Progress indicator
            if i % 1000 == 0 and i > 0:
                print(f"  Generated {i} warnings...")

    gen_time = time.time() - start_gen
    file_size_mb = chain_path.stat().st_size / (1024 * 1024)
    print(f"Generated {file_size_mb:.2f} MB in {gen_time:.2f}s")

    # Verify the file is approximately 100 MB
    assert 90 <= file_size_mb <= 110, f"Expected ~100 MB, got {file_size_mb:.2f} MB"

    # Verify with streaming verifier (Phase 21 budget: <500 MB RSS)
    print("Starting streaming verification...")
    verifier = StreamingAuditVerifier(max_memory_mb=500)
    start_verify = time.time()
    result = verifier.verify_hmac(chain_path, key)
    verify_time = time.time() - start_verify

    print(f"Verification completed in {verify_time:.2f}s")
    print(f"  Records checked: {result.records_checked}")
    print(f"  Duration (reported): {result.duration_ms}ms")

    # Acceptance criteria
    assert result.ok is True, f"HMAC verification failed: {result.reason}"
    assert result.records_checked == num_warnings, (
        f"Expected {num_warnings} records, verified {result.records_checked}"
    )
    assert verify_time < 30, (
        f"Verification took {verify_time:.2f}s, expected <30s (Phase 21 budget)"
    )

    print("✓ 100 MB trace with 10,000 bypass warnings verified successfully")
    print("✓ HMAC validation passed")
    print(f"✓ Completed within Phase 21 budget ({verify_time:.2f}s < 30s)")
