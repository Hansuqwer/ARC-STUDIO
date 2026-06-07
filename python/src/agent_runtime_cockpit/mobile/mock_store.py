"""In-memory mock state store for fixture-backed simulation.

Used by the simulator for ``app.memory.*`` capabilities.
Per-session only; not persisted. Safe: no filesystem I/O, no network.
"""

from __future__ import annotations

from typing import Any


class MockStore:
    """Simple key-value store for simulator sessions."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def write(self, key: str, value: Any) -> dict[str, Any]:
        self._store[key] = value
        return {"stored": True, "key": key}

    def retrieve(self, key: str) -> dict[str, Any]:
        if key not in self._store and key != "last":
            return {"found": False, "key": key, "value": None}
        if key == "last":
            # Return most recently written value
            if not self._store:
                return {"found": False, "key": key, "value": None}
            val = next(reversed(self._store.values()))
            return {"found": True, "key": key, "value": val}
        return {"found": True, "key": key, "value": self._store[key]}

    def clear(self) -> None:
        self._store.clear()


# Module-level default store (reset between test sessions if needed)
_default_store = MockStore()


def get_default_store() -> MockStore:
    return _default_store


def reset_default_store() -> None:
    _default_store.clear()
