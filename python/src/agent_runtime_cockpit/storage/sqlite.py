"""SQLite store for ARC metadata (runs index, audit log)."""
from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

log = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(".arc") / "arc.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details TEXT,
    verified INTEGER DEFAULT 0
);
"""


class SqliteStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA)
            log.info("ARC SQLite DB initialised: %s", self.db_path)
        except Exception as e:
            log.warning("Failed to init SQLite DB: %s", e)

    def insert_run(self, run_id: str, workflow_id: str, runtime: str,
                   status: str, started_at: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
                    (run_id, workflow_id, runtime, status, started_at, None, None)
                )
        except Exception as e:
            log.warning("SQLite insert_run failed: %s", e)

    def update_run_status(self, run_id: str, status: str, ended_at: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE runs SET status=?, ended_at=? WHERE id=?",
                    (status, ended_at, run_id)
                )
        except Exception as e:
            log.warning("SQLite update_run failed: %s", e)
