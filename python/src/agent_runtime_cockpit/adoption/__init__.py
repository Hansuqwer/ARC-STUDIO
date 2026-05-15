"""Adoption layer — shared SwarmGraph orchestration interface (P1b).

Provides the protocol, registry, and runner skeleton for wrapping
external runtimes inside SwarmGraph queen/worker orchestration.
"""
from __future__ import annotations

from .protocol import (
    AdoptionMode,
    AdoptionSpec,
    WorkerTask,
    WorkerProposal,
    Vote,
    ConsensusResult,
    AdoptionStatus,
    AdoptionCapability,
    AdoptionRunner,
)
from .registry import AdoptionRegistry

__all__ = [
    "AdoptionMode",
    "AdoptionSpec",
    "WorkerTask",
    "WorkerProposal",
    "Vote",
    "ConsensusResult",
    "AdoptionStatus",
    "AdoptionCapability",
    "AdoptionRunner",
    "AdoptionRegistry",
]
