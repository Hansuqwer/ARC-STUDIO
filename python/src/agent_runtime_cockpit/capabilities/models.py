"""Capability Cards — typed models for runtime capability manifests.

A Capability Card is a deterministic, versioned, hashable metadata document that
describes what every runtime, adapter, workflow, agent, MCP tool, model call, and
SwarmGraph IR node can read, write, call, spend, expose, remember, and execute.

Design rules:
- This is NOT a runtime engine. Models hold data only; nothing here executes a
  workflow, calls a tool/model, opens a socket, or launches an MCP server.
- The package name is intentionally ``capabilities`` (NOT a submodule of
  ``agent_runtime_cockpit.swarmgraph``) so it is not rewritten by the SwarmGraph
  bridge MetaPathFinder.
- Forward-compatible: unknown fields are ignored on load (``extra="ignore"``) so
  newer card files load in older readers; ``schema_version`` gates migrations.
- All capability fields default to False/unknown so that missing data is safe.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# Bump the MAJOR for breaking changes; additive changes stay within a major.
CARD_SCHEMA_VERSION = 1


class EntityType(str, Enum):
    """Normalized entity types that can have Capability Cards."""

    RUNTIME_ADAPTER = "runtime_adapter"
    WORKFLOW = "workflow"
    IR_GRAPH = "ir_graph"
    IR_NODE = "ir_node"
    MCP_SERVER = "mcp_server"
    MCP_TOOL = "mcp_tool"
    NATIVE_TOOL = "native_tool"
    MODEL_PROVIDER = "model_provider"
    MODEL = "model"
    AGENT = "agent"
    MEMORY_STORE = "memory_store"
    SEARCH_INDEX = "search_index"
    EVALUATOR = "evaluator"
    SIMULATOR = "simulator"
    AGENTS_MD = "agents_md"
    SKILL = "skill"
    A2A_AGENT = "a2a_agent"
    UNKNOWN = "unknown"


class TrustLevel(str, Enum):
    """Trust level requirements for an entity."""

    NONE = "none"  # No trust required
    WORKSPACE = "workspace"  # Requires workspace trust marker
    EXPLICIT = "explicit"  # Requires explicit approval
    PRIVILEGED = "privileged"  # Requires privileged/elevated trust


class AuditLevel(str, Enum):
    """Audit level requirements."""

    NONE = "none"  # No audit required
    ARC_SHA256 = "arc_sha256"  # SHA-256 receipt verification
    SWARMGRAPH_HMAC = "swarmgraph_hmac"  # SwarmGraph HMAC verification
    FULL = "full"  # Full audit trail with receipts


class HitlRequirement(str, Enum):
    """Human-in-the-loop requirements."""

    NONE = "none"  # No HITL required
    RECOMMENDED = "recommended"  # HITL recommended but not required
    REQUIRED = "required"  # HITL required before execution
    BLOCKING = "blocking"  # Must pause and await human approval


class ApprovalMode(str, Enum):
    """Approval mode for entities that require explicit approval."""

    AUTO_APPROVED = "auto_approved"  # Auto-approved (trust level sufficient)
    MANUAL_APPROVAL = "manual_approval"  # Requires manual approval
    TOKEN_SCOPED = "token_scoped"  # Approval via scoped token
    NONE = "none"  # No approval required


class RiskLevel(str, Enum):
    """Risk classification levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─── Capability Flags ────────────────────────────────────────────────────────


class CapabilitySet(BaseModel):
    """Boolean flags describing what an entity can do.

    All fields default to False so that missing data is safe (fail-closed).
    """

    model_config = ConfigDict(extra="ignore")

    # Data operations
    can_read: bool = False
    can_write: bool = False
    can_delete: bool = False

    # Execution
    can_execute: bool = False
    can_run_background: bool = False

    # Network
    can_network: bool = False

    # Tool invocations
    can_call_tools: bool = False
    can_call_mcp: bool = False
    can_call_models: bool = False

    # Secrets and sensitive data
    can_read_secrets: bool = False
    can_access_outside_workspace: bool = False

    # Paid calls
    can_make_paid_calls: bool = False

    # Memory and persistence
    can_persist_memory: bool = False

    # Events and side effects
    can_emit_events: bool = False
    can_emit_audit: bool = False

    # HITL
    can_request_hitl: bool = False

    # Replay
    can_replay: bool = False


# ─── Data Access ─────────────────────────────────────────────────────────────


class DataSensitivity(str, Enum):
    """Data sensitivity classification."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataAccess(BaseModel):
    """Describes what data an entity reads, writes, or deletes."""

    model_config = ConfigDict(extra="ignore")

    reads: list[str] = Field(default_factory=list)  # e.g. ["workspace://*.py", "env://API_KEY"]
    writes: list[str] = Field(default_factory=list)  # e.g. ["workspace://output/", "file://*.json"]
    deletes: list[str] = Field(default_factory=list)  # e.g. ["file://temp/*"]

    sensitivity: DataSensitivity = DataSensitivity.PUBLIC
    scope: str = "workspace"  # "workspace", "system", "network", "global"
    redaction_required: bool = False


# ─── Side Effects ─────────────────────────────────────────────────────────────


class SideEffectProfile(BaseModel):
    """Profile of side effects produced by an entity."""

    model_config = ConfigDict(extra="ignore")

    kind: str = "none"  # "none", "read", "write", "network", "paid_call", "exec", "secret_read"
    target: Optional[str] = None  # Redacted path/host; never raw secrets
    reversible: bool = False
    idempotent: bool = True
    requires_hitl: bool = False
    requires_audit: bool = False
    requires_trust: bool = False


# ─── Permission Requirements ──────────────────────────────────────────────────


class PermissionRequirement(BaseModel):
    """Describes a permission requirement for an entity."""

    model_config = ConfigDict(extra="ignore")

    kind: str  # e.g. "fs.write", "net.http", "secret.read", "model.paid_call"
    required: bool = True
    reason: Optional[str] = None
    approval_mode: ApprovalMode = ApprovalMode.NONE
    scope: str = "workspace"  # "workspace", "system", "network", "global"
    default_decision: str = "deny"  # "allow", "deny", "prompt"


# ─── MCP Capability ───────────────────────────────────────────────────────────


class McpCapability(BaseModel):
    """MCP-specific capability metadata."""

    model_config = ConfigDict(extra="ignore")

    server_id: str
    tool_name: Optional[str] = None  # None means server-level capability

    manifest_hash: Optional[str] = None
    pinned: bool = False
    drifted: bool = False

    approved: bool = False
    blocked: bool = False

    risk_flags: list[str] = Field(default_factory=list)  # e.g. ["can_write", "can_network"]
    risk_level: RiskLevel = RiskLevel.LOW

    # Legacy MCP registry fields
    approved_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)


# ─── Cost Capability ──────────────────────────────────────────────────────────


class CostCapability(BaseModel):
    """Cost and budget capability metadata."""

    model_config = ConfigDict(extra="ignore")

    paid: bool = False
    budget_required: bool = False
    max_cost_usd: Optional[float] = None
    max_tokens: Optional[int] = None
    provider: Optional[str] = None
    latency_ms_budget: Optional[int] = None
    paid_call_gate: bool = False


# ─── Trust Profile ────────────────────────────────────────────────────────────


class TrustProfile(BaseModel):
    """Trust requirements for an entity."""

    model_config = ConfigDict(extra="ignore")

    requires_workspace_trust: bool = False
    requires_tool_approval: bool = False
    requires_manifest_pin: bool = False
    requires_secret_scope: bool = False

    trust_level: TrustLevel = TrustLevel.NONE

    hitl_requirement: HitlRequirement = HitlRequirement.NONE
    approval_mode: ApprovalMode = ApprovalMode.NONE


# ─── Audit Profile ────────────────────────────────────────────────────────────


class AuditProfile(BaseModel):
    """Audit requirements for an entity."""

    model_config = ConfigDict(extra="ignore")

    audit_required: bool = False
    audit_level: AuditLevel = AuditLevel.NONE
    audit_event_types: list[str] = Field(default_factory=list)  # e.g. ["tool_call", "model_call"]
    redact_fields: list[str] = Field(default_factory=list)  # e.g. ["key", "token", "secret"]
    receipt_required: bool = False


# ─── Replay Profile ───────────────────────────────────────────────────────────


class ReplayProfile(BaseModel):
    """Replay and determinism metadata for an entity."""

    model_config = ConfigDict(extra="ignore")

    replayable: bool = True
    deterministic: bool = False
    requires_recorded_inputs: bool = False

    non_replayable_reasons: list[str] = Field(default_factory=list)


# ─── Provenance ───────────────────────────────────────────────────────────────


class CapabilityProvenance(BaseModel):
    """Source and provenance information for a Capability Card."""

    model_config = ConfigDict(extra="ignore")

    source_type: str = (
        "manual"  # "ir_graph", "ir_node", "mcp_server", "mcp_tool", "adapter", "manual"
    )
    source_file: Optional[str] = None  # Redacted/relative path

    # IR-specific
    ir_graph_id: Optional[str] = None
    ir_graph_hash: Optional[str] = None
    ir_node_id: Optional[str] = None

    # MCP-specific
    mcp_server_id: Optional[str] = None
    mcp_manifest_hash: Optional[str] = None

    # Adapter-specific
    adapter_id: Optional[str] = None
    adapter_name: Optional[str] = None

    # General
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Main Capability Card ─────────────────────────────────────────────────────


class CapabilityCard(BaseModel):
    """Canonical typed metadata document for all executable or inspectable entities.

    A Capability Card answers:
    - What can this thing do?
    - What data can it read/write/delete?
    - Can it call the network?
    - Can it call paid models?
    - Can it access secrets?
    - Can it invoke MCP tools?
    - Can it modify files?
    - Can it run shell commands?
    - Can it run outside the workspace?
    - Does it require HITL?
    - Does it require workspace trust?
    - Is it approved, blocked, pinned, or drifted?
    - Is it replayable?
    - Is it auditable?
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: int = CARD_SCHEMA_VERSION

    # Identity
    id: str  # Deterministic, unique identifier
    name: str
    entity_type: EntityType = EntityType.UNKNOWN
    version: str = "1.0.0"

    # Description
    description: str = ""

    # Capability flags (boolean summary)
    capabilities: CapabilitySet = Field(default_factory=CapabilitySet)

    # Permission requirements
    permissions: list[PermissionRequirement] = Field(default_factory=list)

    # Data access
    data_access: Optional[DataAccess] = None

    # Side effects
    side_effects: list[SideEffectProfile] = Field(default_factory=list)

    # MCP capability (if MCP-related)
    mcp: Optional[McpCapability] = None

    # Cost and budget
    cost: Optional[CostCapability] = None

    # Trust requirements
    trust: TrustProfile = Field(default_factory=TrustProfile)

    # Audit requirements
    audit: AuditProfile = Field(default_factory=AuditProfile)

    # Replay profile
    replay: ReplayProfile = Field(default_factory=ReplayProfile)

    # Risk assessment
    risk_level: RiskLevel = RiskLevel.LOW
    risk_signals: list[str] = Field(default_factory=list)
    risk_rationale: Optional[str] = None

    # Provenance
    provenance: CapabilityProvenance = Field(default_factory=CapabilityProvenance)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Stable hash (computed, not included in hash input)
    card_hash: Optional[str] = None

    # Opaque/unknown flag for entities we can't fully inspect
    opaque: bool = False
    requires_review: bool = False


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "CARD_SCHEMA_VERSION",
    "EntityType",
    "TrustLevel",
    "AuditLevel",
    "HitlRequirement",
    "ApprovalMode",
    "RiskLevel",
    "DataSensitivity",
    "CapabilitySet",
    "DataAccess",
    "SideEffectProfile",
    "PermissionRequirement",
    "McpCapability",
    "CostCapability",
    "TrustProfile",
    "AuditProfile",
    "ReplayProfile",
    "CapabilityProvenance",
    "CapabilityCard",
]
