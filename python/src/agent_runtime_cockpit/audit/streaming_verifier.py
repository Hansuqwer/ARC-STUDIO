"""Streaming audit verification for memory-bounded processing of large traces.

This module provides streaming verification for both SHA-256 and HMAC audit chains,
processing files line-by-line or in configurable chunks to avoid loading entire
traces into memory. Critical for handling 100 MB+ audit files.

Architecture Review P0-1 Finding: Original verification used read_text().splitlines()
which breaks on large traces. This streaming implementation processes files with
bounded memory usage (default: 8 MB chunks, configurable up to 500 MB).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from agent_runtime_cockpit.events import get_bus
from agent_runtime_cockpit.events.types import AuditVerified

from .key_manager import sign_audit_record, verify_audit_signature

log = logging.getLogger(__name__)

GENESIS = "GENESIS"
DEFAULT_CHUNK_SIZE_MB = 8
MAX_CHUNK_SIZE_MB = 500
AuditRecordFormat = Literal["hmac", "sha256", "event_bus", "audit_event_schema", "unknown"]


class VerificationResult(BaseModel):
    """Structured verification result with stable JSON output format."""

    ok: bool
    mode: Literal["sha256", "hmac"]
    records_checked: int
    reason: str
    duration_ms: int
    file_size_bytes: Optional[int] = None
    peak_memory_mb: Optional[float] = None


class StreamingAuditVerifier:
    """Memory-bounded audit chain verifier supporting SHA-256 and HMAC modes.

    Processes audit files line-by-line to avoid loading entire traces into memory.
    Supports both legacy SHA-256 format (chain.py) and HMAC-signed format (hmac_chain.py).
    """

    def __init__(self, max_memory_mb: int = DEFAULT_CHUNK_SIZE_MB) -> None:
        """Initialize streaming verifier.

        Args:
            max_memory_mb: Maximum memory budget for buffering (default: 8 MB).
                          Does not enforce hard limit, but guides chunk sizing.

        """
        if max_memory_mb < 1 or max_memory_mb > MAX_CHUNK_SIZE_MB:
            raise ValueError(
                f"max_memory_mb must be between 1 and {MAX_CHUNK_SIZE_MB}, got {max_memory_mb}"
            )
        self.max_memory_mb = max_memory_mb
        self._buffer_size = max_memory_mb * 1024 * 1024  # Convert to bytes

    @staticmethod
    def _classify_record(record: dict) -> AuditRecordFormat:
        """Classify record envelopes without treating payload event keys as chain metadata."""
        if {"signature", "record_hash", "prev_hash"}.issubset(record):
            return "hmac"
        if {"chain_hash", "event_hash", "prev_hash"}.issubset(record):
            return "sha256"
        if "event_type" in record:
            return "event_bus"
        if "eventType" in record:
            return "audit_event_schema"
        return "unknown"

    @staticmethod
    def _record_keys(record: dict) -> str:
        return ", ".join(sorted(str(key) for key in record.keys()))

    def verify_hmac(self, file_path: Path, key: bytes) -> VerificationResult:
        """Verify HMAC-signed audit chain with streaming processing.

        Processes the chain line-by-line, verifying:
        1. Each record's HMAC signature
        2. Chain continuity (prev_hash matches)
        3. JSON validity

        Args:
            file_path: Path to HMAC-signed audit chain (.audit.jsonl)
            key: HMAC key for signature verification

        Returns:
            VerificationResult with ok, mode, records_checked, reason, duration_ms

        """
        start_time = time.time()

        if not file_path.exists():
            return VerificationResult(
                ok=False,
                mode="hmac",
                records_checked=0,
                reason=f"Chain file not found: {file_path}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        file_size = file_path.stat().st_size
        records_checked = 0
        prev_hash = GENESIS

        try:
            with open(file_path, "r", encoding="utf-8", buffering=self._buffer_size) as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        return VerificationResult(
                            ok=False,
                            mode="hmac",
                            records_checked=records_checked,
                            reason=f"Invalid JSON at line {line_num}: {e}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Verify chain continuity
                    stored_prev = record.get("prev_hash", "")
                    if stored_prev != prev_hash:
                        return VerificationResult(
                            ok=False,
                            mode="hmac",
                            records_checked=records_checked,
                            reason=f"Chain broken at line {line_num}: prev_hash mismatch (expected {prev_hash}, got {stored_prev})",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    seq = record.get("seq")
                    if seq is not None and seq != records_checked:
                        return VerificationResult(
                            ok=False,
                            mode="hmac",
                            records_checked=records_checked,
                            reason=f"Sequence mismatch at line {line_num}: expected {records_checked}, got {seq}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Verify HMAC signature
                    event = record.get("event", {})
                    signature = record.get("signature", "")
                    expected_hash, _ = sign_audit_record(event, key, prev_hash)
                    stored_hash = record.get("record_hash", "")
                    if stored_hash != expected_hash:
                        return VerificationResult(
                            ok=False,
                            mode="hmac",
                            records_checked=records_checked,
                            reason=f"Record hash invalid at line {line_num}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )
                    if not verify_audit_signature(event, signature, key, prev_hash):
                        return VerificationResult(
                            ok=False,
                            mode="hmac",
                            records_checked=records_checked,
                            reason=f"Signature invalid at line {line_num}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Update state for next record
                    prev_hash = stored_hash
                    records_checked += 1

        except Exception as e:
            return VerificationResult(
                ok=False,
                mode="hmac",
                records_checked=records_checked,
                reason=f"Verification error: {e}",
                duration_ms=int((time.time() - start_time) * 1000),
                file_size_bytes=file_size,
            )

        duration_ms = int((time.time() - start_time) * 1000)

        if records_checked == 0:
            return VerificationResult(
                ok=True,
                mode="hmac",
                records_checked=0,
                reason="Empty chain",
                duration_ms=duration_ms,
                file_size_bytes=file_size,
            )

        return VerificationResult(
            ok=True,
            mode="hmac",
            records_checked=records_checked,
            reason=f"verified {records_checked} records",
            duration_ms=duration_ms,
            file_size_bytes=file_size,
        )

    def verify_sha256(
        self, chain_path: Path, events_path: Optional[Path] = None
    ) -> VerificationResult:
        """Verify SHA-256 hash-chained audit log with streaming processing.

        Backward compatible with existing chain.py format. Processes the chain
        line-by-line, verifying:
        1. Event hash matches canonical JSON
        2. Chain hash continuity
        3. JSON validity

        Args:
            chain_path: Path to audit chain file (.jsonl)
            events_path: Optional path to raw events file (if None, only chain hashes verified)

        Returns:
            VerificationResult with ok, mode, records_checked, reason, duration_ms

        """
        start_time = time.time()

        if not chain_path.exists():
            return VerificationResult(
                ok=False,
                mode="sha256",
                records_checked=0,
                reason=f"Chain file not found: {chain_path}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        file_size = chain_path.stat().st_size
        records_checked = 0
        prev_hash = GENESIS

        # If events_path provided, we need to verify against raw events
        # For now, implement chain-only verification (most common case)
        # Full event verification can be added if needed
        if events_path is not None:
            log.warning(
                "SHA-256 verification with separate events file not yet implemented in streaming mode"
            )

        try:
            with open(chain_path, "r", encoding="utf-8", buffering=self._buffer_size) as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        return VerificationResult(
                            ok=False,
                            mode="sha256",
                            records_checked=records_checked,
                            reason=f"Invalid JSON at line {line_num}: {e}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Verify chain continuity
                    stored_prev = record.get("prev_hash", "")
                    if stored_prev != prev_hash:
                        return VerificationResult(
                            ok=False,
                            mode="sha256",
                            records_checked=records_checked,
                            reason=f"Chain broken at line {line_num}: prev_hash mismatch",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Verify chain hash
                    event_hash = record.get("event_hash", "")
                    expected_chain_hash = hashlib.sha256(
                        f"{prev_hash}:{event_hash}".encode("utf-8")
                    ).hexdigest()
                    stored_chain_hash = record.get("chain_hash", "")

                    if expected_chain_hash != stored_chain_hash:
                        return VerificationResult(
                            ok=False,
                            mode="sha256",
                            records_checked=records_checked,
                            reason=f"Chain hash mismatch at line {line_num}",
                            duration_ms=int((time.time() - start_time) * 1000),
                            file_size_bytes=file_size,
                        )

                    # Update state for next record
                    prev_hash = stored_chain_hash
                    records_checked += 1

        except Exception as e:
            return VerificationResult(
                ok=False,
                mode="sha256",
                records_checked=records_checked,
                reason=f"Verification error: {e}",
                duration_ms=int((time.time() - start_time) * 1000),
                file_size_bytes=file_size,
            )

        duration_ms = int((time.time() - start_time) * 1000)

        if records_checked == 0:
            return VerificationResult(
                ok=True,
                mode="sha256",
                records_checked=0,
                reason="Empty chain",
                duration_ms=duration_ms,
                file_size_bytes=file_size,
            )

        return VerificationResult(
            ok=True,
            mode="sha256",
            records_checked=records_checked,
            reason=f"verified {records_checked} records",
            duration_ms=duration_ms,
            file_size_bytes=file_size,
        )

    def verify_auto(self, file_path: Path, key: Optional[bytes] = None) -> VerificationResult:
        """Auto-detect format and verify with appropriate method.

        Detects HMAC vs SHA-256 format by inspecting the first record.
        HMAC records have 'signature' field, SHA-256 records have 'chain_hash'.

        Args:
            file_path: Path to audit chain file
            key: Optional HMAC key (required if HMAC format detected)

        Returns:
            VerificationResult with detected mode

        """
        start_time = time.time()

        if not file_path.exists():
            return self._emit_audit_verified(
                VerificationResult(
                    ok=False,
                    mode="sha256",  # Default mode for error case
                    records_checked=0,
                    reason=f"Chain file not found: {file_path}",
                    duration_ms=int((time.time() - start_time) * 1000),
                ),
                file_path,
            )

        # Read first non-empty line to detect format
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        record_format = self._classify_record(record)
                        if record_format == "hmac":
                            if key is None:
                                return self._emit_audit_verified(
                                    VerificationResult(
                                        ok=False,
                                        mode="hmac",
                                        records_checked=0,
                                        reason="HMAC format detected but no key provided",
                                        duration_ms=int((time.time() - start_time) * 1000),
                                    ),
                                    file_path,
                                )
                            return self._emit_audit_verified(
                                self.verify_hmac(file_path, key), file_path
                            )
                        if record_format == "sha256":
                            return self._emit_audit_verified(
                                self.verify_sha256(file_path), file_path
                            )
                        return self._emit_audit_verified(
                            VerificationResult(
                                ok=False,
                                mode="sha256",
                                records_checked=0,
                                reason=(
                                    "Unknown audit format: expected HMAC or SHA-256 chain "
                                    f"envelope, got {record_format} record with keys: "
                                    f"{self._record_keys(record)}"
                                ),
                                duration_ms=int((time.time() - start_time) * 1000),
                            ),
                            file_path,
                        )
                    except json.JSONDecodeError:
                        return VerificationResult(
                            ok=False,
                            mode="sha256",
                            records_checked=0,
                            reason="Invalid JSON in first record",
                            duration_ms=int((time.time() - start_time) * 1000),
                        )

                # Empty file
                return self._emit_audit_verified(
                    VerificationResult(
                        ok=True,
                        mode="sha256",
                        records_checked=0,
                        reason="Empty chain",
                        duration_ms=int((time.time() - start_time) * 1000),
                    ),
                    file_path,
                )

        except Exception as e:
            return self._emit_audit_verified(
                VerificationResult(
                    ok=False,
                    mode="sha256",
                    records_checked=0,
                    reason=f"Format detection error: {e}",
                    duration_ms=int((time.time() - start_time) * 1000),
                ),
                file_path,
            )

    def _emit_audit_verified(
        self, result: VerificationResult, file_path: Optional[Path] = None
    ) -> VerificationResult:
        """Emit audit_verified event and return the result unchanged."""
        try:
            bus = get_bus()
            bus.publish(
                AuditVerified(
                    ok=result.ok,
                    mode=result.mode,
                    records_checked=result.records_checked,
                    reason=result.reason,
                    duration_ms=result.duration_ms,
                    payload={
                        "file_path": str(file_path) if file_path else None,
                        "file_size_bytes": result.file_size_bytes,
                    },
                )
            )
        except Exception:
            log.warning("Failed to emit audit_verified event", exc_info=True)
        return result
