"""SQLite-based HITL storage for persistent prompts and decisions (Phase 29 / R22)."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

from agent_runtime_cockpit.audit.hitl import HitlDecision, HitlPrompt, HitlResponse

log = logging.getLogger(__name__)
DEFAULT_HITL_DB_PATH = Path(".arc") / "hitl.db"
DEFAULT_EXPIRY_SECONDS = 3600

# HITL storage schema
HITL_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_prompts (
    hitl_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    context TEXT NOT NULL,
    options TEXT NOT NULL,
    timeout_seconds INTEGER DEFAULT 300,
    created_at TEXT NOT NULL,
    expires_at REAL NOT NULL,
    token TEXT NOT NULL,
    responded INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_hitl_prompts_run ON hitl_prompts(run_id);
CREATE INDEX IF NOT EXISTS idx_hitl_prompts_expires ON hitl_prompts(expires_at);
CREATE INDEX IF NOT EXISTS idx_hitl_prompts_responded ON hitl_prompts(responded);

CREATE TABLE IF NOT EXISTS hitl_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hitl_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    operator_id TEXT DEFAULT 'anonymous',
    modified_data TEXT,
    notes TEXT DEFAULT '',
    responded_at TEXT NOT NULL,
    audit_hash TEXT,
    FOREIGN KEY (hitl_id) REFERENCES hitl_prompts(hitl_id)
);

CREATE INDEX IF NOT EXISTS idx_hitl_responses_hitl ON hitl_responses(hitl_id);
CREATE INDEX IF NOT EXISTS idx_hitl_responses_run ON hitl_responses(run_id);

CREATE TABLE IF NOT EXISTS _hitl_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class HitlSqliteStore:
    """SQLite storage for HITL prompts and responses."""

    def __init__(self, db_path: Path = DEFAULT_HITL_DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """Ensure tables exist. Idempotent."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.executescript(HITL_SCHEMA)
            log.info("HITL DB initialised: %s", self.db_path)
        except Exception as e:
            log.warning("Failed to init HITL DB: %s", e)

    def _ensure_init(self) -> None:
        """Auto-init if the DB file doesn't exist yet."""
        if not self.db_path.exists():
            self.init_db()

    def _conn(self) -> sqlite3.Connection:
        self._ensure_init()
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def save_prompt(
        self,
        prompt: HitlPrompt,
        expiry_seconds: int = DEFAULT_EXPIRY_SECONDS,
    ) -> str:
        """Save a HITL prompt with expiry and single-use token.

        Returns the generated token.
        """
        token = uuid4().hex
        expires_at = time.time() + expiry_seconds

        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO hitl_prompts
                       (hitl_id, run_id, step_id, prompt_text, context, options,
                        timeout_seconds, created_at, expires_at, token, responded)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        prompt.hitl_id,
                        prompt.run_id,
                        prompt.step_id,
                        prompt.prompt_text,
                        json.dumps(prompt.context),
                        json.dumps(prompt.options),
                        prompt.timeout_seconds,
                        prompt.created_at,
                        expires_at,
                        token,
                        0,
                    ),
                )
            log.info("HITL prompt saved: %s", prompt.hitl_id)
            return token
        except Exception as e:
            log.error("Failed to save HITL prompt %s: %s", prompt.hitl_id, e)
            raise

    def list_prompts(self, include_expired: bool = False) -> list[HitlPrompt]:
        """List pending HITL prompts, excluding expired ones by default."""
        try:
            now = time.time()
            query = "SELECT * FROM hitl_prompts WHERE responded = 0"

            if not include_expired:
                query += " AND expires_at > ?"
                params = (now,)
            else:
                params = ()

            query += " ORDER BY created_at DESC"

            with self._conn() as conn:
                rows = conn.execute(query, params).fetchall()
                prompts = []
                for row in rows:
                    prompt = HitlPrompt(
                        hitl_id=row["hitl_id"],
                        run_id=row["run_id"],
                        step_id=row["step_id"],
                        prompt_text=row["prompt_text"],
                        context=json.loads(row["context"]),
                        options=json.loads(row["options"]),
                        timeout_seconds=row["timeout_seconds"],
                        created_at=row["created_at"],
                    )
                    prompts.append(prompt)
                return prompts
        except Exception as e:
            log.error("Failed to list HITL prompts: %s", e)
            return []

    def get_prompt(self, hitl_id: str) -> Optional[HitlPrompt]:
        """Get a specific HITL prompt by ID."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM hitl_prompts WHERE hitl_id = ?", (hitl_id,)
                ).fetchone()

                if not row:
                    return None

                return HitlPrompt(
                    hitl_id=row["hitl_id"],
                    run_id=row["run_id"],
                    step_id=row["step_id"],
                    prompt_text=row["prompt_text"],
                    context=json.loads(row["context"]),
                    options=json.loads(row["options"]),
                    timeout_seconds=row["timeout_seconds"],
                    created_at=row["created_at"],
                )
        except Exception as e:
            log.error("Failed to get HITL prompt %s: %s", hitl_id, e)
            return None

    def get_token(self, hitl_id: str) -> Optional[str]:
        """Get the single-use token for a pending prompt."""
        try:
            now = time.time()
            with self._conn() as conn:
                row = conn.execute(
                    """SELECT token FROM hitl_prompts
                       WHERE hitl_id = ? AND responded = 0 AND expires_at > ?""",
                    (hitl_id, now),
                ).fetchone()

                if row:
                    return row["token"]
                return None
        except Exception as e:
            log.error("Failed to get token for %s: %s", hitl_id, e)
            return None

    def respond(
        self,
        hitl_id: str,
        decision: HitlDecision,
        token: str,
        operator_id: str = "anonymous",
        notes: str = "",
        audit_hash: Optional[str] = None,
    ) -> Optional[HitlResponse]:
        """Respond to a HITL prompt with token validation.

        Returns None if prompt not found, expired, already responded, or token mismatch.
        """
        try:
            now = time.time()

            # Verify token and get prompt
            with self._conn() as conn:
                row = conn.execute(
                    """SELECT * FROM hitl_prompts
                       WHERE hitl_id = ? AND responded = 0 AND expires_at > ?""",
                    (hitl_id, now),
                ).fetchone()

                if not row:
                    log.warning("HITL prompt not found or expired: %s", hitl_id)
                    return None

                stored_token = row["token"]
                if not token or token != stored_token:
                    log.warning("Token mismatch for HITL prompt: %s", hitl_id)
                    return None

                run_id = row["run_id"]

                # Mark prompt as responded
                conn.execute("UPDATE hitl_prompts SET responded = 1 WHERE hitl_id = ?", (hitl_id,))

                # Save response
                from datetime import datetime, timezone

                responded_at = datetime.now(timezone.utc).isoformat()

                conn.execute(
                    """INSERT INTO hitl_responses
                       (hitl_id, run_id, decision, operator_id, modified_data, notes, responded_at, audit_hash)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        hitl_id,
                        run_id,
                        decision.value,
                        operator_id,
                        None,  # modified_data not implemented yet
                        notes,
                        responded_at,
                        audit_hash,
                    ),
                )

                log.info("HITL response saved: %s (decision: %s)", hitl_id, decision.value)

                return HitlResponse(
                    hitl_id=hitl_id,
                    run_id=run_id,
                    decision=decision,
                    operator_id=operator_id,
                    notes=notes,
                    responded_at=responded_at,
                )
        except Exception as e:
            log.error("Failed to respond to HITL prompt %s: %s", hitl_id, e)
            return None

    def get_response(self, hitl_id: str) -> Optional[HitlResponse]:
        """Get the response for a HITL prompt."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM hitl_responses WHERE hitl_id = ? ORDER BY id DESC LIMIT 1",
                    (hitl_id,),
                ).fetchone()

                if not row:
                    return None

                return HitlResponse(
                    hitl_id=row["hitl_id"],
                    run_id=row["run_id"],
                    decision=HitlDecision(row["decision"]),
                    operator_id=row["operator_id"],
                    modified_data=json.loads(row["modified_data"])
                    if row["modified_data"]
                    else None,
                    notes=row["notes"],
                    responded_at=row["responded_at"],
                )
        except Exception as e:
            log.error("Failed to get HITL response %s: %s", hitl_id, e)
            return None

    def prune_expired(self) -> int:
        """Remove expired pending prompts. Returns count pruned."""
        try:
            now = time.time()
            with self._conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM hitl_prompts WHERE responded = 0 AND expires_at < ?", (now,)
                )
                pruned = cursor.rowcount
            log.info("Pruned %d expired HITL prompts", pruned)
            return pruned
        except Exception as e:
            log.error("Failed to prune expired HITL prompts: %s", e)
            return 0

    def list_responses_for_run(self, run_id: str) -> list[HitlResponse]:
        """List all responses for a specific run."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM hitl_responses WHERE run_id = ? ORDER BY responded_at DESC",
                    (run_id,),
                ).fetchall()

                responses = []
                for row in rows:
                    response = HitlResponse(
                        hitl_id=row["hitl_id"],
                        run_id=row["run_id"],
                        decision=HitlDecision(row["decision"]),
                        operator_id=row["operator_id"],
                        modified_data=json.loads(row["modified_data"])
                        if row["modified_data"]
                        else None,
                        notes=row["notes"],
                        responded_at=row["responded_at"],
                    )
                    responses.append(response)
                return responses
        except Exception as e:
            log.error("Failed to list responses for run %s: %s", run_id, e)
            return []
