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
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA_SQL)
            row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row and row[0] != 1:
                raise SchemaVersionError(f"Expected schema v1, got v{row[0]}")

    # ── Transcript ────────────────────────────────────────────

    def save_transcript(self, entries: list[TranscriptEntry]) -> None:
        """Atomic replace: clear existing entries, insert all provided entries (encrypted)."""
        import json
        import sqlite3

        rows = [
            (
                e.timestamp,
                e.role,
                self._encrypt(e.content),
                self._encrypt(json.dumps(e.metadata)) if e.metadata else None,
            )
            for e in entries
        ]
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM transcript_entries")
            conn.executemany(
                "INSERT INTO transcript_entries (timestamp, role, content, metadata) VALUES (?,?,?,?)",
                rows,
            )

    def load_transcript(self) -> list[TranscriptEntry]:
        """Return decrypted transcript in chronological order.

        Raises SessionCorruptedError on decryption failure.
        """
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT seq_id, timestamp, role, content, metadata FROM transcript_entries ORDER BY seq_id"
            ).fetchall()
        result = []
        for seq_id, timestamp, role, enc_content, enc_meta in rows:
            content = self._decrypt(enc_content)
            metadata: dict[str, Any] = {}
            if enc_meta:
                metadata = json.loads(self._decrypt(enc_meta))
            result.append(
                TranscriptEntry(
                    seq_id=seq_id,
                    timestamp=timestamp,
                    role=role,
                    content=content,
                    metadata=metadata,
                )
            )
        return result

    def append_transcript_entry(self, entry: TranscriptEntry) -> None:
        """Append a single entry without clearing existing ones."""
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO transcript_entries (timestamp, role, content, metadata) VALUES (?,?,?,?)",
                (
                    entry.timestamp,
                    entry.role,
                    self._encrypt(entry.content),
                    self._encrypt(json.dumps(entry.metadata)) if entry.metadata else None,
                ),
            )

    # ── UI State ──────────────────────────────────────────────

    def save_ui_state(self, state: dict[str, Any]) -> None:
        """Save UI state dict (non-sensitive; stored as plaintext JSON)."""
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM ui_state")
            conn.executemany(
                "INSERT INTO ui_state (key, value) VALUES (?,?)",
                [(k, json.dumps(v)) for k, v in state.items()],
            )

    def load_ui_state(self) -> dict[str, Any]:
        """Return UI state dict, or {} if nothing stored."""
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT key, value FROM ui_state").fetchall()
        return {k: json.loads(v) for k, v in rows}

    # ── Run Context ───────────────────────────────────────────

    def save_run_context(self, context: RunContext) -> None:
        """Upsert run context."""
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO run_context
                   (run_id, status, started_at, last_event_id, provider_id, model_id,
                    context_budget, context_used, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    context.run_id,
                    context.status,
                    context.started_at,
                    context.last_event_id,
                    context.provider_id,
                    context.model_id,
                    context.context_budget,
                    context.context_used,
                    json.dumps(context.metadata),
                ),
            )

    def load_run_context(self, run_id: str) -> RunContext | None:
        """Return RunContext for run_id, or None if not found."""
        import json
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT run_id, status, started_at, last_event_id, provider_id, model_id, "
                "context_budget, context_used, metadata FROM run_context WHERE run_id=?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        return RunContext(
            run_id=row[0],
            status=row[1],
            started_at=row[2],
            last_event_id=row[3],
            provider_id=row[4],
            model_id=row[5],
            context_budget=row[6],
            context_used=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
        )

    def list_runs(self) -> list[str]:
        """Return all run_ids stored in run_context."""
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute("SELECT run_id FROM run_context ORDER BY started_at").fetchall()
        return [r[0] for r in rows]

    # ── Metadata ──────────────────────────────────────────────

    def save_meta(self, key: str, value: str) -> None:
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO session_meta (key, value) VALUES (?,?)", (key, value)
            )

    def load_meta(self, key: str) -> str | None:
        import sqlite3

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT value FROM session_meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def delete(self) -> None:
        """Delete this session's database file. Idempotent."""
        try:
            self._db_path.unlink()
        except FileNotFoundError:
            pass

    @property
    def db_path(self) -> Path:
        return self._db_path

    # ── Encryption helpers ────────────────────────────────────

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt with Fernet; return base64-encoded ciphertext string."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt Fernet ciphertext string.

        Raises SessionCorruptedError on InvalidToken.
        """
        from cryptography.fernet import InvalidToken

        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise SessionCorruptedError(f"Decryption failed for session {self.session_id}") from exc
