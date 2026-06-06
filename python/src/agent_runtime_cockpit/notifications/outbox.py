"""Local-only JSONL notification outbox with TTL/GC."""

from __future__ import annotations

import json
import time
from pathlib import Path

_DEFAULT_TTL_DAYS = 7


class NotificationOutbox:
    def __init__(self, path: Path, ttl_days: int = _DEFAULT_TTL_DAYS) -> None:
        self._path = path
        self._ttl_days = ttl_days
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict) -> None:
        entry = {"ts": time.time(), "status": "PENDING", **event}
        with self._path.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []
        return [json.loads(line) for line in self._path.read_text().splitlines() if line.strip()]

    def gc(self) -> int:
        """Remove entries older than ttl_days that are not PENDING. Returns count removed."""
        if not self._path.exists():
            return 0
        cutoff = time.time() - self._ttl_days * 86400
        entries = self.read_all()
        keep = [e for e in entries if e.get("status") == "PENDING" or e.get("ts", 0) >= cutoff]
        removed = len(entries) - len(keep)
        if removed:
            self._path.write_text("\n".join(json.dumps(e) for e in keep) + ("\n" if keep else ""))
        return removed
