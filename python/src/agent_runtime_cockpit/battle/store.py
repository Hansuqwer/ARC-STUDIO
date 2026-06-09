"""SQLite store for ARC Battle Mode (Phase 34/R26A).

Stores battle runs, candidates, votes, outcomes, and ELO ratings.
Compatible with existing arc runs infrastructure.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from .models import (
    BattleCandidate,
    BattleOutcome,
    BattleRun,
    BattleVote,
    EloRating,
)

log = logging.getLogger(__name__)
DEFAULT_BATTLE_DB_PATH = Path(".arc") / "battles.db"

# Battle schema with foreign key constraints
BATTLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS battle_runs (
    id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    workers INTEGER NOT NULL CHECK(workers >= 2 AND workers <= 4),
    topology TEXT NOT NULL DEFAULT 'flat',
    consensus_protocol TEXT NOT NULL DEFAULT 'majority',
    runtime_mode TEXT NOT NULL DEFAULT 'fake/offline',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    consensus_escrow INTEGER NOT NULL DEFAULT 0,
    require_hitl INTEGER NOT NULL DEFAULT 0,
    error_detail TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_battle_runs_status ON battle_runs(status);
CREATE INDEX IF NOT EXISTS idx_battle_runs_created ON battle_runs(created_at);

CREATE TABLE IF NOT EXISTS battle_candidates (
    id TEXT PRIMARY KEY,
    battle_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    output TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (battle_id) REFERENCES battle_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_battle_candidates_battle ON battle_candidates(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_candidates_model ON battle_candidates(model_id);

CREATE TABLE IF NOT EXISTS battle_votes (
    id TEXT PRIMARY KEY,
    battle_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    voter TEXT NOT NULL,
    voter_type TEXT NOT NULL DEFAULT 'human',
    approved INTEGER NOT NULL,
    reasoning TEXT,
    created_at TEXT NOT NULL,
    commit_hash TEXT,
    reveal_nonce TEXT,
    metadata TEXT,
    FOREIGN KEY (battle_id) REFERENCES battle_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES battle_candidates(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_battle_votes_battle ON battle_votes(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_votes_candidate ON battle_votes(candidate_id);
CREATE INDEX IF NOT EXISTS idx_battle_votes_voter ON battle_votes(voter);

CREATE TABLE IF NOT EXISTS battle_outcomes (
    id TEXT PRIMARY KEY,
    battle_id TEXT NOT NULL UNIQUE,
    winner_candidate_id TEXT,
    consensus_reached INTEGER NOT NULL,
    consensus_result TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    metadata TEXT,
    FOREIGN KEY (battle_id) REFERENCES battle_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (winner_candidate_id) REFERENCES battle_candidates(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_battle_outcomes_battle ON battle_outcomes(battle_id);
CREATE INDEX IF NOT EXISTS idx_battle_outcomes_winner ON battle_outcomes(winner_candidate_id);

CREATE TABLE IF NOT EXISTS elo_ratings (
    model_id TEXT PRIMARY KEY,
    rating REAL NOT NULL DEFAULT 1500.0,
    games_played INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_elo_ratings_rating ON elo_ratings(rating DESC);
CREATE INDEX IF NOT EXISTS idx_elo_ratings_games ON elo_ratings(games_played DESC);

CREATE TABLE IF NOT EXISTS _battle_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


class BattleStore:
    """SQLite store for battle data.

    Stores battle runs, candidates, votes, outcomes, and ELO ratings.
    """

    def __init__(self, db_path: Path = DEFAULT_BATTLE_DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """Ensure tables exist. Idempotent."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.executescript(BATTLE_SCHEMA)
            log.info("Battle DB initialized: %s", self.db_path)
        except Exception as e:
            log.warning("Failed to init Battle DB: %s", e)

    def _ensure_init(self) -> None:
        """Auto-init if the DB file doesn't exist yet."""
        if not self.db_path.exists():
            self.init_db()

    def _conn(self) -> sqlite3.Connection:
        self._ensure_init()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA wal_autocheckpoint = 1000")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    # Battle Run operations
    def insert_battle_run(self, battle: BattleRun) -> None:
        """Insert a new battle run."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO battle_runs
                       (id, prompt, workers, topology, consensus_protocol, runtime_mode,
                        status, created_at, started_at, completed_at,
                        consensus_escrow, require_hitl, error_detail, metadata)
                       VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?,?)""",
                    (
                        battle.id,
                        battle.prompt,
                        battle.workers,
                        battle.topology.value,
                        battle.consensus_protocol.value,
                        battle.runtime_mode,
                        battle.status.value,
                        battle.created_at.isoformat(),
                        battle.started_at.isoformat() if battle.started_at else None,
                        battle.completed_at.isoformat() if battle.completed_at else None,
                        1 if battle.consensus_escrow else 0,
                        1 if battle.require_hitl else 0,
                        battle.error_detail,
                        json.dumps(battle.metadata) if battle.metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("Failed to insert battle run %s: %s", battle.id, e)
            raise

    def get_battle_run(self, battle_id: str) -> BattleRun | None:
        """Get a battle run by ID."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM battle_runs WHERE id = ?", (battle_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_battle_run(row)
        except Exception as e:
            log.warning("Failed to get battle run %s: %s", battle_id, e)
            return None

    def update_battle_status(
        self,
        battle_id: str,
        status: str,
        *,
        started_at: str | None = None,
        completed_at: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        """Update battle run status."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """UPDATE battle_runs
                       SET status = ?, started_at = COALESCE(?, started_at),
                           completed_at = COALESCE(?, completed_at),
                           error_detail = COALESCE(?, error_detail)
                       WHERE id = ?""",
                    (status, started_at, completed_at, error_detail, battle_id),
                )
        except Exception as e:
            log.warning("Failed to update battle status %s: %s", battle_id, e)
            raise

    def list_battle_runs(self, *, status: str | None = None, limit: int = 100) -> list[BattleRun]:
        """List battle runs, optionally filtered by status."""
        try:
            with self._conn() as conn:
                if status:
                    rows = conn.execute(
                        """SELECT * FROM battle_runs WHERE status = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """SELECT * FROM battle_runs
                           ORDER BY created_at DESC LIMIT ?""",
                        (limit,),
                    ).fetchall()
                return [self._row_to_battle_run(row) for row in rows]
        except Exception as e:
            log.warning("Failed to list battle runs: %s", e)
            return []

    # Battle Candidate operations
    def insert_candidate(self, candidate: BattleCandidate) -> None:
        """Insert a battle candidate."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO battle_candidates
                       (id, battle_id, worker_id, model_id, output, created_at, metadata)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        candidate.id,
                        candidate.battle_id,
                        candidate.worker_id,
                        candidate.model_id,
                        candidate.output,
                        candidate.created_at.isoformat(),
                        json.dumps(candidate.metadata) if candidate.metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("Failed to insert candidate %s: %s", candidate.id, e)
            raise

    def get_candidates(self, battle_id: str) -> list[BattleCandidate]:
        """Get all candidates for a battle."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM battle_candidates WHERE battle_id = ?
                       ORDER BY created_at""",
                    (battle_id,),
                ).fetchall()
                return [self._row_to_candidate(row) for row in rows]
        except Exception as e:
            log.warning("Failed to get candidates for battle %s: %s", battle_id, e)
            return []

    # Battle Vote operations
    def insert_vote(self, vote: BattleVote) -> None:
        """Insert a battle vote."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO battle_votes
                       (id, battle_id, candidate_id, voter, voter_type, approved,
                        reasoning, created_at, commit_hash, reveal_nonce, metadata)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        vote.id,
                        vote.battle_id,
                        vote.candidate_id,
                        vote.voter,
                        vote.voter_type.value,
                        1 if vote.approved else 0,
                        vote.reasoning,
                        vote.created_at.isoformat(),
                        vote.commit_hash,
                        vote.reveal_nonce,
                        json.dumps(vote.metadata) if vote.metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("Failed to insert vote %s: %s", vote.id, e)
            raise

    def get_votes(self, battle_id: str) -> list[BattleVote]:
        """Get all votes for a battle."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM battle_votes WHERE battle_id = ?
                       ORDER BY created_at""",
                    (battle_id,),
                ).fetchall()
                return [self._row_to_vote(row) for row in rows]
        except Exception as e:
            log.warning("Failed to get votes for battle %s: %s", battle_id, e)
            return []

    def get_votes_for_candidate(self, candidate_id: str) -> list[BattleVote]:
        """Get all votes for a specific candidate."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM battle_votes WHERE candidate_id = ?
                       ORDER BY created_at""",
                    (candidate_id,),
                ).fetchall()
                return [self._row_to_vote(row) for row in rows]
        except Exception as e:
            log.warning("Failed to get votes for candidate %s: %s", candidate_id, e)
            return []

    # Battle Outcome operations
    def insert_outcome(self, outcome: BattleOutcome) -> None:
        """Insert a battle outcome."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO battle_outcomes
                       (id, battle_id, winner_candidate_id, consensus_reached,
                        consensus_result, completed_at, metadata)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        outcome.id,
                        outcome.battle_id,
                        outcome.winner_candidate_id,
                        1 if outcome.consensus_reached else 0,
                        json.dumps(outcome.consensus_result),
                        outcome.completed_at.isoformat(),
                        json.dumps(outcome.metadata) if outcome.metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("Failed to insert outcome %s: %s", outcome.id, e)
            raise

    def get_outcome(self, battle_id: str) -> BattleOutcome | None:
        """Get the outcome for a battle."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM battle_outcomes WHERE battle_id = ?", (battle_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_outcome(row)
        except Exception as e:
            log.warning("Failed to get outcome for battle %s: %s", battle_id, e)
            return None

    # ELO Rating operations
    def upsert_elo_rating(self, rating: EloRating) -> None:
        """Insert or update an ELO rating."""
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT INTO elo_ratings
                       (model_id, rating, games_played, wins, losses, draws,
                        last_updated, metadata)
                       VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(model_id) DO UPDATE SET
                           rating = excluded.rating,
                           games_played = excluded.games_played,
                           wins = excluded.wins,
                           losses = excluded.losses,
                           draws = excluded.draws,
                           last_updated = excluded.last_updated,
                           metadata = excluded.metadata""",
                    (
                        rating.model_id,
                        rating.rating,
                        rating.games_played,
                        rating.wins,
                        rating.losses,
                        rating.draws,
                        rating.last_updated.isoformat(),
                        json.dumps(rating.metadata) if rating.metadata else None,
                    ),
                )
        except Exception as e:
            log.warning("Failed to upsert ELO rating for %s: %s", rating.model_id, e)
            raise

    def get_elo_rating(self, model_id: str) -> EloRating | None:
        """Get ELO rating for a model."""
        try:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM elo_ratings WHERE model_id = ?", (model_id,)
                ).fetchone()
                if not row:
                    return None
                return self._row_to_elo_rating(row)
        except Exception as e:
            log.warning("Failed to get ELO rating for %s: %s", model_id, e)
            return None

    def list_elo_ratings(self, limit: int = 100) -> list[EloRating]:
        """List ELO ratings, ordered by rating descending."""
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    """SELECT * FROM elo_ratings
                       ORDER BY rating DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
                return [self._row_to_elo_rating(row) for row in rows]
        except Exception as e:
            log.warning("Failed to list ELO ratings: %s", e)
            return []

    # Helper methods to convert rows to models
    def _row_to_battle_run(self, row: sqlite3.Row) -> BattleRun:
        """Convert a database row to a BattleRun model."""
        from datetime import datetime

        return BattleRun(
            id=row["id"],
            prompt=row["prompt"],
            workers=row["workers"],
            topology=row["topology"],
            consensus_protocol=row["consensus_protocol"],
            runtime_mode=row["runtime_mode"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            consensus_escrow=bool(row["consensus_escrow"]),
            require_hitl=bool(row["require_hitl"]),
            error_detail=row["error_detail"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_candidate(self, row: sqlite3.Row) -> BattleCandidate:
        """Convert a database row to a BattleCandidate model."""
        from datetime import datetime

        return BattleCandidate(
            id=row["id"],
            battle_id=row["battle_id"],
            worker_id=row["worker_id"],
            model_id=row["model_id"],
            output=row["output"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_vote(self, row: sqlite3.Row) -> BattleVote:
        """Convert a database row to a BattleVote model."""
        from datetime import datetime

        return BattleVote(
            id=row["id"],
            battle_id=row["battle_id"],
            candidate_id=row["candidate_id"],
            voter=row["voter"],
            voter_type=row["voter_type"],
            approved=bool(row["approved"]),
            reasoning=row["reasoning"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            commit_hash=row["commit_hash"],
            reveal_nonce=row["reveal_nonce"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_outcome(self, row: sqlite3.Row) -> BattleOutcome:
        """Convert a database row to a BattleOutcome model."""
        from datetime import datetime

        return BattleOutcome(
            id=row["id"],
            battle_id=row["battle_id"],
            winner_candidate_id=row["winner_candidate_id"],
            consensus_reached=bool(row["consensus_reached"]),
            consensus_result=json.loads(row["consensus_result"]),
            completed_at=datetime.fromisoformat(row["completed_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_elo_rating(self, row: sqlite3.Row) -> EloRating:
        """Convert a database row to an EloRating model."""
        from datetime import datetime

        return EloRating(
            model_id=row["model_id"],
            rating=row["rating"],
            games_played=row["games_played"],
            wins=row["wins"],
            losses=row["losses"],
            draws=row["draws"],
            last_updated=datetime.fromisoformat(row["last_updated"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
