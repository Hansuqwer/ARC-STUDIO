"""Budget persistence layer — SQLite WAL storage for BudgetState.

Provides:
  BudgetStorage (ABC) — interface
  InMemoryStorage — default, preserves v0.4.0 behavior (session resets on restart)
  SQLiteWALStorage — durable storage; SESSION + PROVIDER_DAY survive restart

Storage path (SQLite):
  macOS:  ~/Library/Application Support/arc-theia-studio/budget.db
  Linux:  ~/.local/share/arc-theia-studio/budget.db
  Other:  ~/.arc-theia-studio/budget.db

RUN scope is intentionally NOT persisted — per-run reset is by design.
WORKFLOW scope is NOT persisted — ephemeral per workflow.

Schema version: 1 (stored in budget_meta table).
Concurrency: SQLite WAL mode allows multiple readers; single-writer serialized
by sqlite3's built-in serialization. No additional file locks needed for
single-user local tool.
"""

from __future__ import annotations

import abc
import os
import sqlite3
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional


# ── Storage path resolution ────────────────────────────────────────────────


def _data_dir() -> Path:
    """Return platform-appropriate data directory for arc-theia-studio."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / "arc-theia-studio"
    d.mkdir(parents=True, exist_ok=True)
    return d


DEFAULT_DB_PATH = _data_dir() / "budget.db"

SCHEMA_VERSION = 1

_CREATE_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS budget_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS budget_spend (
    scope        TEXT NOT NULL,
    provider_key TEXT NOT NULL DEFAULT '',
    date_key     TEXT NOT NULL DEFAULT '',
    amount_usd   TEXT NOT NULL DEFAULT '0',
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (scope, provider_key, date_key)
);
"""

_UPSERT_SQL = """
INSERT INTO budget_spend (scope, provider_key, date_key, amount_usd, updated_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(scope, provider_key, date_key) DO UPDATE SET
    amount_usd = excluded.amount_usd,
    updated_at = excluded.updated_at
"""


# ── ABC ───────────────────────────────────────────────────────────────────────


class BudgetStorage(abc.ABC):
    """Persistence interface for budget spend data."""

    @abc.abstractmethod
    def load_session(self) -> Decimal:
        """Return accumulated SESSION spend since last reset (or $0 on fresh DB)."""

    @abc.abstractmethod
    def load_provider_day(self, provider_key: str, date_key: str) -> Decimal:
        """Return accumulated PROVIDER_DAY spend for provider + date."""

    @abc.abstractmethod
    def save_session(self, amount_usd: Decimal) -> None:
        """Persist SESSION spend (overwrites previous value)."""

    @abc.abstractmethod
    def save_provider_day(self, provider_key: str, date_key: str, amount_usd: Decimal) -> None:
        """Persist PROVIDER_DAY spend."""

    @abc.abstractmethod
    def reset_session(self) -> None:
        """Clear SESSION spend (e.g., on explicit /wallet reset)."""


# ── In-memory (v0.4.0 default) ───────────────────────────────────────────────


class InMemoryStorage(BudgetStorage):
    """No-op storage — all spend resets on process exit. Preserves v0.4.0 behavior."""

    def __init__(self) -> None:
        self._session = Decimal("0")
        self._provider_days: dict[tuple[str, str], Decimal] = {}

    def load_session(self) -> Decimal:
        return self._session

    def load_provider_day(self, provider_key: str, date_key: str) -> Decimal:
        return self._provider_days.get((provider_key, date_key), Decimal("0"))

    def save_session(self, amount_usd: Decimal) -> None:
        self._session = amount_usd

    def save_provider_day(self, provider_key: str, date_key: str, amount_usd: Decimal) -> None:
        self._provider_days[(provider_key, date_key)] = amount_usd

    def reset_session(self) -> None:
        self._session = Decimal("0")


# ── SQLite WAL storage ────────────────────────────────────────────────────────


class SQLiteWALStorage(BudgetStorage):
    """Durable SQLite WAL storage. SESSION + PROVIDER_DAY survive process restart.

    Fail-closed: any DB corruption → raises, never returns 0 silently.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=5)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")  # WAL safe, faster than FULL
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_SQL)
            cur = conn.execute("SELECT value FROM budget_meta WHERE key = 'schema_version'")
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO budget_meta VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            # Future: run migrations if row[0] < SCHEMA_VERSION

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load_session(self) -> Decimal:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT amount_usd FROM budget_spend WHERE scope='SESSION' AND provider_key='' AND date_key=''"
            )
            row = cur.fetchone()
            return Decimal(row[0]) if row else Decimal("0")

    def load_provider_day(self, provider_key: str, date_key: str) -> Decimal:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT amount_usd FROM budget_spend WHERE scope='PROVIDER_DAY' AND provider_key=? AND date_key=?",
                (provider_key, date_key),
            )
            row = cur.fetchone()
            return Decimal(row[0]) if row else Decimal("0")

    def save_session(self, amount_usd: Decimal) -> None:
        with self._connect() as conn:
            conn.execute(_UPSERT_SQL, ("SESSION", "", "", str(amount_usd), self._now()))

    def save_provider_day(self, provider_key: str, date_key: str, amount_usd: Decimal) -> None:
        with self._connect() as conn:
            conn.execute(
                _UPSERT_SQL, ("PROVIDER_DAY", provider_key, date_key, str(amount_usd), self._now())
            )

    def reset_session(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM budget_spend WHERE scope='SESSION'")


def default_storage() -> BudgetStorage:
    """Return SQLiteWALStorage for CLI sessions."""
    return SQLiteWALStorage()


__all__ = [
    "BudgetStorage",
    "InMemoryStorage",
    "SQLiteWALStorage",
    "default_storage",
    "DEFAULT_DB_PATH",
]
