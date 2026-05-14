"""SHA-256 hash-chained audit log. Tamper-evident, append-only."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from typing import Any

GENESIS = "GENESIS"


def canonical_dumps(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class AuditChainWriter:
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self._fp = None
        self._seq = 0
        self._prev = GENESIS

    def __enter__(self) -> "AuditChainWriter":
        self._fp = self.path.open("a", encoding="utf-8")
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._fp:
            self._fp.flush()
            self._fp.close()

    def append(self, ag_event: dict[str, Any]) -> None:
        event_hash = sha256_hex(canonical_dumps(ag_event))
        chain_hash = sha256_hex(f"{self._prev}:{event_hash}".encode("utf-8"))
        record = {
            "seq": self._seq,
            "ts": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_hash": event_hash,
            "prev_hash": self._prev,
            "chain_hash": chain_hash,
        }
        self._fp.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._seq += 1
        self._prev = chain_hash


def verify(path: pathlib.Path, events_jsonl: pathlib.Path) -> tuple[bool, str]:
    """Return (ok, reason). Walks audit + raw events; flags any drift."""
    prev = GENESIS
    seq = 0
    chain_lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    event_lines = [json.loads(l) for l in events_jsonl.read_text().splitlines() if l.strip()]
    if len(chain_lines) != len(event_lines):
        return False, f"length mismatch: chain={len(chain_lines)} events={len(event_lines)}"
    for c, e in zip(chain_lines, event_lines):
        eh = sha256_hex(canonical_dumps(e))
        if eh != c["event_hash"]:
            return False, f"event_hash drift at seq {seq}"
        ch = sha256_hex(f"{prev}:{eh}".encode("utf-8"))
        if ch != c["chain_hash"]:
            return False, f"chain_hash drift at seq {seq}"
        prev = ch
        seq += 1
    return True, "ok"
