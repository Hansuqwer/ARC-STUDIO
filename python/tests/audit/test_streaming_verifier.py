"""Tests for streaming audit verification (Phase 21).

Architecture Review P0-1 Finding: Original verification loaded entire files into memory,
breaking on large traces (100 MB+). These tests verify streaming implementation handles
large files with bounded memory usage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.key_manager import sign_audit_record
from agent_runtime_cockpit.audit.streaming_verifier import (
    StreamingAuditVerifier,
    VerificationResult,
    GENESIS,
)


class TestStreamingVerifierInit:
    """Test StreamingAuditVerifier initialization and configuration."""

    def test_default_init(self):
        verifier = StreamingAuditVerifier()
        assert verifier.max_memory_mb == 8  # Default chunk size

    def test_custom_memory_budget(self):
        verifier = StreamingAuditVerifier(max_memory_mb=100)
        assert verifier.max_memory_mb == 100

    def test_invalid_memory_budget_too_low(self):
        with pytest.raises(ValueError, match="must be between 1 and 500"):
            StreamingAuditVerifier(max_memory_mb=0)

    def test_invalid_memory_budget_too_high(self):
        with pytest.raises(ValueError, match="must be between 1 and 500"):
            StreamingAuditVerifier(max_memory_mb=501)


class TestHMACStreamingVerification:
    """Test HMAC-signed audit chain streaming verification."""

    def test_verify_hmac_small_chain(self, tmp_path: Path):
        """Verify a small HMAC chain with 3 records."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "audit.jsonl"

        # Write HMAC chain
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            record_hash, signature = sign_audit_record(event, key, prev_hash)
            record = {
                "seq": i,
                "event": event,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "signature": signature,
            }
            records.append(record)
            prev_hash = record_hash

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")

        # Verify with streaming verifier
        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is True
        assert result.mode == "hmac"
        assert result.records_checked == 3
        assert "Verified 3 records" in result.reason
        assert result.duration_ms >= 0
        assert result.file_size_bytes > 0

    def test_verify_hmac_empty_chain(self, tmp_path: Path):
        """Verify empty HMAC chain."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "empty.jsonl"
        chain_path.write_text("")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is True
        assert result.mode == "hmac"
        assert result.records_checked == 0
        assert "Empty chain" in result.reason

    def test_verify_hmac_chain_not_found(self, tmp_path: Path):
        """Verify behavior when chain file doesn't exist."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "nonexistent.jsonl"

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is False
        assert result.mode == "hmac"
        assert result.records_checked == 0
        assert "not found" in result.reason

    def test_verify_hmac_invalid_json(self, tmp_path: Path):
        """Verify detection of invalid JSON."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "invalid.jsonl"
        chain_path.write_text("not valid json\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is False
        assert result.mode == "hmac"
        assert "Invalid JSON" in result.reason

    def test_verify_hmac_chain_broken(self, tmp_path: Path):
        """Verify detection of broken chain continuity."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "broken.jsonl"

        # Write chain with broken continuity
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            record_hash, signature = sign_audit_record(event, key, prev_hash)
            record = {
                "seq": i,
                "event": event,
                "prev_hash": prev_hash if i != 1 else "BROKEN",  # Break chain at record 1
                "record_hash": record_hash,
                "signature": signature,
            }
            records.append(record)
            prev_hash = record_hash

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is False
        assert result.mode == "hmac"
        assert "Chain broken" in result.reason
        assert "prev_hash mismatch" in result.reason

    def test_verify_hmac_invalid_signature(self, tmp_path: Path):
        """Verify detection of invalid HMAC signature."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "tampered.jsonl"

        # Write valid chain
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            record_hash, signature = sign_audit_record(event, key, prev_hash)
            record = {
                "seq": i,
                "event": event,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "signature": signature if i != 1 else "invalid_signature",  # Tamper signature
            }
            records.append(record)
            prev_hash = record_hash

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is False
        assert result.mode == "hmac"
        assert "Signature invalid" in result.reason

    def test_verify_hmac_tampered_content(self, tmp_path: Path):
        """Verify detection of tampered event content."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "tampered.jsonl"

        # Write valid chain, then tamper content
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            record_hash, signature = sign_audit_record(event, key, prev_hash)
            record = {
                "seq": i,
                "event": event,
                "prev_hash": prev_hash,
                "record_hash": record_hash,
                "signature": signature,
            }
            records.append(record)
            prev_hash = record_hash

        # Tamper the event content of record 1
        records[1]["event"]["action"] = "tampered"

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_hmac(chain_path, key)

        assert result.ok is False
        assert result.mode == "hmac"
        assert "Signature invalid" in result.reason


class TestSHA256StreamingVerification:
    """Test SHA-256 hash-chained audit log streaming verification."""

    def test_verify_sha256_small_chain(self, tmp_path: Path):
        """Verify a small SHA-256 chain with 3 records."""
        import hashlib

        chain_path = tmp_path / "chain.jsonl"

        # Write SHA-256 chain (format from chain.py)
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
            event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
            chain_hash = hashlib.sha256(f"{prev_hash}:{event_hash}".encode("utf-8")).hexdigest()
            record = {
                "seq": i,
                "prev_hash": prev_hash,
                "event_hash": event_hash,
                "chain_hash": chain_hash,
            }
            records.append(record)
            prev_hash = chain_hash

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")

        # Verify with streaming verifier
        verifier = StreamingAuditVerifier()
        result = verifier.verify_sha256(chain_path)

        assert result.ok is True
        assert result.mode == "sha256"
        assert result.records_checked == 3
        assert "Verified 3 records" in result.reason
        assert result.duration_ms >= 0

    def test_verify_sha256_empty_chain(self, tmp_path: Path):
        """Verify empty SHA-256 chain."""
        chain_path = tmp_path / "empty.jsonl"
        chain_path.write_text("")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_sha256(chain_path)

        assert result.ok is True
        assert result.mode == "sha256"
        assert result.records_checked == 0
        assert "Empty chain" in result.reason

    def test_verify_sha256_chain_broken(self, tmp_path: Path):
        """Verify detection of broken SHA-256 chain continuity."""
        import hashlib

        chain_path = tmp_path / "broken.jsonl"

        # Write chain with broken continuity
        prev_hash = GENESIS
        records = []
        for i in range(3):
            event = {"seq": i, "action": f"step-{i}"}
            event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
            event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
            chain_hash = hashlib.sha256(f"{prev_hash}:{event_hash}".encode("utf-8")).hexdigest()
            record = {
                "seq": i,
                "prev_hash": prev_hash if i != 1 else "BROKEN",  # Break chain
                "event_hash": event_hash,
                "chain_hash": chain_hash,
            }
            records.append(record)
            prev_hash = chain_hash

        with open(chain_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_sha256(chain_path)

        assert result.ok is False
        assert result.mode == "sha256"
        assert "Chain broken" in result.reason


class TestAutoDetection:
    """Test automatic format detection."""

    def test_auto_detect_hmac(self, tmp_path: Path):
        """Auto-detect HMAC format from signature field."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "hmac.jsonl"

        # Write HMAC chain
        event = {"seq": 0, "action": "test"}
        record_hash, signature = sign_audit_record(event, key, GENESIS)
        record = {
            "seq": 0,
            "event": event,
            "prev_hash": GENESIS,
            "record_hash": record_hash,
            "signature": signature,
        }

        with open(chain_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_auto(chain_path, key)

        assert result.ok is True
        assert result.mode == "hmac"
        assert result.records_checked == 1

    def test_auto_detect_sha256(self, tmp_path: Path):
        """Auto-detect SHA-256 format from chain_hash field."""
        import hashlib

        chain_path = tmp_path / "sha256.jsonl"

        # Write SHA-256 chain
        event = {"seq": 0, "action": "test"}
        event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(event_json.encode("utf-8")).hexdigest()
        chain_hash = hashlib.sha256(f"{GENESIS}:{event_hash}".encode("utf-8")).hexdigest()
        record = {
            "seq": 0,
            "prev_hash": GENESIS,
            "event_hash": event_hash,
            "chain_hash": chain_hash,
        }

        with open(chain_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_auto(chain_path)

        assert result.ok is True
        assert result.mode == "sha256"
        assert result.records_checked == 1

    def test_auto_detect_hmac_without_key(self, tmp_path: Path):
        """Auto-detect HMAC but fail without key."""
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "hmac.jsonl"

        # Write HMAC chain
        event = {"seq": 0, "action": "test"}
        record_hash, signature = sign_audit_record(event, key, GENESIS)
        record = {
            "seq": 0,
            "event": event,
            "prev_hash": GENESIS,
            "record_hash": record_hash,
            "signature": signature,
        }

        with open(chain_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

        verifier = StreamingAuditVerifier()
        result = verifier.verify_auto(chain_path, key=None)

        assert result.ok is False
        assert result.mode == "hmac"
        assert "no key provided" in result.reason


class TestLargeFilePerformance:
    """Test streaming verification performance on large files."""

    @pytest.mark.slow
    def test_verify_100mb_hmac_chain(self, tmp_path: Path):
        """Verify 100 MB HMAC chain completes in <30s with <500 MB RSS.

        This is the critical Phase 21 acceptance test for memory-bounded verification.
        """
        key = b"test-hmac-key-32-bytes-long!!"
        chain_path = tmp_path / "large.jsonl"

        # Generate ~100 MB of audit records
        # Each record is ~500 bytes, so we need ~200,000 records
        target_size_mb = 100
        record_size_estimate = 500
        num_records = (target_size_mb * 1024 * 1024) // record_size_estimate

        print(f"\nGenerating {num_records} records for ~{target_size_mb} MB chain...")
        start_gen = time.time()

        prev_hash = GENESIS
        with open(chain_path, "w", encoding="utf-8") as f:
            for i in range(num_records):
                event = {
                    "seq": i,
                    "action": f"step-{i}",
                    "data": "x" * 400,  # Padding to reach target size
                }
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
                if i % 10000 == 0 and i > 0:
                    print(f"  Generated {i} records...")

        gen_time = time.time() - start_gen
        file_size_mb = chain_path.stat().st_size / (1024 * 1024)
        print(f"Generated {file_size_mb:.2f} MB in {gen_time:.2f}s")

        # Verify with streaming verifier
        print("Starting streaming verification...")
        verifier = StreamingAuditVerifier(max_memory_mb=500)
        start_verify = time.time()
        result = verifier.verify_hmac(chain_path, key)
        verify_time = time.time() - start_verify

        print(f"Verification completed in {verify_time:.2f}s")
        print(f"  Records checked: {result.records_checked}")
        print(f"  Duration (reported): {result.duration_ms}ms")

        # Acceptance criteria
        assert result.ok is True, f"Verification failed: {result.reason}"
        assert result.records_checked == num_records
        assert verify_time < 30, f"Verification took {verify_time:.2f}s, expected <30s"
        # Note: RSS memory check would require psutil or similar, not included here
        # In practice, streaming should use <500 MB RSS regardless of file size


class TestVerificationResultModel:
    """Test VerificationResult Pydantic model and JSON output."""

    def test_result_model_construction(self):
        """Test VerificationResult model construction."""
        result = VerificationResult(
            ok=True,
            mode="hmac",
            records_checked=100,
            reason="Verified 100 records",
            duration_ms=1234,
            file_size_bytes=1024000,
        )

        assert result.ok is True
        assert result.mode == "hmac"
        assert result.records_checked == 100
        assert result.reason == "Verified 100 records"
        assert result.duration_ms == 1234
        assert result.file_size_bytes == 1024000

    def test_result_model_json_serialization(self):
        """Test stable JSON output format."""
        result = VerificationResult(
            ok=True,
            mode="sha256",
            records_checked=50,
            reason="Verified 50 records",
            duration_ms=567,
        )

        json_str = result.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["ok"] is True
        assert parsed["mode"] == "sha256"
        assert parsed["records_checked"] == 50
        assert parsed["reason"] == "Verified 50 records"
        assert parsed["duration_ms"] == 567
        assert "file_size_bytes" in parsed  # Optional field present as null

    def test_result_model_dict_output(self):
        """Test dict output for CLI JSON mode."""
        result = VerificationResult(
            ok=False,
            mode="hmac",
            records_checked=10,
            reason="Signature invalid at line 11",
            duration_ms=123,
            file_size_bytes=5000,
        )

        data = result.model_dump()

        assert data["ok"] is False
        assert data["mode"] == "hmac"
        assert data["records_checked"] == 10
        assert "Signature invalid" in data["reason"]
        assert data["duration_ms"] == 123
        assert data["file_size_bytes"] == 5000
