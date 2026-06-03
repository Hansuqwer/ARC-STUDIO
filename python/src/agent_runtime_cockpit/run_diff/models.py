"""Run Diff / Time Travel - typed Pydantic models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RUN_DIFF_SCHEMA_VERSION = 1

DiffMode = Literal[
    "ir_vs_ir",
    "run_vs_run",
    "policy_vs_policy",
    "simulation_vs_simulation",
    "simulation_vs_run",
    "capability_vs_capability",
    "flight_vs_flight",
    "mcp_vs_mcp",
]


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class DiffSubjectKind(str, Enum):
    IR_GRAPH = "ir_graph"
    RUN_RECORD = "run_record"
    POLICY_REPORT = "policy_report"
    SIMULATION_REPORT = "simulation_report"
    CAPABILITY_CARD = "capability_card"
    FLIGHT_SEGMENT = "flight_segment"
    MCP_MANIFEST = "mcp_manifest"
    UNKNOWN = "unknown"


class DiffSubject(_Base):
    kind: DiffSubjectKind = DiffSubjectKind.UNKNOWN
    id: str = ""
    path: Optional[str] = None
    hash: Optional[str] = None
    run_id: Optional[str] = None
    graph_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DiffSummary(_Base):
    nodes_added: int = 0
    nodes_removed: int = 0
    nodes_changed: int = 0
    edges_added: int = 0
    edges_removed: int = 0
    edges_changed: int = 0
    events_added: int = 0
    events_removed: int = 0
    events_changed: int = 0
    event_types_added: list[str] = Field(default_factory=list)
    event_types_removed: list[str] = Field(default_factory=list)
    policy_issues_added: int = 0
    policy_issues_removed: int = 0
    policy_blockers_introduced: int = 0
    policy_errors_introduced: int = 0
    risk_increased: bool = False
    risk_decreased: bool = False
    mcp_drift_changed: bool = False
    paid_call_delta: int = 0
    hitl_gate_delta: int = 0
    consensus_changed: bool = False
    hitl_removed: bool = False
    total_changes: int = 0

    @property
    def has_changes(self) -> bool:
        return self.total_changes > 0

    def compute_total(self) -> "DiffSummary":
        self.total_changes = (
            self.nodes_added
            + self.nodes_removed
            + self.nodes_changed
            + self.edges_added
            + self.edges_removed
            + self.edges_changed
            + self.events_added
            + self.events_removed
            + self.events_changed
            + self.policy_issues_added
            + self.policy_issues_removed
        )
        return self


class NodeDiffField(_Base):
    field_name: str
    left_value: Any = None
    right_value: Any = None
    change_type: ChangeType = ChangeType.UNCHANGED


class NodeDiff(_Base):
    node_id: str
    change_type: ChangeType = ChangeType.CHANGED
    changed_fields: list[NodeDiffField] = Field(default_factory=list)
    risk_delta: Optional[str] = None
    policy_delta: Optional[str] = None
    tool_delta: Optional[str] = None
    mcp_delta: Optional[str] = None
    consensus_delta: Optional[str] = None
    hitl_delta: Optional[str] = None
    paid_call_delta: Optional[bool] = None
    audit_delta: Optional[str] = None
    is_semantic_regression: bool = False
    regression_reason: Optional[str] = None


class GraphDiff(_Base):
    nodes_added: list[str] = Field(default_factory=list)
    nodes_removed: list[str] = Field(default_factory=list)
    nodes_changed: list[NodeDiff] = Field(default_factory=list)
    edges_added: list[str] = Field(default_factory=list)
    edges_removed: list[str] = Field(default_factory=list)
    edges_changed: list[dict[str, Any]] = Field(default_factory=list)
    node_count_left: int = 0
    node_count_right: int = 0
    edge_count_left: int = 0
    edge_count_right: int = 0
    risk_level_left: Optional[str] = None
    risk_level_right: Optional[str] = None
    consensus_left: Optional[str] = None
    consensus_right: Optional[str] = None


class EventEntry(_Base):
    event_index: int
    event_type: str
    timestamp: Optional[str] = None
    sequence: Optional[int] = None
    data_keys: list[str] = Field(default_factory=list)
    hash: Optional[str] = None


class EventDiff(_Base):
    events_added: list[EventEntry] = Field(default_factory=list)
    events_removed: list[EventEntry] = Field(default_factory=list)
    events_changed: list[dict[str, Any]] = Field(default_factory=list)
    sequence_alignment: list[dict[str, Any]] = Field(default_factory=list)
    first_event_divergence: Optional[int] = None
    event_count_left: int = 0
    event_count_right: int = 0


class PolicyIssueDiff(_Base):
    rule: str
    left_severity: Optional[str] = None
    right_severity: Optional[str] = None
    node_id: Optional[str] = None
    left_present: bool = False
    right_present: bool = False
    is_regression: bool = False
    regression_type: Optional[str] = None


class PolicyDiff(_Base):
    issues_added: list[PolicyIssueDiff] = Field(default_factory=list)
    issues_removed: list[PolicyIssueDiff] = Field(default_factory=list)
    issues_changed: list[PolicyIssueDiff] = Field(default_factory=list)
    can_run_left: bool = True
    can_run_right: bool = True
    can_run_regression: bool = False
    risk_level_left: Optional[str] = None
    risk_level_right: Optional[str] = None
    risk_regression: bool = False
    suggested_consensus_left: Optional[str] = None
    suggested_consensus_right: Optional[str] = None
    consensus_regression: bool = False
    error_count_left: int = 0
    error_count_right: int = 0
    error_count_delta: int = 0
    warning_count_left: int = 0
    warning_count_right: int = 0
    warning_count_delta: int = 0


class SimulationDiff(_Base):
    summary_changed: bool = False
    reachable_nodes_left: int = 0
    reachable_nodes_right: int = 0
    hitl_gates_left: int = 0
    hitl_gates_right: int = 0
    hitl_gate_delta: int = 0
    paid_calls_left: int = 0
    paid_calls_right: int = 0
    paid_call_delta: int = 0
    mcp_tools_left: int = 0
    mcp_tools_right: int = 0
    gate_count_left: int = 0
    gate_count_right: int = 0
    policy_regression: bool = False
    can_run_left: bool = True
    can_run_right: bool = True
    warnings_added: list[str] = Field(default_factory=list)
    warnings_removed: list[str] = Field(default_factory=list)


class McpManifestDiff(_Base):
    servers_added: list[str] = Field(default_factory=list)
    servers_removed: list[str] = Field(default_factory=list)
    hash_changed: list[dict[str, str]] = Field(default_factory=list)
    approved_tools_delta: int = 0
    blocked_tools_delta: int = 0
    tools_added: list[str] = Field(default_factory=list)
    tools_removed: list[str] = Field(default_factory=list)
    drifted_servers: list[str] = Field(default_factory=list)


class CapabilityDiff(_Base):
    cards_added: list[str] = Field(default_factory=list)
    cards_removed: list[str] = Field(default_factory=list)
    cards_changed: list[dict[str, Any]] = Field(default_factory=list)
    capabilities_added: list[str] = Field(default_factory=list)
    capabilities_removed: list[str] = Field(default_factory=list)
    risk_level_changed: list[dict[str, str]] = Field(default_factory=list)
    mcp_drift_detected: bool = False
    trust_regression: bool = False


class FlightDiff(_Base):
    events_added: int = 0
    events_removed: int = 0
    events_changed: int = 0
    segment_hashes_match: bool = False
    hash_chain_valid: bool = True
    event_types_added: list[str] = Field(default_factory=list)
    event_types_removed: list[str] = Field(default_factory=list)
    first_event_divergence: Optional[int] = None


class CostDiff(_Base):
    has_paid_calls_left: bool = False
    has_paid_calls_right: bool = False
    paid_calls_introduced: bool = False
    estimated_cost_delta_usd: float = 0.0
    estimated_cost_floor_left: float = 0.0
    estimated_cost_floor_right: float = 0.0


class RiskDiff(_Base):
    level_left: Optional[str] = None
    level_right: Optional[str] = None
    level_changed: bool = False
    signals_added: list[str] = Field(default_factory=list)
    signals_removed: list[str] = Field(default_factory=list)
    score_delta: float = 0.0


class FirstDivergence(_Base):
    kind: str = "unknown"
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    event_id: Optional[str] = None
    policy_rule: Optional[str] = None
    sequence: Optional[int] = None
    frame_index: Optional[int] = None
    left_value: Any = None
    right_value: Any = None
    reason: str = ""


class TimelineFrame(_Base):
    frame_id: str
    sequence: int
    timestamp: Optional[str] = None
    subject: str = "run"
    event_type: Optional[str] = None
    node_id: Optional[str] = None
    summary: str = ""
    left_label: Optional[str] = None
    right_label: Optional[str] = None
    change_type: ChangeType = ChangeType.UNCHANGED
    left_value: Optional[dict[str, Any]] = None
    right_value: Optional[dict[str, Any]] = None
    redacted: bool = False
    redacted_fields: list[str] = Field(default_factory=list)


class RunDiffReport(_Base):
    schema_version: int = RUN_DIFF_SCHEMA_VERSION
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    left: DiffSubject = Field(default_factory=DiffSubject)
    right: DiffSubject = Field(default_factory=DiffSubject)
    mode: DiffMode = "run_vs_run"
    summary: DiffSummary = Field(default_factory=DiffSummary)
    first_divergence: Optional[FirstDivergence] = None
    graph_diff: Optional[GraphDiff] = None
    event_diff: Optional[EventDiff] = None
    policy_diff: Optional[PolicyDiff] = None
    simulation_diff: Optional[SimulationDiff] = None
    capability_diff: Optional[CapabilityDiff] = None
    flight_diff: Optional[FlightDiff] = None
    mcp_diff: Optional[McpManifestDiff] = None
    cost_diff: Optional[CostDiff] = None
    risk_diff: Optional[RiskDiff] = None
    timeline: list[TimelineFrame] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    mode_metadata: dict[str, Any] = Field(default_factory=dict)
    diff_hash: Optional[str] = None

    def compute_hash(self) -> str:
        content = {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "left": _subject_for_hash(self.left),
            "right": _subject_for_hash(self.right),
            "summary": self.summary.model_dump(mode="json"),
            "first_divergence": self.first_divergence.model_dump(mode="json")
            if self.first_divergence
            else None,
            "graph_diff": self.graph_diff.model_dump(mode="json") if self.graph_diff else None,
            "event_diff": self.event_diff.model_dump(mode="json") if self.event_diff else None,
            "policy_diff": self.policy_diff.model_dump(mode="json") if self.policy_diff else None,
            "simulation_diff": self.simulation_diff.model_dump(mode="json")
            if self.simulation_diff
            else None,
            "capability_diff": self.capability_diff.model_dump(mode="json")
            if self.capability_diff
            else None,
            "flight_diff": self.flight_diff.model_dump(mode="json") if self.flight_diff else None,
            "mcp_diff": self.mcp_diff.model_dump(mode="json") if self.mcp_diff else None,
            "cost_diff": self.cost_diff.model_dump(mode="json") if self.cost_diff else None,
            "risk_diff": self.risk_diff.model_dump(mode="json") if self.risk_diff else None,
        }
        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def with_hash(self) -> "RunDiffReport":
        return self.model_copy(update={"diff_hash": self.compute_hash()})


def _subject_for_hash(subject: DiffSubject) -> dict[str, Any]:
    return {
        "kind": subject.kind.value,
        "id": subject.id,
        "hash": subject.hash,
        "run_id": subject.run_id,
        "graph_hash": subject.graph_hash,
    }
