from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ConsensusProtocol(str, Enum):
    majority = "majority"
    quorum = "quorum"
    raft = "raft"
    bft = "bft"
    gossip = "gossip"
    bft_escrow = "bft_escrow"
    selective_debate = "selective_debate"
    confidence_weighted = "confidence_weighted"
    critic_verifier = "critic_verifier"
    hitl_signoff = "hitl_signoff"


class SwarmStrategy(str, Enum):
    fan_out = "fan_out"
    sequential = "sequential"
    hierarchical = "hierarchical"


class SwarmTopology(str, Enum):
    star = "star"
    chain = "chain"
    mesh = "mesh"
    tree = "tree"


class ComplexityTier(str, Enum):
    simple = "simple"
    moderate = "moderate"
    complex = "complex"
    critical = "critical"


class ExecutionMode(str, Enum):
    fake_offline = "fake_offline"
    gated_local = "gated_local"
    provider_backed = "provider_backed"


class SwarmGraphConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(default="default-swarm", min_length=1, max_length=128)
    version: str = Field(default="0.1.0", max_length=32)

    num_workers: int = Field(default=3, ge=1, le=50)
    max_rounds: int = Field(default=3, ge=1, le=100)
    quorum_size: int | None = Field(default=None, ge=1)
    consensus_protocol: ConsensusProtocol = Field(default=ConsensusProtocol.majority)
    strategy: SwarmStrategy = Field(default=SwarmStrategy.fan_out)
    topology: SwarmTopology = Field(default=SwarmTopology.star)

    execution_mode: ExecutionMode = Field(default=ExecutionMode.fake_offline)
    allow_paid_calls: bool = Field(default=False)
    require_hitl: bool = Field(default=False)
    enable_audit: bool = Field(default=False)
    enable_budget: bool = Field(default=False)
    budget_limit_usd: float | None = Field(default=None, ge=0)
    audit_secret: str | None = Field(default=None, min_length=8, max_length=256)

    worker_timeout_seconds: float = Field(default=30.0, ge=1, le=600)
    poll_interval_seconds: float = Field(default=0.1, ge=0.01, le=10)
    fan_out_threshold: float = Field(default=0.6, ge=0, le=1.0)
    max_parallel_workers: int = Field(default=3, ge=1, le=50)

    def effective_quorum(self, num_workers: int) -> int:
        if self.quorum_size is not None:
            return self.quorum_size
        return max(1, num_workers // 2 + 1)
