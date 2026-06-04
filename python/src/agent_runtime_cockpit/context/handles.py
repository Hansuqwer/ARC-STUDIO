"""QW-4 MCP output handle virtualization.

Tool outputs > VIRTUALIZE_THRESHOLD bytes are stored content-addressed as
    arc://output/sha256/<64-hex>
and surfaced to the model as a resource_link with head/tail preview.

SHA is computed AFTER redaction — no cleartext secret ever enters the hash.
Fail-closed: missing or corrupt handle raises, never returns empty content.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Callable

from ..budget.storage import SQLiteWALStorage

# ── Constants ──────────────────────────────────────────────────────────────

URI_SCHEME = "arc://output/sha256/"
VIRTUALIZE_THRESHOLD = int(os.environ.get("ARC_TOOL_VIRTUALIZE_THRESHOLD_BYTES", 8 * 1024))
DEFAULT_MAX_BYTES = 1024 * 1024 * 1024  # 1 GB
PREVIEW_CHARS = 500
TOKENS_PER_CHAR_ESTIMATE = 0.25  # ~4 chars/token


# ── Exceptions ─────────────────────────────────────────────────────────────


class HandleNotFound(KeyError):
    """Raised when a handle URI / prefix does not exist in the store."""


class HandleCorrupt(RuntimeError):
    """Raised when fetched content fails SHA256 verification."""


class HandleAmbiguous(ValueError):
    """Raised when a short prefix matches more than one handle."""


# ── Data classes ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HandleMetadata:
    uri: str  # arc://output/sha256/<hex>
    sha256_hex: str  # 64-char lowercase hex
    size_bytes: int
    mime_type: str
    preview_head: str  # first PREVIEW_CHARS chars (post-redaction, decoded)
    preview_tail: str  # last PREVIEW_CHARS chars
    estimated_tokens: int


# ── HandleStore ────────────────────────────────────────────────────────────


class HandleStore:
    """Content-addressed handle storage backed by SQLiteWALStorage.

    Invariants:
    - SHA computed AFTER redaction (no cleartext secret in hash or DB).
    - Dedup is free: identical content → identical URI.
    - LRU eviction by last_access_ts, capped at max_bytes (default 1 GB).
    - Fail-closed: corrupt or missing handle raises, never returns empty.
    """

    def __init__(
        self,
        storage: SQLiteWALStorage,
        redactor: Callable[[bytes], bytes] | None = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self._storage = storage
        self._redactor: Callable[[bytes], bytes] = redactor or (lambda b: b)
        self._max_bytes = max_bytes

    def store(self, content: bytes, mime_type: str = "text/plain") -> HandleMetadata:
        """Redact, hash, store (dedup), return metadata for resource_link.

        Triggers LRU eviction if total stored bytes would exceed max_bytes.
        """
        redacted = self._redactor(content)
        sha = hashlib.sha256(redacted).hexdigest()
        uri = URI_SCHEME + sha

        decoded = redacted.decode(errors="replace")
        preview_head = decoded[:PREVIEW_CHARS]
        preview_tail = decoded[-PREVIEW_CHARS:] if len(decoded) > PREVIEW_CHARS else ""
        estimated_tokens = max(1, int(len(decoded) * TOKENS_PER_CHAR_ESTIMATE))

        self._storage.handle_store(sha, redacted, mime_type)

        # Evict if over cap
        if self._max_bytes > 0:
            self._storage.handle_evict_lru(self._max_bytes)

        return HandleMetadata(
            uri=uri,
            sha256_hex=sha,
            size_bytes=len(redacted),
            mime_type=mime_type,
            preview_head=preview_head,
            preview_tail=preview_tail,
            estimated_tokens=estimated_tokens,
        )

    def expand(self, sha_or_prefix: str) -> bytes:
        """Fetch full content by full SHA or unambiguous prefix.

        Updates last_access_ts. Raises HandleNotFound / HandleCorrupt /
        HandleAmbiguous — never returns empty bytes for a present handle.
        """
        # Strip URI prefix if caller passes full URI
        key = sha_or_prefix
        if key.startswith(URI_SCHEME):
            key = key[len(URI_SCHEME) :]

        # Resolve prefix → full SHA
        if len(key) < 64:
            try:
                full = self._storage.handle_resolve_prefix(key)
            except ValueError as exc:
                raise HandleAmbiguous(str(exc)) from exc
            if full is None:
                raise HandleNotFound(f"No handle matching prefix {key!r}")
            key = full
        else:
            # Exact lookup — verify it exists
            if self._storage.handle_resolve_prefix(key) is None:
                raise HandleNotFound(f"Handle {key!r} not found")

        content = self._storage.handle_fetch(key)
        if content is None:
            raise HandleNotFound(f"Handle {key!r} not found")

        # Verify integrity
        actual = hashlib.sha256(content).hexdigest()
        if actual != key:
            raise HandleCorrupt(
                f"Handle {key[:8]}… content failed SHA256 verification "
                f"(stored {key[:8]}, got {actual[:8]})"
            )
        return content

    def total_bytes(self) -> int:
        """Total bytes currently stored."""
        return self._storage.handle_total_bytes()

    def count(self) -> int:
        """Number of handles currently stored."""
        return self._storage.handle_count()
