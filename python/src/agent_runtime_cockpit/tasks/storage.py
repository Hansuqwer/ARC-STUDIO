"""SQLite storage for ARC task registry."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType

log = logging.getLogger(__name__)
DEFAULT_TASK_DB_PATH = Path(".arc") / "tasks.db"

# Task registry schema
TASK_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    operation TEXT NOT NULL,
    params TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    expires_at TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_expires ON tasks(expires_at);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_next_retry ON tasks(next_retry_at);

CREATE TABLE IF NOT EXISTS _task_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class TaskStorage:
    """SQLite storage for task registry."""

    def __init__(self, db_path: Path = DEFAULT_TASK_DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """Ensure tables exist. Idempotent."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executescript(TASK_SCHEMA)
            log.info("Task DB initialised: %s", self.db_path)
        except Exception as e:
            log.warning("Failed to init task DB: %s", e)

    def _ensure_init(self) -> None:
        """Auto-init if the DB file doesn't exist yet."""
        if not self.db_path.exists():
            self.init_db()

    def _conn(self) -> sqlite3.Connection:
        self._ensure_init()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA wal_autocheckpoint = 1000")
        conn.row_factory = sqlite3.Row
        return conn

    def create_task(self, task: Task) -> None:
        """Create a new task."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO tasks
                       (id, type, operation, params, status, result, error,
                        created_at, started_at, ended_at, expires_at,
                        retry_count, max_retries, next_retry_at)
                       VALUES (?,?,?,?,?,?,?, ?,?,?,?, ?,?,?)""",
                    (
                        task.id,
                        task.type.value,
                        task.operation,
                        json.dumps(task.params),
                        task.status.value,
                        json.dumps(task.result) if task.result else None,
                        task.error,
                        task.created_at,
                        task.started_at,
                        task.ended_at,
                        task.expires_at,
                        task.retry_count,
                        task.max_retries,
                        task.next_retry_at,
                    ),
                )
            log.info("Task created: %s", task.id)
        except Exception as e:
            log.error("Failed to create task %s: %s", task.id, e)
            raise

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        try:
            with self._conn() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
                if row:
                    return self._row_to_task(row)
                return None
        except Exception as e:
            log.error("Failed to get task %s: %s", task_id, e)
            return None

    def update_task(self, task: Task) -> None:
        """Update existing task."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE tasks SET
                       type=?, operation=?, params=?, status=?, result=?, error=?,
                       created_at=?, started_at=?, ended_at=?, expires_at=?,
                       retry_count=?, max_retries=?, next_retry_at=?
                       WHERE id=?""",
                    (
                        task.type.value,
                        task.operation,
                        json.dumps(task.params),
                        task.status.value,
                        json.dumps(task.result) if task.result else None,
                        task.error,
                        task.created_at,
                        task.started_at,
                        task.ended_at,
                        task.expires_at,
                        task.retry_count,
                        task.max_retries,
                        task.next_retry_at,
                        task.id,
                    ),
                )
            log.info("Task updated: %s", task.id)
        except Exception as e:
            log.error("Failed to update task %s: %s", task.id, e)
            raise

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 100,
    ) -> list[Task]:
        """List tasks with optional filters."""
        try:
            query = "SELECT * FROM tasks WHERE 1=1"
            params: list[str] = []

            if status:
                query += " AND status = ?"
                params.append(status.value)

            if task_type:
                query += " AND type = ?"
                params.append(task_type.value)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(str(limit))

            with self._conn() as conn:
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_task(row) for row in rows]
        except Exception as e:
            log.error("Failed to list tasks: %s", e)
            return []

    def get_tasks_for_retry(self) -> list[Task]:
        """Get tasks that are ready for retry."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM tasks
                       WHERE status = 'failed'
                       AND retry_count < max_retries
                       AND (next_retry_at IS NULL OR next_retry_at <= ?)
                       ORDER BY next_retry_at ASC""",
                    (now,),
                ).fetchall()
                return [self._row_to_task(row) for row in rows]
        except Exception as e:
            log.error("Failed to get tasks for retry: %s", e)
            return []

    def delete_expired_tasks(self) -> int:
        """Delete expired tasks. Returns count of deleted tasks."""
        try:
            now = datetime.now(timezone.utc).isoformat()
            with self._conn() as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE expires_at < ?", (now,))
                deleted = cursor.rowcount
            log.info("Deleted %d expired tasks", deleted)
            return deleted
        except Exception as e:
            log.error("Failed to delete expired tasks: %s", e)
            return 0

    def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID. Returns True if deleted."""
        try:
            with self._conn() as conn:
                cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                deleted = cursor.rowcount > 0
            if deleted:
                log.info("Task deleted: %s", task_id)
            return deleted
        except Exception as e:
            log.error("Failed to delete task %s: %s", task_id, e)
            return False

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        return Task(
            id=row["id"],
            type=TaskType(row["type"]),
            operation=row["operation"],
            params=json.loads(row["params"]),
            status=TaskStatus(row["status"]),
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            expires_at=row["expires_at"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            next_retry_at=row["next_retry_at"],
        )
