"""SQLite-backed session state store for R86 ARC Continuum.

Provides:
  SessionStore   — persist/restore transcript, UI state, and run context.
  TranscriptEntry / RunContext — immutable data classes.
  SessionStoreError hierarchy.

Schema: session_state v1
  ~/.arc/sessions/{session_id}/state.db

Encryption: Fernet from auth/manager.py (key reuse, no new key management).
  Encrypted fields: transcript content + metadata.
  Plaintext fields: ui_state, timestamps, run_id, status.

This is a stub: all method bodies raise NotImplementedError.
Kiro agents should fill the bodies without guessing the interface.

Dependencies:
  - auth/manager.py        (FernetKeyManager)
  - cli_repl/session.py    (ChatSession — canonical session format)
  - tui/screen.py          (DataStore — source of UI state to persist)

Companion audit doc:
  docs/research-findings/r86-session-persistence-audit-2026-06-09.md
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet


log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Schema (session_state v1)
# ─────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS session_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_entries (
    seq_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    role      TEXT NOT NULL,
    content   TEXT NOT NULL,
    metadata  TEXT
);

CREATE TABLE IF NOT EXISTS ui_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_context (
    run_id         TEXT PRIMARY KEY,
    status         TEXT NOT NULL,
    started_at     TEXT NOT NULL,
    last_event_id  INTEGER,
    provider_id    TEXT,
    model_id       TEXT,
    context_budget INTEGER,
    context_used   INTEGER,
    metadata       TEXT
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""

# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────


class SessionStoreError(Exception):
    """Base exception for SessionStore operations."""


class SessionNotFoundError(SessionStoreError):
    """Requested session does not exist."""


class SessionCorruptedError(SessionStoreError):
    """Session data is corrupted or decryption failed."""


class SchemaVersionError(SessionStoreError):
    """Database schema version mismatch."""


# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TranscriptEntry:
    seq_id: int
    timestamp: str
    role: str  # user | assistant | system | tool
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunContext:
    run_id: str
    status: str  # running | paused | completed | failed
    started_at: str
    last_event_id: int | None = None
    provider_id: str | None = None
    model_id: str | None = None
    context_budget: int | None = None
    context_used: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
# SessionStore
# ─────────────────────────────────────────────────────────────


class SessionStore:
    """SQLite-backed session state store.

    Usage:
        key_manager = FernetKeyManager()
        store = SessionStore("s-abc123", key_manager.get_or_create_key())
        store.append_transcript_entry(entry)
        entries = store.load_transcript()
    """

    def __init__(self, session_id: str, fernet_key: bytes) -> None:
        self.session_id = session_id
        self._fernet = Fernet(fernet_key)
        self._db_path = self._get_db_path(session_id)
        self._init_db()

    # ── Path helpers ─────────────────────────────────────────

    @staticmethod
    def _get_sessions_dir() -> Path:
        override = os.environ.get("ARC_STUDIO_SESSIONS_DIR")
        base = Path(override).expanduser() if override else Path.home() / ".arc" / "sessions"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _get_db_path(self, session_id: str) -> Path:
        return self._get_sessions_dir() / session_id / "state.db"

    def _init_db(self) -> None:
        """Create tables if absent; enforce schema version 1."""
        raise NotImplementedError

    # ── Transcript ────────────────────────────────────────────

    def save_transcript(self, entries: list[TranscriptEntry]) -> None:
        """Atomic replace: clear existing entries, insert all provided entries (encrypted)."""
        raise NotImplementedError

    def load_transcript(self) -> list[TranscriptEntry]:
        """Return decrypted transcript in chronological order.

        Raises SessionCorruptedError on decryption failure.
        """
        raise NotImplementedError

    def append_transcript_entry(self, entry: TranscriptEntry) -> None:
        """Append a single entry without clearing existing ones."""
        raise NotImplementedError

    # ── UI State ──────────────────────────────────────────────

    def save_ui_state(self, state: dict[str, Any]) -> None:
        """Save UI state dict (non-sensitive; stored as plaintext JSON)."""
        raise NotImplementedError

    def load_ui_state(self) -> dict[str, Any]:
        """Return UI state dict, or {} if nothing stored."""
        raise NotImplementedError

    # ── Run Context ───────────────────────────────────────────

    def save_run_context(self, context: RunContext) -> None:
        """Upsert run context."""
        raise NotImplementedError

    def load_run_context(self, run_id: str) -> RunContext | None:
        """Return RunContext for run_id, or None if not found."""
        raise NotImplementedError

    def list_runs(self) -> list[str]:
        """Return all run_ids stored in run_context."""
        raise NotImplementedError

    # ── Metadata ──────────────────────────────────────────────

    def save_meta(self, key: str, value: str) -> None:
        raise NotImplementedError

    def load_meta(self, key: str) -> str | None:
        raise NotImplementedError

    def delete(self) -> None:
        """Delete this session's database file. Idempotent."""
        raise NotImplementedError

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ── Encryption helpers ────────────────────────────────────

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt with Fernet; return base64-encoded ciphertext string."""
        raise NotImplementedError

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt Fernet ciphertext string.

        Raises SessionCorruptedError on InvalidToken.
        """
        raise NotImplementedError
