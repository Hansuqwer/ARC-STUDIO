"""HMAC-authenticated audit chain writer and verifier."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from .key_manager import AuditKeyManager, sign_audit_record, verify_audit_signature

log = logging.getLogger(__name__)

GENESIS = "GENESIS"


class HmacAuditChainWriter:
    """Append-only HMAC-authenticated audit chain writer.

    Production decision required before merge: reuse vendored swarm_shared.audit or
    explicitly ship separate ARC/SwarmGraph verifiers. Do not silently reinvent
    canonicalization. Writer resumes _prev_hash/_seq from existing files before append.
    """

    def __init__(self, path: Path, key_manager: AuditKeyManager) -> None:
        self.path = path
        self.key_manager = key_manager
        self._seq, self._prev_hash = self._load_tail_state()

    def _load_tail_state(self) -> tuple[int, str]:
        if not self.path.exists():
            return 0, GENESIS
        last: dict[str, Any] | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last = json.loads(line)
        if last is None:
            return 0, GENESIS
        return int(last["seq"]) + 1, str(last["record_hash"])

    def append(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Append an event to the audit chain. Returns the signed record, or None if no key."""
        key, status = self.key_manager.get_key()
        if key is None:
            log.warning("No audit key available — skipping HMAC signing for seq %d", self._seq)
            return None
        record_hash, signature = sign_audit_record(event, key, self._prev_hash)
        record = {
            "seq": self._seq,
            "event": event,
            "prev_hash": self._prev_hash,
            "record_hash": record_hash,
            "signature": signature,
            "key_source": status.source,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            f.flush()
        self._prev_hash = record_hash
        self._seq += 1
        return record


def verify_hmac_chain(chain_path: Path, key: bytes) -> tuple[bool, str]:
    """Verify an HMAC-signed audit chain.

    Returns (ok, reason). Walks the chain and verifies each record's signature
    and chain hash continuity.
    """
    if not chain_path.exists():
        return False, f"Chain file not found: {chain_path}"
    lines = chain_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return True, "empty chain"
    prev_hash = GENESIS
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
        if stored_prev != prev_hash:
            return False, f"chain broken at seq {i}: prev_hash mismatch"
        if not verify_audit_signature(event, signature, key, prev_hash):
            return False, f"signature invalid at seq {i}"
        prev_hash = stored_hash
    count = len([l for l in lines if l.strip()])
    return True, f"verified {count} records"
