"""ARC Battle Mode (Phase 34/R26A).

ARC-native, offline-first SwarmGraph battle mode for CLI and IDE.
No provider-backed/live claims. Offline/fake mode only.
"""

from .models import (
    BattleCandidate,
    BattleOutcome,
    BattleRun,
    BattleStatus,
    BattleTopology,
    BattleVote,
    ConsensusProtocol,
    EloRating,
    VoterType,
    calculate_elo_change,
    calculate_elo_draw,
)
from .runner import BattleRunner
from .store import BattleStore

__all__ = [
    "BattleCandidate",
    "BattleOutcome",
    "BattleRun",
    "BattleRunner",
    "BattleStatus",
    "BattleStore",
    "BattleTopology",
    "BattleVote",
    "ConsensusProtocol",
    "EloRating",
    "VoterType",
    "calculate_elo_change",
    "calculate_elo_draw",
]
