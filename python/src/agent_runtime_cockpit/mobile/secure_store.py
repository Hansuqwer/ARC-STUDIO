"""Secure local store for ARC Mobile Runtime (Phase 8).

Real encryption-at-rest using Fernet (AES-128-CBC + HMAC authentication). Values are
serialized to JSON and encrypted before they touch memory-of-record or disk — the
persisted file holds ciphertext only, never plaintext. Each entry carries a data
classification tag (reusing MobileDataSensitivity) and supports data-subject export/delete.

Key management is abstracted via `KeyProvider`. The bundled `InMemoryKeyProvider` is the
simulator-preview provider; on a real device the Keychain (iOS) / Keystore (Android) would
back the same interface. Deterministic, offline, no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from cryptography.fernet import Fernet, InvalidToken

from .models import MobileDataSensitivity

# Classifications that must never be returned in a metadata/export bundle in cleartext
# unless the caller explicitly opts in (data-subject self-export).
_RESTRICTED = {MobileDataSensitivity.HIGH, MobileDataSensitivity.CRITICAL}


class KeyProvider(Protocol):
    """Abstraction over the platform secret store (Keychain/Keystore on device)."""

    def get_key(self) -> bytes: ...


@dataclass
class InMemoryKeyProvider:
    """Simulator-preview key provider. A real device backs this with Keychain/Keystore."""

    key: bytes = field(default_factory=Fernet.generate_key)

    def get_key(self) -> bytes:
        return self.key


@dataclass
class _Entry:
    ciphertext: bytes
    classification: MobileDataSensitivity
    created_at: str
    updated_at: str


class SecureStoreError(RuntimeError):
    """Raised on decryption failure or tamper detection."""


class SecureLocalStore:
    """Encrypted-at-rest key/value store with classification tags and export/delete.

    Plaintext exists only transiently in `put`/`get`; the in-memory record and any persisted
    file hold Fernet ciphertext. Tampered ciphertext fails closed (SecureStoreError).
    """

    def __init__(self, key_provider: KeyProvider | None = None, path: Path | None = None) -> None:
        self._keys = key_provider or InMemoryKeyProvider()
        self._fernet = Fernet(self._keys.get_key())
        self._path = Path(path) if path else None
        self._entries: dict[str, _Entry] = {}
        if self._path and self._path.exists():
            self._load()

    # ── core ──
    def put(
        self,
        key: str,
        value: Any,
        classification: MobileDataSensitivity | str = MobileDataSensitivity.LOW,
    ) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        cls = (
            MobileDataSensitivity(classification)
            if isinstance(classification, str)
            else classification
        )
        plaintext = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        now = datetime.now(timezone.utc).isoformat()
        created = self._entries[key].created_at if key in self._entries else now
        self._entries[key] = _Entry(
            ciphertext=self._fernet.encrypt(plaintext),
            classification=cls,
            created_at=created,
            updated_at=now,
        )
        self._persist()

    def get(self, key: str) -> Any:
        entry = self._entries.get(key)
        if entry is None:
            raise KeyError(key)
        try:
            return json.loads(self._fernet.decrypt(entry.ciphertext).decode("utf-8"))
        except InvalidToken as exc:  # tamper / wrong key → fail closed
            raise SecureStoreError(f"decryption failed for '{key}' (tamper or wrong key)") from exc

    def delete(self, key: str) -> bool:
        existed = self._entries.pop(key, None) is not None
        if existed:
            self._persist()
        return existed

    def classification_of(self, key: str) -> MobileDataSensitivity:
        if key not in self._entries:
            raise KeyError(key)
        return self._entries[key].classification

    def keys(self) -> list[str]:
        return sorted(self._entries)

    # ── data-subject export ──
    def export(self, include_values: bool = False) -> dict[str, Any]:
        """Export entry metadata. Values are included only when `include_values=True`
        (data-subject self-export); restricted classifications are never silently exported."""
        items = []
        for key in self.keys():
            e = self._entries[key]
            item: dict[str, Any] = {
                "key": key,
                "classification": e.classification.value,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
            }
            if include_values:
                if e.classification in _RESTRICTED:
                    item["value"] = "[redacted: restricted classification]"
                    item["value_redacted"] = True
                else:
                    item["value"] = self.get(key)
            items.append(item)
        return {"simulator_preview": True, "encrypted_at_rest": True, "entries": items}

    def wipe(self) -> int:
        """Delete every entry (data-subject erasure). Returns the number removed."""
        n = len(self._entries)
        self._entries.clear()
        self._persist()
        return n

    # ── persistence (ciphertext only) ──
    def _persist(self) -> None:
        if not self._path:
            return
        payload = {
            "version": 1,
            "entries": {
                k: {
                    "ciphertext": e.ciphertext.decode("ascii"),
                    "classification": e.classification.value,
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                }
                for k, e in self._entries.items()
            },
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload), encoding="utf-8")

    def _load(self) -> None:
        assert self._path is not None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for k, raw in data.get("entries", {}).items():
            self._entries[k] = _Entry(
                ciphertext=raw["ciphertext"].encode("ascii"),
                classification=MobileDataSensitivity(raw["classification"]),
                created_at=raw["created_at"],
                updated_at=raw["updated_at"],
            )
