"""Tests for QW-4 HandleStore (context/handles.py)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent_runtime_cockpit.budget.storage import SQLiteWALStorage
from agent_runtime_cockpit.context.handles import (
    DEFAULT_MAX_BYTES,
    HandleAmbiguous,
    HandleCorrupt,
    HandleNotFound,
    HandleStore,
    URI_SCHEME,
)


def _store(tmp_path: Path, redactor=None, max_bytes: int = DEFAULT_MAX_BYTES) -> HandleStore:
    storage = SQLiteWALStorage(tmp_path / "test.db")
    return HandleStore(storage, redactor=redactor, max_bytes=max_bytes)


# ── 1. Round-trip store → expand ──────────────────────────────────────────


def test_store_expand_round_trip(tmp_path):
    hs = _store(tmp_path)
    content = b"hello world"
    meta = hs.store(content)
    assert meta.uri.startswith(URI_SCHEME)
    assert hs.expand(meta.sha256_hex) == content


# ── 2. Dedup: same content → same URI ────────────────────────────────────


def test_dedup_same_content_same_uri(tmp_path):
    hs = _store(tmp_path)
    content = b"duplicate content"
    m1 = hs.store(content)
    m2 = hs.store(content)
    assert m1.uri == m2.uri
    assert hs.count() == 1


# ── 3. Redaction at write time, not expand time ──────────────────────────


def test_redaction_applied_at_write(tmp_path):
    called = []

    def redactor(b: bytes) -> bytes:
        called.append(b)
        return b.replace(b"SECRET", b"REDACTED")

    hs = _store(tmp_path, redactor=redactor)
    content = b"token=SECRET"
    meta = hs.store(content)
    assert len(called) == 1  # redacted exactly once at write

    expanded = hs.expand(meta.sha256_hex)
    assert b"SECRET" not in expanded
    assert b"REDACTED" in expanded

    # SHA was computed from redacted content
    expected_sha = hashlib.sha256(b"token=REDACTED").hexdigest()
    assert meta.sha256_hex == expected_sha


# ── 4. Secret not stored cleartext (SHA of redacted) ─────────────────────


def test_sha_computed_post_redaction(tmp_path):
    hs = _store(tmp_path, redactor=lambda b: b"[redacted]")
    meta = hs.store(b"very secret content")
    assert meta.sha256_hex == hashlib.sha256(b"[redacted]").hexdigest()


# ── 5. Prefix resolution — unambiguous ───────────────────────────────────


def test_prefix_resolution_unambiguous(tmp_path):
    hs = _store(tmp_path)
    meta = hs.store(b"unique content abc")
    prefix = meta.sha256_hex[:8]
    result = hs.expand(prefix)
    assert result == b"unique content abc"


# ── 6. Prefix resolution — ambiguous raises ──────────────────────────────


def test_prefix_resolution_collision_raises(tmp_path):
    storage = SQLiteWALStorage(tmp_path / "test.db")
    hs = HandleStore(storage)
    # Manually insert two handles with same 1-char prefix by forcing known SHAs
    storage.handle_store("aa" + "0" * 62, b"content_aa", "text/plain")
    storage.handle_store("aa" + "1" * 62, b"content_bb", "text/plain")
    with pytest.raises(HandleAmbiguous):
        hs.expand("aa")


# ── 7. Missing handle raises HandleNotFound ──────────────────────────────


def test_missing_handle_raises(tmp_path):
    hs = _store(tmp_path)
    with pytest.raises(HandleNotFound):
        hs.expand("deadbeef")


# ── 8. Expand full URI works ──────────────────────────────────────────────


def test_expand_full_uri(tmp_path):
    hs = _store(tmp_path)
    meta = hs.store(b"some data")
    assert hs.expand(meta.uri) == b"some data"


# ── 9. last_access updated on expand ─────────────────────────────────────


def test_last_access_updated_on_expand(tmp_path):
    storage = SQLiteWALStorage(tmp_path / "test.db")
    hs = HandleStore(storage)
    meta = hs.store(b"data")
    # First expand
    hs.expand(meta.sha256_hex)
    with storage._connect() as conn:
        ts1 = conn.execute(
            "SELECT last_access_ts FROM handles WHERE sha256=?", (meta.sha256_hex,)
        ).fetchone()[0]
    # Second expand
    hs.expand(meta.sha256_hex)
    with storage._connect() as conn:
        ts2 = conn.execute(
            "SELECT last_access_ts FROM handles WHERE sha256=?", (meta.sha256_hex,)
        ).fetchone()[0]
    assert ts2 >= ts1


# ── 10. LRU eviction respects max_bytes ──────────────────────────────────


def test_lru_eviction_enforces_max_bytes(tmp_path):
    hs = _store(tmp_path, max_bytes=50)
    # Store 3 × 30-byte items; each store triggers eviction
    hs.store(b"A" * 30)
    hs.store(b"B" * 30)  # evicts previous
    m3 = hs.store(b"C" * 30)  # most-recent survives
    assert hs.total_bytes() <= 50
    # m3 should still be retrievable
    assert hs.expand(m3.sha256_hex) == b"C" * 30


# ── 11. total_bytes and count ─────────────────────────────────────────────


def test_total_bytes_and_count(tmp_path):
    hs = _store(tmp_path)
    assert hs.count() == 0
    assert hs.total_bytes() == 0
    hs.store(b"hello")
    hs.store(b"world")
    assert hs.count() == 2
    assert hs.total_bytes() == 10


# ── 12. Corrupt content raises HandleCorrupt ─────────────────────────────


def test_corrupt_content_raises(tmp_path):
    storage = SQLiteWALStorage(tmp_path / "test.db")
    hs = HandleStore(storage)
    # Store valid
    meta = hs.store(b"real content")
    # Tamper with DB directly
    with storage._connect() as conn:
        conn.execute(
            "UPDATE handles SET content = ? WHERE sha256 = ?",
            (b"tampered", meta.sha256_hex),
        )
    with pytest.raises(HandleCorrupt):
        hs.expand(meta.sha256_hex)


# ── 13. metadata fields populated correctly ──────────────────────────────


def test_metadata_fields(tmp_path):
    hs = _store(tmp_path)
    content = b"x" * 1200
    meta = hs.store(content)
    assert meta.size_bytes == 1200
    assert len(meta.preview_head) == 500
    assert len(meta.preview_tail) == 500
    assert meta.estimated_tokens > 0
    assert meta.mime_type == "text/plain"
