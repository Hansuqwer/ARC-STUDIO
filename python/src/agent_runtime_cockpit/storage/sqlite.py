"""SQLite store for ARC metadata (runs index, audit log) — ADR-003."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)
DEFAULT_DB_PATH = Path(".arc") / "arc.db"

# ADR-003 schema: full run metadata index (no events), audit log, schema version
SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    runtime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_ms INTEGER,
    profile_id TEXT DEFAULT 'stub',
    isolation TEXT DEFAULT 'none',
    supervisor_id TEXT,
    cancel_reason TEXT,
    error_detail TEXT,
    trace_path TEXT,
    audit_path TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_runtime ON runs(runtime);
CREATE INDEX IF NOT EXISTS idx_runs_workflow ON runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_supervisor ON runs(supervisor_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    details TEXT,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id);

CREATE TABLE IF NOT EXISTS _schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class SqliteStore:
    """SQLite index for run metadata. JSONL remains canonical (ADR-003)."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """Ensure tables exist. Idempotent."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executescript(SCHEMA)
            log.info("SQLite DB initialised: %s", self.db_path)
        except Exception as e:
            log.warning("Failed to init SQLite DB: %s", e)

    def _ensure_init(self) -> None:
        """Auto-init if the DB file doesn't exist yet."""
        if not self.db_path.exists():
            self.init_db()

    def _conn(self) -> sqlite3.Connection:
        self._ensure_init()
        return sqlite3.connect(str(self.db_path))

    def insert_run(
        self,
        run_id: str,
        workflow_id: str,
        runtime: str,
        status: str,
        started_at: str,
        *,
        profile_id: str = "stub",
        isolation: str = "none",
        supervisor_id: Optional[str] = None,
        trace_path: Optional[str] = None,
        audit_path: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Insert or replace a run metadata row."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO runs
                       (id, workflow_id, runtime, status, started_at,
                        profile_id, isolation, supervisor_id,
                        trace_path, audit_path, metadata)
                       VALUES (?,?,?,?,?, ?,?,?, ?,?,?)""",
                    (
                        run_id,
                        workflow_id,
                        runtime,
                        status,
                        started_at,
                        profile_id,
                        isolation,
                        supervisor_id,
                        trace_path,
                        audit_path,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("SQLite insert_run failed for %s: %s", run_id, e)

    def update_run_status(
        self,
        run_id: str,
        status: str,
        ended_at: str,
        *,
        duration_ms: Optional[int] = None,
        cancel_reason: Optional[str] = None,
        error_detail: Optional[str] = None,
    ) -> None:
        """Update run status, ended_at, and optional completion fields."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE runs SET status=?, ended_at=?,
                       duration_ms=?, cancel_reason=?, error_detail=?,
                       updated_at=datetime('now')
                       WHERE id=?""",
                    (status, ended_at, duration_ms, cancel_reason, error_detail, run_id),
                )
        except Exception as e:
            log.warning("SQLite update_run_status failed for %s: %s", run_id, e)

    def update_run_audit_path(self, run_id: str, audit_path: str) -> None:
        """Set audit_path after run completes and audit chain is written."""
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE runs SET audit_path=?, updated_at=datetime('now') WHERE id=?",
                    (audit_path, run_id),
                )
        except Exception as e:
            log.warning("SQLite update_run_audit_path failed for %s: %s", run_id, e)

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single run metadata row."""
        try:
            with self._conn() as conn:
                cur = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,))
                row = cur.fetchone()
                if row is None:
                    return None
                columns = [d[0] for d in cur.description]
                return dict(zip(columns, row))
        except Exception as e:
            log.warning("SQLite get_run failed for %s: %s", run_id, e)
            return None

    def list_runs(
        self,
        *,
        status: Optional[str] = None,
        runtime: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List runs with optional filters. Returns metadata rows, not full records."""
        try:
            where_clauses: list[str] = []
            params: list[Any] = []
            if status:
                where_clauses.append("status = ?")
                params.append(status)
            if runtime:
                where_clauses.append("runtime = ?")
                params.append(runtime)
            if workflow_id:
                where_clauses.append("workflow_id = ?")
                params.append(workflow_id)
            where_sql = ""
            if where_clauses:
                where_sql = " WHERE " + " AND ".join(where_clauses)
            with self._conn() as conn:
                cur = conn.execute(
                    f"SELECT * FROM runs{where_sql} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                    params + [limit, offset],
                )
                columns = [d[0] for d in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            log.warning("SQLite list_runs failed: %s", e)
            return []

    def count_runs(self) -> int:
        """Return total number of indexed runs."""
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT COUNT(*) FROM runs").fetchone()
                return row[0] if row else 0
        except Exception as e:
            log.warning("SQLite count_runs failed: %s", e)
            return 0

    def run_exists(self, run_id: str) -> bool:
        """Check if a run is already indexed."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT 1 FROM runs WHERE id=?", (run_id,)
                ).fetchone()
                return row is not None
        except Exception as e:
            log.warning("SQLite run_exists failed for %s: %s", run_id, e)
            return False
