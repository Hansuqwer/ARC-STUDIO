"""Adoption protocol — shared interface for all runtime + SwarmGraph modes (P1b).

Defines the Pydantic models and abstract runner that every adoption adapter
must implement. Runners may return RUNNABLE status when dependencies and gates
are satisfied; default behavior is NOT_IMPLEMENTED or NOT_RUNNABLE.
"""

from __future__ import annotations

import abc
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class AdoptionMode(str, Enum):
    """Canonical ``<runtime>+swarmgraph`` runtime IDs."""

    LANGGRAPH = "langgraph+swarmgraph"
    AG2 = "ag2+swarmgraph"
    CREWAI = "crewai+swarmgraph"
    OPENAI_AGENTS = "openai_agents+swarmgraph"
    LLAMAINDEX = "llamaindex+swarmgraph"


class AdoptionSpec(BaseModel):
    """Input specification for an adoption run."""

    mode: AdoptionMode
    runtime_config: dict[str, Any] = Field(default_factory=dict)
    swarmgraph_config: dict[str, Any] = Field(default_factory=dict)
    max_workers: int = 3
    consensus_threshold: float = 0.67


class WorkerTask(BaseModel):
    """A single worker task assigned by the SwarmGraph queen."""

    task_id: str
    worker_id: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    runtime: str


class WorkerProposal(BaseModel):
    """Output produced by one worker for one task."""

    task_id: str
    worker_id: str
    output: str
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Vote(BaseModel):
    """A vote cast on a worker proposal."""

    task_id: str
    voter_id: str
    proposal_id: str
    score: float
    reason: str = ""


class ConsensusResult(BaseModel):
    """Final consensus outcome for one task."""

    task_id: str
    winning_proposal: WorkerProposal
    votes: list[Vote] = Field(default_factory=list)
    consensus_reached: bool
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdoptionStatus(str, Enum):
    """Honest status for adoption runners."""

    NOT_IMPLEMENTED = "not_implemented"
    NOT_RUNNABLE = "not_runnable"
    RUNNABLE = "runnable"


class AdoptionCapability(BaseModel):
    """Capability report for one adoption mode."""

    mode: AdoptionMode
    status: AdoptionStatus
    reason: str = ""
    doctor_actions: list[dict[str, str]] = Field(default_factory=list)


class AdoptionRunner(abc.ABC):
    """Abstract base for an adoption adapter (one per runtime)."""

    @property
    @abc.abstractmethod
    def mode(self) -> AdoptionMode:
        """Return the adoption mode this runner handles."""
        ...

    @abc.abstractmethod
    def check_availability(self, workspace: Path) -> AdoptionCapability:
        """Report whether the adoption mode is runnable in the given workspace."""
        ...

    @abc.abstractmethod
    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute the adoption run."""
        ...

    @abc.abstractmethod
    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream worker-level events for live UI."""
        yield {}
