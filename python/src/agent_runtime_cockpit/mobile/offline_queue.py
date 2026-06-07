"""Offline queue for ARC Mobile Runtime (Phase 8).

Durable, bounded queue for actions captured while offline. Entries are stored HASH-ONLY:
the queue persists a SHA-256 of the payload plus minimal redacted metadata (capability id,
byte size, timestamps) — never the raw payload — so the at-rest file leaks no sensitive
data. Retention is enforced by per-entry TTL and a max-entry cap (FIFO eviction). Integrity
of a replayed payload is verified against the stored hash. Deterministic, offline, no network.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _hash_payload(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class QueueEntry:
    """A queued action — hash-only (no raw payload retained)."""

    id: str
    capability_id: str
    payload_hash: str
    byte_size: int
    created_at: str
    expires_at: str | None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and datetime.fromisoformat(self.expires_at) <= now

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "capability_id": self.capability_id,
            "payload_hash": self.payload_hash,
            "byte_size": self.byte_size,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class OfflineQueue:
    """Durable, bounded, hash-only offline action queue with TTL retention."""

    def __init__(
        self,
        path: Path | None = None,
        max_entries: int = 1000,
        default_ttl_seconds: int | None = None,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be > 0")
        self._path = Path(path) if path else None
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._entries: deque[QueueEntry] = deque()
        if self._path and self._path.exists():
            self._load()

    def enqueue(
        self,
        capability_id: str,
        payload: Any,
        ttl_seconds: int | None = None,
        now: datetime | None = None,
    ) -> QueueEntry:
        now = now or _now()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = (now + timedelta(seconds=ttl)).isoformat() if ttl is not None else None
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
        entry = QueueEntry(
            id=uuid.uuid4().hex,
            capability_id=capability_id,
            payload_hash=_hash_payload(payload),
            byte_size=len(raw),
            created_at=now.isoformat(),
            expires_at=expires_at,
        )
        self._entries.append(entry)
        # FIFO eviction when over the retention cap
        while len(self._entries) > self.max_entries:
            self._entries.popleft()
        self._persist()
        return entry

    def gc(self, now: datetime | None = None) -> int:
        """Drop expired entries. Returns the number removed."""
        now = now or _now()
        before = len(self._entries)
        self._entries = deque(e for e in self._entries if not e.is_expired(now))
        removed = before - len(self._entries)
        if removed:
            self._persist()
        return removed

    def flush(self, now: datetime | None = None) -> list[QueueEntry]:
        """Return all ready (non-expired) entries in FIFO order and clear the queue
        (expired entries are dropped, never returned)."""
        now = now or _now()
        ready = [e for e in self._entries if not e.is_expired(now)]
        self._entries.clear()
        self._persist()
        return ready

    def verify(self, entry: QueueEntry, payload: Any) -> bool:
        """Integrity check: does a replayed payload match the stored hash?"""
        return _hash_payload(payload) == entry.payload_hash

    def pending(self, now: datetime | None = None) -> list[QueueEntry]:
        now = now or _now()
        return [e for e in self._entries if not e.is_expired(now)]

    def __len__(self) -> int:
        return len(self._entries)

    # ── persistence (hash-only) ──
    def _persist(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "entries": [e.as_dict() for e in self._entries]}
        self._path.write_text(json.dumps(payload), encoding="utf-8")

    def _load(self) -> None:
        assert self._path is not None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for raw in data.get("entries", []):
            self._entries.append(QueueEntry(**raw))
