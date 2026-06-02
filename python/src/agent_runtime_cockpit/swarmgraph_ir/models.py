"""SwarmGraph Intermediate Representation (IR) — typed models.

A normalization & analysis layer that ingests workflows already exported by ARC
runtime adapters (``RuntimeAdapter.export_workflow() -> list[WorkflowInfo]``) and
re-expresses them as a typed, inspectable, policy-aware graph.

Design rules (see docs/research/SWARMGRAPH_IR_COMPILER_ARCHITECTURE.md):
- This is NOT a runtime engine. Models hold data only; nothing here executes a
  workflow, calls a tool/model, opens a socket, or launches an MCP server.
- The package name is intentionally ``swarmgraph_ir`` (NOT a submodule of
  ``agent_runtime_cockpit.swarmgraph``) so it is not rewritten by the SwarmGraph
  bridge MetaPathFinder.
- Forward-compatible: unknown fields are ignored on load (``extra="ignore"``) so
  newer IR files load in older readers; ``ir_version`` gates migrations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Bump the MAJOR for breaking changes; additive changes stay within a major.
IR_SCHEMA_VERSION = 1

RiskLevelStr = Literal["low", "medium", "high", "critical"]


class IRNodeKind(str, Enum):
    """Normalized node kinds across all source frameworks."""

    AGENT = "agent"
    TOOL = "tool"
    MCP_TOOL = "mcp_tool"
    MODEL_CALL = "model_call"
    HUMAN_GATE = "human_gate"
    CONSENSUS = "consensus"
    ROUTER = "router"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"
    START = "start"
    END = "end"
    UNKNOWN = "unknown"


class SideEffectKind(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    PAID_CALL = "paid_call"
    EXEC = "exec"
    SECRET_READ = "secret_read"


class _Base(BaseModel):
    """Shared config: ignore unknown fields for forward compatibility."""

    model_config = ConfigDict(extra="ignore")


class IRRisk(_Base):
    level: RiskLevelStr = "low"
    score: float = 0.0  # 0.0 .. 1.0
    signals: list[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    source: Literal["sdk", "heuristic", "manual"] = "heuristic"


class IRCapabilityRequirement(_Base):
    capability: str  # e.g. "fs.write", "net.http", "secret.read"
    reason: Optional[str] = None
    optional: bool = False


class IRSideEffect(_Base):
    kind: SideEffectKind
    target: Optional[str] = None  # redacted path/host; never raw secrets
    paid: bool = False
    confidence: float = 1.0


class IRBudget(_Base):
    tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    requires_paid_call: bool = False
    paid_call_gate: bool = False


class IRToolRef(_Base):
    name: str
    namespace: Optional[str] = None
    pinned: bool = False
    capabilities: list[IRCapabilityRequirement] = Field(default_factory=list)


class IRMcpToolRef(_Base):
    server_id: str
    tool_name: str
    manifest_hash: Optional[str] = None  # filled by enrich.attach_mcp_risk
    can_write: bool = False
    can_network: bool = False
    can_read_secrets: bool = False
    accesses_outside_workspace: bool = False
    risk_level: Literal["low", "medium", "high"] = "low"
    approved: bool = False
    blocked: bool = False


class IRModelCall(_Base):
    provider: Optional[str] = None
    model: Optional[str] = None
    paid: bool = False
    budget: Optional[IRBudget] = None


class IRHumanGate(_Base):
    gate_id: str
    blocking: bool = True
    prompt: Optional[str] = None
    trust_required: Optional[int] = None  # ADR-014 trust tier


class IRConsensusHint(_Base):
    protocol: Optional[str] = None
    suggested_protocol: Optional[str] = None
    min_workers: Optional[int] = None
    source: Literal["sdk", "metadata", "default"] = "default"


class IRAuditBoundary(_Base):
    boundary_id: str
    reason: str  # "privileged" | "paid_call" | "hitl" | ...
    audit_level: Literal["none", "arc_sha256", "swarmgraph_hmac"] = "arc_sha256"


class IRReplayMarker(_Base):
    marker_id: str  # deterministic, derived from node id
    node_id: str
    correlation_key: str


class IRAdapterProvenance(_Base):
    adapter_id: str  # e.g. "langgraph"
    runtime: str
    adapter_version: Optional[str] = None
    source_file: Optional[str] = None  # relative/redacted
    exported_via: str = "export_workflow"
    imported_at: Optional[str] = None  # excluded from graph_hash


class IRNode(_Base):
    id: str
    label: str = ""
    kind: IRNodeKind = IRNodeKind.UNKNOWN
    tool: Optional[IRToolRef] = None
    mcp_tool: Optional[IRMcpToolRef] = None
    model_call: Optional[IRModelCall] = None
    human_gate: Optional[IRHumanGate] = None
    consensus: Optional[IRConsensusHint] = None
    risk: IRRisk = Field(default_factory=IRRisk)
    capabilities: list[IRCapabilityRequirement] = Field(default_factory=list)
    side_effects: list[IRSideEffect] = Field(default_factory=list)
    budget: Optional[IRBudget] = None
    audit_boundary: Optional[IRAuditBoundary] = None
    replay_marker: Optional[IRReplayMarker] = None
    trust_annotation: Optional[str] = None  # ADR-014 origin/trust tag
    privileged: bool = False
    write_path: Optional[str] = None  # redacted; relative when in-workspace
    eval_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IREdge(_Base):
    id: str  # "<from>→<to>"
    from_node: str
    to_node: str
    conditional: bool = False
    condition: Optional[str] = None
    label: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IRValidationReport(_Base):
    ok: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0


class IRGraph(_Base):
    ir_version: int = IR_SCHEMA_VERSION
    id: str
    name: str = ""
    runtime: str
    provenance: IRAdapterProvenance
    nodes: list[IRNode] = Field(default_factory=list)
    edges: list[IREdge] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    risk: IRRisk = Field(default_factory=IRRisk)
    consensus: IRConsensusHint = Field(default_factory=IRConsensusHint)
    graph_hash: Optional[str] = None  # filled on emit; excluded from its own input
    compiled_at: Optional[str] = None  # excluded from graph_hash
    metadata: dict[str, Any] = Field(default_factory=dict)
