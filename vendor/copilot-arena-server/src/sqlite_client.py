"""SQLite client replacing Firebase for local arena server.

Stores completions, outcomes (votes), and users in a local SQLite database.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path("data/arena.db")


class SQLiteClient:
    """Local SQLite storage for arena data."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS completions (
                    completion_id TEXT PRIMARY KEY,
                    pair_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    completion TEXT NOT NULL,
                    prompt TEXT,
                    timestamp INTEGER NOT NULL,
                    pair_index INTEGER NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS outcomes (
                    pair_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    accepted_index INTEGER NOT NULL,
                    completion_items TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    created_at INTEGER NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_completions_user ON completions(user_id);
                CREATE INDEX IF NOT EXISTS idx_outcomes_user ON outcomes(user_id);
            """)

    def upload_completion(self, data: dict[str, Any]):
        """Store a completion record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO completions 
                   (completion_id, pair_id, user_id, model, completion, prompt, timestamp, pair_index)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["completionId"],
                    data.get("pairCompletionId", data["completionId"]),
                    data["userId"],
                    data["model"],
                    data["completion"],
                    data.get("prompt", ""),
                    data["timestamp"],
                    data.get("pairIndex", 0),
                ),
            )

    def upload_outcome(self, data: dict[str, Any]):
        """Store a vote/outcome record."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO outcomes 
                   (pair_id, user_id, accepted_index, completion_items, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    data["pairId"],
                    data["userId"],
                    data["acceptedIndex"],
                    json.dumps(data["completionItems"]),
                    data.get("timestamp", int(datetime.now().timestamp())),
                ),
            )

    def get_user_outcomes(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all outcomes for a user."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT pair_id, user_id, accepted_index, completion_items, timestamp FROM outcomes WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            return [
                {
                    "pairId": r[0],
                    "userId": r[1],
                    "acceptedIndex": r[2],
                    "completionItems": json.loads(r[3]),
                    "timestamp": r[4],
                }
                for r in rows
            ]

    def get_all_outcomes(self) -> list[dict[str, Any]]:
        """Retrieve all outcomes (for global ELO)."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT pair_id, user_id, accepted_index, completion_items, timestamp FROM outcomes"
            ).fetchall()
            return [
                {
                    "pairId": r[0],
                    "userId": r[1],
                    "acceptedIndex": r[2],
                    "completionItems": json.loads(r[3]),
                    "timestamp": r[4],
                }
                for r in rows
            ]

    def create_user(self, user_id: str, username: str, password_hash: str | None = None):
        """Create a new user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (user_id, username, password_hash, int(datetime.now().timestamp())),
            )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Retrieve a user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, username, password_hash, created_at FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row:
                return {
                    "userId": row[0],
                    "username": row[1],
                    "passwordHash": row[2],
                    "createdAt": row[3],
                }
            return None

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """Retrieve a user by username."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT user_id, username, password_hash, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row:
                return {
                    "userId": row[0],
                    "username": row[1],
                    "passwordHash": row[2],
                    "createdAt": row[3],
                }
            return None
