"""Tests: SessionStore R86a — _init_db, _encrypt/_decrypt, transcript (Phase 278)."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from agent_runtime_cockpit.continuum.store import (
    SessionCorruptedError,
    SessionStore,
    TranscriptEntry,
)


@pytest.fixture
def fernet_key() -> bytes:
    return Fernet.generate_key()


@pytest.fixture
def store(tmp_path, fernet_key, monkeypatch):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    return SessionStore("test-session-1", fernet_key)


# ── _init_db ─────────────────────────────────────────────────


def test_init_db_creates_file(store, tmp_path):
    assert store.db_path.exists()


def test_init_db_schema_version_1(store):
    import sqlite3

    with sqlite3.connect(store.db_path) as conn:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
    assert row[0] == 1


def test_init_db_idempotent(tmp_path, fernet_key, monkeypatch):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    # Opening twice should not raise
    s1 = SessionStore("s2", fernet_key)
    s2 = SessionStore("s2", fernet_key)
    assert s1.db_path == s2.db_path


# ── _encrypt / _decrypt ───────────────────────────────────────


def test_encrypt_decrypt_roundtrip(store):
    plaintext = "hello world"
    ciphertext = store._encrypt(plaintext)
    assert ciphertext != plaintext
    assert store._decrypt(ciphertext) == plaintext


def test_decrypt_wrong_key_raises(store, tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    other_key = Fernet.generate_key()
    other_store = SessionStore("s3", other_key)
    ciphertext = store._encrypt("secret")
    with pytest.raises(SessionCorruptedError):
        other_store._decrypt(ciphertext)


# ── transcript ────────────────────────────────────────────────


def _entry(seq: int, content: str) -> TranscriptEntry:
    return TranscriptEntry(
        seq_id=seq, timestamp="2026-01-01T00:00:00Z", role="user", content=content
    )


def test_save_and_load_transcript(store):
    entries = [_entry(1, "hello"), _entry(2, "world")]
    store.save_transcript(entries)
    loaded = store.load_transcript()
    assert len(loaded) == 2
    assert loaded[0].content == "hello"
    assert loaded[1].content == "world"


def test_save_transcript_is_atomic_replace(store):
    store.save_transcript([_entry(1, "old")])
    store.save_transcript([_entry(1, "new")])
    loaded = store.load_transcript()
    assert len(loaded) == 1
    assert loaded[0].content == "new"


def test_append_transcript_entry(store):
    store.save_transcript([_entry(1, "first")])
    store.append_transcript_entry(_entry(0, "second"))
    loaded = store.load_transcript()
    assert len(loaded) == 2
    contents = {e.content for e in loaded}
    assert "first" in contents
    assert "second" in contents


def test_load_empty_transcript(store):
    assert store.load_transcript() == []


def test_transcript_content_is_encrypted_on_disk(store):
    """Raw DB bytes should not contain plaintext content."""
    store.save_transcript([_entry(1, "supersecret")])
    raw = store.db_path.read_bytes()
    assert b"supersecret" not in raw


# ── meta ──────────────────────────────────────────────────────


def test_save_load_meta(store):
    store.save_meta("session_name", "my-session")
    assert store.load_meta("session_name") == "my-session"


def test_load_missing_meta_returns_none(store):
    assert store.load_meta("missing") is None


# ── delete ────────────────────────────────────────────────────


def test_delete_removes_db(store):
    assert store.db_path.exists()
    store.delete()
    assert not store.db_path.exists()


def test_delete_idempotent(store):
    store.delete()
    store.delete()  # should not raise
