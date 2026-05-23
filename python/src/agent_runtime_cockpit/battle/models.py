"""Battle models for ARC Battle Mode (Phase 34/R26A).

ARC-native, offline-first SwarmGraph battle mode for CLI and IDE.
No provider-backed/live claims. Offline/fake mode only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BattleStatus(str, Enum):
    """Battle run status."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class BattleTopology(str, Enum):
    """Battle topology (flat only for baseline)."""

    flat = "flat"


class ConsensusProtocol(str, Enum):
    """Consensus protocol for battle voting."""

    majority = "majority"
    quorum = "quorum"


class VoterType(str, Enum):
    """Type of voter (human or model)."""

    human = "human"
    model = "model"


class BattleRun(BaseModel):
    """Battle run record.

    Represents a single battle instance where multiple workers compete
    to produce the best solution for a given prompt.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"battle-{uuid.uuid4().hex[:12]}")
    prompt: str = Field(..., min_length=1, max_length=8192)
    workers: int = Field(..., ge=2, le=4)  # 2 or 4 workers for baseline
    topology: BattleTopology = Field(default=BattleTopology.flat)
    consensus_protocol: ConsensusProtocol = Field(default=ConsensusProtocol.majority)
    runtime_mode: str = Field(default="fake/offline", max_length=64)
    status: BattleStatus = Field(default=BattleStatus.pending)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Optional fields
    consensus_escrow: bool = Field(default=False)
    require_hitl: bool = Field(default=False)
    error_detail: str | None = Field(default=None, max_length=4096)

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)


class BattleCandidate(BaseModel):
    """Battle candidate (worker output).

    Represents a single worker's solution to the battle prompt.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"candidate-{uuid.uuid4().hex[:12]}")
    battle_id: str = Field(..., min_length=1)
    worker_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)  # For ELO tracking
    output: str = Field(..., min_length=1, max_length=32768)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)


class BattleVote(BaseModel):
    """Battle vote on a candidate.

    Represents a single vote (human or model) on a candidate solution.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"vote-{uuid.uuid4().hex[:12]}")
    battle_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    voter: str = Field(..., min_length=1)  # Voter identifier
    voter_type: VoterType = Field(default=VoterType.human)
    approved: bool = Field(...)
    reasoning: str = Field(default="", max_length=4096)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Commit-reveal fields (optional, for consensus escrow)
    commit_hash: str | None = Field(default=None, max_length=128)
    reveal_nonce: str | None = Field(default=None, max_length=128)

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)


class BattleOutcome(BaseModel):
    """Battle outcome (final result).

    Represents the final result of a battle after consensus is reached.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"outcome-{uuid.uuid4().hex[:12]}")
    battle_id: str = Field(..., min_length=1)
    winner_candidate_id: str | None = Field(default=None)  # None if no consensus
    consensus_reached: bool = Field(...)
    consensus_result: dict[str, Any] = Field(default_factory=dict)  # Full consensus data
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)


class EloRating(BaseModel):
    """ELO rating for a model.

    Tracks model performance across battles using ELO rating system.
    Keyed by model_id, not worker role.
    """

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(..., min_length=1)
    rating: float = Field(default=1500.0)  # Standard ELO starting rating
    games_played: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)


# Helper functions for ELO calculation
def calculate_elo_change(
    winner_rating: float,
    loser_rating: float,
    k_factor: float = 32.0,
) -> tuple[float, float]:
    """Calculate ELO rating changes for winner and loser.

    Args:
        winner_rating: Current rating of the winner
        loser_rating: Current rating of the loser
        k_factor: K-factor for ELO calculation (default 32)

    Returns:
        Tuple of (winner_new_rating, loser_new_rating)
    """
    # Expected scores
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))

    # Actual scores (1 for win, 0 for loss)
    actual_winner = 1.0
    actual_loser = 0.0

    # New ratings
    new_winner_rating = winner_rating + k_factor * (actual_winner - expected_winner)
    new_loser_rating = loser_rating + k_factor * (actual_loser - expected_loser)

    return new_winner_rating, new_loser_rating


def calculate_elo_draw(
    rating_a: float,
    rating_b: float,
    k_factor: float = 32.0,
) -> tuple[float, float]:
    """Calculate ELO rating changes for a draw.

    Args:
        rating_a: Current rating of player A
        rating_b: Current rating of player B
        k_factor: K-factor for ELO calculation (default 32)

    Returns:
        Tuple of (new_rating_a, new_rating_b)
    """
    # Expected scores
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 / (1 + 10 ** ((rating_a - rating_b) / 400))

    # Actual scores (0.5 for draw)
    actual_a = 0.5
    actual_b = 0.5

    # New ratings
    new_rating_a = rating_a + k_factor * (actual_a - expected_a)
    new_rating_b = rating_b + k_factor * (actual_b - expected_b)

    return new_rating_a, new_rating_b
