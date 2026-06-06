"""Action Simulator typed models.

All models are pure data containers — no execution, network, or I/O.
Schema version 1; forward-compatible via extra="ignore".
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SIMULATION_SCHEMA_VERSION = 1


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SimulationConfig(_Base):
    assume_all_branches: bool = True  # conservative: all nodes reachable
    include_mcp_registry: bool = True  # read local registry/manifests
    include_eval_recommendations: bool = False
    redact_secrets: bool = True
    workspace: Optional[str] = None
    # MT-2: per-call cost estimate from live CostRates. When set, replaces the
    # hardcoded _PAID_CALL_COST_FLOOR constant in the simulator. Callers can
    # populate this via simulation_cost_per_call(provider_id, model).
    cost_per_paid_call_usd: Optional[float] = None


class SimulatedSideEffect(_Base):
    id: str  # se-<node_id>-<idx>
    node_id: str
    kind: str  # matches SideEffectKind.value
    target: Optional[str] = None
    paid: bool = False
    audit_required: bool = False


class SimulatedToolCall(_Base):
    id: str  # tc-<node_id>-<idx>
    node_id: str
    tool_name: str
    namespace: Optional[str] = None
    is_mcp: bool = False
    server_id: Optional[str] = None
    approved: bool = False
    blocked: bool = False
    risk_level: str = "low"
    would_execute: bool = False  # always False — simulator is not a runtime


class SimulatedGate(_Base):
    id: str  # gate-<node_id>-<idx>
    node_id: str
    kind: Literal["hitl", "trust", "paid_call", "write", "privileged"]
    label: str
    blocking: bool = True
    would_require_approval: bool = True


class SimulatedNode(_Base):
    node_id: str
    label: str
    kind: str
    reachable: bool = True
    risk_level: str = "low"
    side_effects: list[SimulatedSideEffect] = Field(default_factory=list)
    tool_calls: list[SimulatedToolCall] = Field(default_factory=list)
    gates: list[SimulatedGate] = Field(default_factory=list)
    is_opaque: bool = False  # kind=UNKNOWN with no structured metadata
    warnings: list[str] = Field(default_factory=list)


class SimulatedEdge(_Base):
    edge_id: str
    from_node: str
    to_node: str
    conditional: bool = False
    reachable: bool = True


class SimulatedMcp(_Base):
    total_mcp_nodes: int = 0
    unique_servers: list[str] = Field(default_factory=list)
    unpinned_servers: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    approved_tools: list[str] = Field(default_factory=list)


class SimulatedCost(_Base):
    """Advisory only — rough estimates, not billing data."""

    has_paid_calls: bool = False
    estimated_paid_call_count: int = 0
    estimated_cost_floor_usd: float = 0.0
    currency: str = "USD"
    note: str = "advisory estimate only"


class PolicySimulationSummary(_Base):
    can_run: bool = True
    risk_level: str = "low"
    suggested_consensus: Optional[str] = None
    error_count: int = 0
    warning_count: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)


class EvalRecommendationRef(_Base):
    source_file: str
    recommendation_id: str
    category: str
    title: str
    confidence: float
    action: str


class SimulationWarning(_Base):
    id: str  # warn-<idx>
    node_id: Optional[str] = None
    code: str
    message: str


class SimulationSummary(_Base):
    total_nodes: int = 0
    reachable_nodes: int = 0
    opaque_nodes: int = 0
    total_edges: int = 0
    side_effect_count: int = 0
    tool_call_count: int = 0
    mcp_tool_count: int = 0
    gate_count: int = 0
    hitl_gate_count: int = 0
    paid_call_count: int = 0
    warning_count: int = 0


class SimulationReport(_Base):
    schema_version: int = SIMULATION_SCHEMA_VERSION
    graph_id: str
    graph_hash: Optional[str] = None
    generated_at: Optional[str] = None  # excluded from determinism_hash
    config: SimulationConfig
    summary: SimulationSummary = Field(default_factory=SimulationSummary)
    nodes: list[SimulatedNode] = Field(default_factory=list)
    edges: list[SimulatedEdge] = Field(default_factory=list)
    side_effects: list[SimulatedSideEffect] = Field(default_factory=list)
    tool_calls: list[SimulatedToolCall] = Field(default_factory=list)
    mcp: SimulatedMcp = Field(default_factory=SimulatedMcp)
    gates: list[SimulatedGate] = Field(default_factory=list)
    policy: PolicySimulationSummary = Field(default_factory=PolicySimulationSummary)
    cost: SimulatedCost = Field(default_factory=SimulatedCost)
    recommendations: list[EvalRecommendationRef] = Field(default_factory=list)
    warnings: list[SimulationWarning] = Field(default_factory=list)
    determinism_hash: Optional[str] = None  # excluded from its own computation
