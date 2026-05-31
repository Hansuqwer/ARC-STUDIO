from __future__ import annotations

# ruff: noqa: E402

from pathlib import Path

_CANDIDATES = (
    Path(__file__).resolve().parents[3] / "src" / "agent_runtime_cockpit" / "swarmgraph",
    Path.cwd() / "src" / "agent_runtime_cockpit" / "swarmgraph",
    Path.cwd() / "python" / "src" / "agent_runtime_cockpit" / "swarmgraph",
)
for _path in _CANDIDATES:
    if _path.exists():
        __path__.insert(0, str(_path))
        break

from .checkpoint import CheckpointStore, JsonFileCheckpointStore
from .config import SwarmGraphConfig
from .consensus import (
    ConsensusResult,
    bft_consensus,
    confidence_weighted_consensus,
    critic_verifier_consensus,
    gossip_consensus,
    hitl_signoff_quorum,
    majority_consensus,
    quorum_consensus,
    raft_consensus,
    run_consensus,
    selective_debate_consensus,
)
from .decomposition import (
    CopyDecomposition,
    DecompositionStrategy,
    StepDecomposition,
    TrivialDecomposition,
    parallelizability_score,
)
from .detectors import (
    detect_consensus_failure,
    detect_coordination_deadlock,
    detect_resource_exhaustion,
)
from .events import (
    AuditEvent,
    BudgetEvent,
    ConsensusEvent,
    HITLEvent,
    SwarmGraphEvent,
    SwarmGraphEventKind,
    TopologyEvent,
    WorkerEvent,
)
from .fixtures import run_deterministic_swarm
from .graph import build_swarm_graph
from .models import (
    AgentSpec,
    AgentState,
    AgentVote,
    ApprovalDecision,
    QueenDirective,
    SwarmTask,
    WorkerResult,
)
from .providers import (
    CostRates,
    Provider,
    ProviderCapability,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from .risk_assessment import (
    CONSENSUS_PROTOCOL_BY_RISK,
    RISK_FIXTURES,
    SIGNAL_WEIGHTS,
    SIGNALS,
    ProtocolSelection,
    RiskAssessment,
    RiskFixture,
    RiskLevel,
    assess_prompt_risk,
    select_consensus_protocol,
)
from .runner import SwarmGraphRunner, SwarmRunResult, SwarmRunTaskResult
from .state import SwarmCheckpoint, SwarmState

__all__ = [
    "SwarmGraphConfig",
    "CheckpointStore",
    "JsonFileCheckpointStore",
    "AgentSpec",
    "AgentState",
    "AgentVote",
    "ApprovalDecision",
    "WorkerResult",
    "SwarmTask",
    "QueenDirective",
    "Provider",
    "ProviderMessage",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderCapability",
    "UsageRecord",
    "CostRates",
    "SwarmState",
    "SwarmCheckpoint",
    "ConsensusResult",
    "majority_consensus",
    "quorum_consensus",
    "raft_consensus",
    "bft_consensus",
    "selective_debate_consensus",
    "confidence_weighted_consensus",
    "critic_verifier_consensus",
    "hitl_signoff_quorum",
    "gossip_consensus",
    "run_consensus",
    "DecompositionStrategy",
    "CopyDecomposition",
    "StepDecomposition",
    "TrivialDecomposition",
    "parallelizability_score",
    "detect_consensus_failure",
    "detect_resource_exhaustion",
    "detect_coordination_deadlock",
    "RiskAssessment",
    "ProtocolSelection",
    "RiskFixture",
    "RiskLevel",
    "assess_prompt_risk",
    "select_consensus_protocol",
    "CONSENSUS_PROTOCOL_BY_RISK",
    "SIGNALS",
    "SIGNAL_WEIGHTS",
    "RISK_FIXTURES",
    "build_swarm_graph",
    "SwarmGraphRunner",
    "SwarmRunResult",
    "SwarmRunTaskResult",
    "SwarmGraphEvent",
    "SwarmGraphEventKind",
    "TopologyEvent",
    "ConsensusEvent",
    "WorkerEvent",
    "HITLEvent",
    "AuditEvent",
    "BudgetEvent",
    "run_deterministic_swarm",
]

del Path, _CANDIDATES, _path
