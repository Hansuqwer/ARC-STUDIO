"""Simple in-memory context cache with TTL."""

from __future__ import annotations

import hashlib
import time
from typing import Optional

from ..protocol.schemas import ContextPackEntry

DEFAULT_TTL_SECONDS = 300  # 5 minutes


class ContextCache:
    def __init__(self, ttl: int = DEFAULT_TTL_SECONDS) -> None:
        self._store: dict[str, tuple[list[ContextPackEntry], float]] = {}
        self._ttl = ttl

    def _key(self, task: str, workspace: Optional[str]) -> str:
        raw = f"{task}|{workspace or ''}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, task: str, workspace: Optional[str] = None) -> Optional[list[ContextPackEntry]]:
        key = self._key(task, workspace)
        if key in self._store:
            entries, ts = self._store[key]
            if time.time() - ts < self._ttl:
                return entries
            del self._store[key]
        return None

    def set(
        self, task: str, entries: list[ContextPackEntry], workspace: Optional[str] = None
    ) -> None:
        key = self._key(task, workspace)
        self._store[key] = (entries, time.time())

    def clear(self) -> None:
        self._store.clear()
