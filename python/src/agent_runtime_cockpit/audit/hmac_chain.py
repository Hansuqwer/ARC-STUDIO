"""HMAC-authenticated audit chain writer and verifier."""

from __future__ import annotations

import json
import logging
import os
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows unsupported for this phase.
    fcntl = None  # type: ignore[assignment]

from .key_manager import (
    AuditKeyManager,
    AuditSigningError,
    legacy_sign_audit_record,
    sign_audit_record,
    verify_audit_signature,
    verify_legacy_audit_signature,
)

log = logging.getLogger(__name__)

GENESIS = "GENESIS"
CHECKPOINT_VERSION = 1


class AuditChainCorruptError(RuntimeError):
    """Raised when an existing audit chain cannot be safely extended."""


@dataclass(frozen=True)
class _TailState:
    seq: int
    prev_hash: str
    stat_signature: tuple[int, int, int] | None


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def checkpoint_path_for_chain(chain_path: Path) -> Path:
    return chain_path.with_name(f"{chain_path.name}.checkpoint.json")


def _checkpoint_signature(payload: dict[str, Any], key: bytes) -> str:
    encoded = _canonical_json(payload).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()


def _write_hmac_checkpoint(
    chain_path: Path,
    key: bytes,
    *,
    records: int,
    terminal_hash: str,
    updated_at: str,
) -> None:
    checkpoint_path = checkpoint_path_for_chain(chain_path)
    payload: dict[str, Any] = {
        "version": CHECKPOINT_VERSION,
        "chain_file": chain_path.name,
        "records": records,
        "terminal_hash": terminal_hash,
        "file_size_bytes": chain_path.stat().st_size,
        "updated_at": updated_at,
    }
    record = {**payload, "signature": _checkpoint_signature(payload, key)}
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = checkpoint_path.with_name(f".{checkpoint_path.name}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(_canonical_json(record) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, checkpoint_path)


def verify_hmac_checkpoint(
    chain_path: Path,
    key: bytes,
    *,
    records_checked: int,
    terminal_hash: str,
) -> tuple[bool, str]:
    checkpoint_path = checkpoint_path_for_chain(chain_path)
    if not checkpoint_path.exists():
        return True, "checkpoint absent"
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"checkpoint invalid: {exc}"
    signature = str(checkpoint.pop("signature", ""))
    if not signature:
        return False, "checkpoint unsigned"
    expected_signature = _checkpoint_signature(checkpoint, key)
    if not hmac.compare_digest(signature, expected_signature):
        return False, "checkpoint signature invalid"
    if checkpoint.get("version") != CHECKPOINT_VERSION:
        return False, f"checkpoint version invalid: {checkpoint.get('version')}"
    if checkpoint.get("chain_file") != chain_path.name:
        return False, "checkpoint chain_file mismatch"
    if checkpoint.get("records") != records_checked:
        return False, "checkpoint record count mismatch"
    if checkpoint.get("terminal_hash") != terminal_hash:
        return False, "checkpoint terminal hash mismatch"
    if checkpoint.get("file_size_bytes") != chain_path.stat().st_size:
        return False, "checkpoint file size mismatch"
    return True, "checkpoint verified"


class _FileLock:
    def __init__(self, file_obj: Any) -> None:
        self._file = file_obj

    def __enter__(self) -> None:
        if fcntl is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if fcntl is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)


class HmacAuditChainWriter:
    """Append-only HMAC-authenticated audit chain writer.

    Production decision required before merge: reuse vendored swarm_shared.audit or
    explicitly ship separate ARC/SwarmGraph verifiers. Do not silently reinvent
    canonicalization. Writer resumes _prev_hash/_seq from existing files before append.
    """

    def __init__(self, path: Path, key_manager: AuditKeyManager) -> None:
        self.path = path
        self.key_manager = key_manager
        tail = self._load_tail_state()
        self._seq = tail.seq
        self._prev_hash = tail.prev_hash
        self._stat_signature = tail.stat_signature

    def _stat_signature_for_path(self) -> tuple[int, int, int] | None:
        if not self.path.exists():
            return None
        stat = self.path.stat()
        return stat.st_size, stat.st_mtime_ns, stat.st_ino

    def _load_tail_state(self) -> _TailState:
        if not self.path.exists():
            return _TailState(0, GENESIS, None)
        last: dict[str, Any] | None = None
        expected_seq = 0
        with open(self.path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditChainCorruptError(f"invalid JSON at line {line_num}: {exc}") from exc
                seq = record.get("seq")
                record_hash = record.get("record_hash")
                if seq != expected_seq:
                    raise AuditChainCorruptError(
                        f"sequence mismatch at line {line_num}: expected {expected_seq}, got {seq}"
                    )
                if not isinstance(record_hash, str) or not record_hash:
                    raise AuditChainCorruptError(f"missing record_hash at line {line_num}")
                last = record
                expected_seq += 1
        if last is None:
            return _TailState(0, GENESIS, self._stat_signature_for_path())
        return _TailState(
            int(last["seq"]) + 1, str(last["record_hash"]), self._stat_signature_for_path()
        )

    def _current_tail_state(self) -> _TailState:
        stat_signature = self._stat_signature_for_path()
        if stat_signature == self._stat_signature:
            return _TailState(self._seq, self._prev_hash, self._stat_signature)
        return self._load_tail_state()

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Append an HMAC-signed event to the audit chain."""
        key, status = self.key_manager.get_key()
        if key is None:
            raise AuditSigningError(status.warning or "No audit key available")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a+", encoding="utf-8") as f:
            with _FileLock(f):
                tail = self._current_tail_state()
                self._seq = tail.seq
                self._prev_hash = tail.prev_hash
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                key_id = status.key_id or status.source
                record_hash, signature = sign_audit_record(
                    event,
                    key,
                    self._prev_hash,
                    seq=self._seq,
                    timestamp=timestamp,
                    key_id=key_id,
                )
                record = {
                    "seq": self._seq,
                    "event": event,
                    "prev_hash": self._prev_hash,
                    "record_hash": record_hash,
                    "signature": signature,
                    "timestamp": timestamp,
                    "key_id": key_id,
                    "key_source": status.source,
                }
                f.seek(0, os.SEEK_END)
                f.write(_canonical_json(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
                _write_hmac_checkpoint(
                    self.path,
                    key,
                    records=self._seq + 1,
                    terminal_hash=record_hash,
                    updated_at=timestamp,
                )
                self._prev_hash = record_hash
                self._seq += 1
                self._stat_signature = self._stat_signature_for_path()
        return record


def verify_hmac_chain(chain_path: Path, key: bytes) -> tuple[bool, str]:
    """Verify an HMAC-signed audit chain.

    Returns (ok, reason). Walks the chain and verifies each record's signature
    and chain hash continuity.
    """
    if not chain_path.exists():
        return False, f"Chain file not found: {chain_path}"
    content = chain_path.read_text(encoding="utf-8")
    if content and not content.endswith("\n"):
        return False, "partial trailing line"
    lines = content.splitlines()
    if not lines:
        return True, "empty chain"
    prev_hash = GENESIS
    records_checked = 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return False, f"invalid JSON at line {i}"
        event = record.get("event", {})
        signature = record.get("signature", "")
        stored_prev = record.get("prev_hash", "")
        stored_hash = record.get("record_hash", "")
        seq = record.get("seq")
        timestamp = str(record.get("timestamp", ""))
        key_id = str(record.get("key_id", ""))
        if not isinstance(seq, int) or seq != records_checked:
            return False, f"sequence mismatch at seq {records_checked}: got {seq}"
        if not signature or not stored_hash:
            return False, f"unsigned record at seq {records_checked}"
        if stored_prev != prev_hash:
            return False, f"chain broken at seq {records_checked}: prev_hash mismatch"
        signed_seq = seq if timestamp or key_id else None
        expected_hash, _ = sign_audit_record(
            event,
            key,
            prev_hash,
            seq=signed_seq,
            timestamp=timestamp,
            key_id=key_id,
        )
        if stored_hash != expected_hash:
            if timestamp or key_id:
                return False, f"record hash invalid at seq {records_checked}"
            legacy_hash, _ = legacy_sign_audit_record(event, key, prev_hash)
            if stored_hash != legacy_hash:
                return False, f"record hash invalid at seq {records_checked}"
            if not verify_legacy_audit_signature(event, signature, key, prev_hash):
                return False, f"signature invalid at seq {records_checked}"
            prev_hash = stored_hash
            records_checked += 1
            continue
        if not verify_audit_signature(
            event,
            signature,
            key,
            prev_hash,
            seq=signed_seq,
            timestamp=timestamp,
            key_id=key_id,
        ):
            return False, f"signature invalid at seq {records_checked}"
        prev_hash = stored_hash
        records_checked += 1
    ok, checkpoint_reason = verify_hmac_checkpoint(
        chain_path, key, records_checked=records_checked, terminal_hash=prev_hash
    )
    if not ok:
        return False, checkpoint_reason
    return True, f"verified {records_checked} records"
