"""Generate Capability Cards from SwarmGraph IR graphs and nodes.

This module provides functions to convert IRGraph and IRNode instances into
CapabilityCard instances. The conversion is read-only and never mutates the IR.

Design rules:
- One card per IR graph (entity_type: ir_graph)
- One card per IR node (entity_type: ir_node)
- Preserve IR graph hash and node IDs in provenance
- Derive read/write/network/paid/MCP/risk/HITL/audit/replay fields from IR metadata
- Never execute workflows, call tools/models, or make network calls
"""

from __future__ import annotations

from typing import Optional

from ..swarmgraph_ir.models import (
    IRGraph,
    IRNode,
    IRNodeKind,
    IRMcpToolRef,
    IRRisk,
    IRSideEffect,
    SideEffectKind,
)

from .hashing import card_hash
from .models import (
    ApprovalMode,
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
    CostCapability,
    DataAccess,
    DataSensitivity,
    EntityType,
    HitlRequirement,
    McpCapability,
    PermissionRequirement,
    ReplayProfile,
    RiskLevel,
    SideEffectProfile,
    TrustLevel,
    TrustProfile,
)


def _ir_risk_to_card_risk(ir_risk: IRRisk) -> tuple[RiskLevel, list[str], Optional[str]]:
    """Convert IR risk to card risk level, signals, and rationale."""
    level_map = {
        "low": RiskLevel.LOW,
        "medium": RiskLevel.MEDIUM,
        "high": RiskLevel.HIGH,
        "critical": RiskLevel.CRITICAL,
    }
    level = level_map.get(ir_risk.level, RiskLevel.LOW)
    signals = list(ir_risk.signals) if ir_risk.signals else []
    rationale = ir_risk.rationale if ir_risk.rationale else None
    return level, signals, rationale


def _ir_side_effects_to_capabilities(
    side_effects: list[IRSideEffect],
) -> tuple[CapabilitySet, list[SideEffectProfile]]:
    """Convert IR side effects to CapabilitySet flags and SideEffectProfiles."""
    caps = CapabilitySet()
    profiles: list[SideEffectProfile] = []

    for se in side_effects:
        profile = SideEffectProfile(
            kind=se.kind.value if hasattr(se.kind, "value") else str(se.kind),
            target=se.target,
            reversible=False,
            idempotent=True,
            requires_hitl=False,
            requires_audit=False,
            requires_trust=False,
        )

        if se.kind == SideEffectKind.READ:
            caps.can_read = True
        elif se.kind == SideEffectKind.WRITE:
            caps.can_write = True
            profile.requires_trust = True
        elif se.kind == SideEffectKind.NETWORK:
            caps.can_network = True
            profile.requires_trust = True
        elif se.kind == SideEffectKind.PAID_CALL:
            caps.can_make_paid_calls = True
            profile.requires_audit = True
        elif se.kind == SideEffectKind.EXEC:
            caps.can_execute = True
            profile.requires_hitl = True
            profile.requires_trust = True
        elif se.kind == SideEffectKind.SECRET_READ:
            caps.can_read_secrets = True
            profile.requires_trust = True

        if profile.kind != SideEffectKind.NONE.value:
            profiles.append(profile)

    return caps, profiles


def _node_kind_to_capabilities(kind: IRNodeKind) -> CapabilitySet:
    """Derive base capabilities from node kind."""
    caps = CapabilitySet()

    if kind == IRNodeKind.AGENT:
        caps.can_read = True
        caps.can_call_models = True
        caps.can_call_tools = True
    elif kind == IRNodeKind.TOOL:
        caps.can_execute = True
        caps.can_call_tools = True
    elif kind == IRNodeKind.MCP_TOOL:
        caps.can_call_mcp = True
        caps.can_call_tools = True
    elif kind == IRNodeKind.MODEL_CALL:
        caps.can_call_models = True
    elif kind == IRNodeKind.HUMAN_GATE:
        caps.can_request_hitl = True
    elif kind == IRNodeKind.CONSENSUS:
        caps.can_emit_events = True
    elif kind == IRNodeKind.ROUTER:
        caps.can_read = True
        caps.can_emit_events = True
    elif kind == IRNodeKind.FAN_OUT:
        caps.can_read = True
        caps.can_emit_events = True
    elif kind == IRNodeKind.FAN_IN:
        caps.can_read = True
        caps.can_emit_events = True

    return caps


def _derive_trust_profile(node: IRNode, caps: CapabilitySet) -> TrustProfile:
    """Derive trust requirements from node metadata and capabilities."""
    profile = TrustProfile(
        requires_workspace_trust=False,
        requires_tool_approval=False,
        requires_manifest_pin=False,
        requires_secret_scope=False,
        trust_level=TrustLevel.NONE,
        hitl_requirement=HitlRequirement.NONE,
        approval_mode=ApprovalMode.NONE,
    )

    # Check for trust annotation
    if node.trust_annotation:
        profile.requires_workspace_trust = True
        profile.trust_level = TrustLevel.WORKSPACE

    # Check for privileged flag
    if node.privileged:
        profile.trust_level = TrustLevel.PRIVILEGED
        profile.requires_workspace_trust = True

    # Check for HITL gates
    if node.human_gate:
        profile.hitl_requirement = (
            HitlRequirement.REQUIRED if node.human_gate.blocking else HitlRequirement.RECOMMENDED
        )
        profile.approval_mode = ApprovalMode.MANUAL_APPROVAL

    # High-risk capabilities require trust
    if caps.can_write or caps.can_delete or caps.can_execute:
        profile.requires_workspace_trust = True
        if profile.trust_level == TrustLevel.NONE:
            profile.trust_level = TrustLevel.WORKSPACE

    # Secret access requires elevated trust
    if caps.can_read_secrets:
        profile.requires_secret_scope = True
        profile.trust_level = TrustLevel.EXPLICIT

    # Network access requires trust
    if caps.can_network:
        profile.requires_workspace_trust = True

    return profile


def _derive_audit_profile(node: IRNode, caps: CapabilitySet) -> AuditProfile:
    """Derive audit requirements from node metadata and capabilities."""
    profile = AuditProfile(
        audit_required=False,
        audit_level=AuditLevel.NONE,
        audit_event_types=[],
        redact_fields=[],
        receipt_required=False,
    )

    # Check for audit boundary
    if node.audit_boundary:
        profile.audit_required = True
        level_map = {
            "none": AuditLevel.NONE,
            "arc_sha256": AuditLevel.ARC_SHA256,
            "swarmgraph_hmac": AuditLevel.SWARMGRAPH_HMAC,
        }
        profile.audit_level = level_map.get(node.audit_boundary.audit_level, AuditLevel.ARC_SHA256)
        profile.audit_event_types = ["tool_call", "model_call"]

    # Paid calls require audit
    if caps.can_make_paid_calls:
        profile.audit_required = True
        if profile.audit_level == AuditLevel.NONE:
            profile.audit_level = AuditLevel.ARC_SHA256
        profile.audit_event_types.append("paid_call")
        profile.receipt_required = True

    # Sensitive operations require redaction
    if caps.can_read_secrets or caps.can_network:
        profile.redact_fields = ["key", "token", "secret", "password", "credential"]

    # Audit boundary nodes require full audit
    if node.audit_boundary:
        profile.audit_required = True

    return profile


def _derive_replay_profile(node: IRNode) -> ReplayProfile:
    """Derive replay characteristics from node metadata."""
    profile = ReplayProfile(
        replayable=True,
        deterministic=False,
        requires_recorded_inputs=False,
        non_replayable_reasons=[],
    )

    # Check for replay marker
    if node.replay_marker:
        profile.replayable = True
        profile.requires_recorded_inputs = True

    # Model calls may not be deterministic
    if node.model_call:
        profile.deterministic = False
        if not node.replay_marker:
            profile.replayable = False
            profile.non_replayable_reasons.append("model_call_non_deterministic")

    # Side effects make replay non-deterministic
    for se in node.side_effects:
        if se.kind in (SideEffectKind.WRITE, SideEffectKind.EXEC):
            profile.deterministic = False
            if not node.replay_marker:
                profile.replayable = False
                profile.non_replayable_reasons.append(f"side_effect_{se.kind.value}")

    return profile


def _derive_cost_capability(node: IRNode) -> Optional[CostCapability]:
    """Derive cost capability from node budget and model call."""
    cost = CostCapability(paid=False, budget_required=False)

    # Check budget
    if node.budget:
        cost.paid = node.budget.requires_paid_call
        cost.budget_required = node.budget.requires_paid_call
        if node.budget.cost_usd is not None:
            cost.max_cost_usd = node.budget.cost_usd
        if node.budget.tokens is not None:
            cost.max_tokens = node.budget.tokens
        cost.paid_call_gate = node.budget.paid_call_gate

    # Check model call
    if node.model_call:
        mc = node.model_call
        cost.paid = mc.paid
        cost.provider = mc.provider
        if mc.budget:
            cost.budget_required = mc.budget.requires_paid_call
            if mc.budget.cost_usd is not None and cost.max_cost_usd is None:
                cost.max_cost_usd = mc.budget.cost_usd

    if not cost.paid and not cost.budget_required:
        return None

    return cost


def _derive_mcp_capability(node: IRNode) -> Optional[McpCapability]:
    """Derive MCP capability from IRMcpToolRef."""
    if not node.mcp_tool:
        return None

    mcp_ref: IRMcpToolRef = node.mcp_tool

    caps = McpCapability(
        server_id=mcp_ref.server_id,
        tool_name=mcp_ref.tool_name,
        manifest_hash=mcp_ref.manifest_hash,
        pinned=False,  # IRMcpToolRef doesn't have pinned; use manifest_hash for drift detection
        drifted=False,
        approved=mcp_ref.approved,
        blocked=mcp_ref.blocked,
        risk_flags=[],
        risk_level=RiskLevel(mcp_ref.risk_level),
    )

    # Derive risk flags from MCP tool ref
    if mcp_ref.can_write:
        caps.risk_flags.append("can_write")
    if mcp_ref.can_network:
        caps.risk_flags.append("can_network")
    if mcp_ref.can_read_secrets:
        caps.risk_flags.append("can_read_secrets")
    if mcp_ref.accesses_outside_workspace:
        caps.risk_flags.append("accesses_outside_workspace")

    return caps


def _derive_permissions(node: IRNode, caps: CapabilitySet) -> list[PermissionRequirement]:
    """Derive permission requirements from node capabilities."""
    permissions: list[PermissionRequirement] = []

    if caps.can_read:
        permissions.append(
            PermissionRequirement(
                kind="fs.read",
                required=False,
                reason="Read workspace files",
                default_decision="allow",
            )
        )

    if caps.can_write:
        permissions.append(
            PermissionRequirement(
                kind="fs.write",
                required=True,
                reason="Write to workspace",
                default_decision="deny",
            )
        )

    if caps.can_execute:
        permissions.append(
            PermissionRequirement(
                kind="exec.run",
                required=True,
                reason="Execute tool commands",
                default_decision="deny",
            )
        )

    if caps.can_network:
        permissions.append(
            PermissionRequirement(
                kind="net.http",
                required=True,
                reason="Make network requests",
                default_decision="deny",
            )
        )

    if caps.can_read_secrets:
        permissions.append(
            PermissionRequirement(
                kind="secret.read",
                required=True,
                reason="Access secrets/credentials",
                default_decision="deny",
            )
        )

    if caps.can_make_paid_calls:
        permissions.append(
            PermissionRequirement(
                kind="model.paid_call",
                required=True,
                reason="Make paid model API calls",
                default_decision="prompt",
            )
        )

    # Add MCP-specific permissions
    if caps.can_call_mcp and node.mcp_tool:
        permissions.append(
            PermissionRequirement(
                kind=f"mcp.{node.mcp_tool.server_id}.call",
                required=True,
                reason=f"Invoke MCP tool {node.mcp_tool.tool_name}",
                default_decision="prompt",
            )
        )

    return permissions


def _derive_data_access(node: IRNode, caps: Optional[CapabilitySet] = None) -> Optional[DataAccess]:
    """Derive data access profile from node metadata."""
    reads: list[str] = []
    writes: list[str] = []
    deletes: list[str] = []

    # Check for read side effects
    for se in node.side_effects:
        if se.kind == SideEffectKind.READ and se.target:
            reads.append(se.target)
        elif se.kind == SideEffectKind.WRITE and se.target:
            writes.append(se.target)

    # Check for write path
    if node.write_path:
        writes.append(node.write_path)

    if not reads and not writes and not deletes:
        return None

    # Determine sensitivity based on secrets access
    sensitivity = DataSensitivity.PUBLIC
    if node.metadata.get("sensitive_data"):
        sensitivity = DataSensitivity.CONFIDENTIAL

    # Check if secrets are accessed
    can_read_secrets = False
    if caps:
        can_read_secrets = caps.can_read_secrets
    else:
        # Check side effects directly
        can_read_secrets = any(se.kind == SideEffectKind.SECRET_READ for se in node.side_effects)

    return DataAccess(
        reads=reads,
        writes=writes,
        deletes=deletes,
        sensitivity=sensitivity,
        scope="workspace" if not node.metadata.get("outside_workspace") else "system",
        redaction_required=can_read_secrets,
    )


def card_from_ir_node(
    graph: IRGraph,
    node: IRNode,
    *,
    include_graph_provenance: bool = True,
) -> CapabilityCard:
    """Generate a CapabilityCard from an IRNode.

    Args:
        graph: The parent IRGraph containing this node.
        node: The IRNode to convert.
        include_graph_provenance: Include graph-level provenance in the card.

    Returns:
        A CapabilityCard representing the node's capabilities.
    """
    # Derive capabilities from node kind and side effects
    kind_caps = _node_kind_to_capabilities(node.kind)
    se_caps, side_effect_profiles = _ir_side_effects_to_capabilities(node.side_effects)

    # Merge capabilities
    caps = CapabilitySet()
    for field in CapabilitySet.model_fields:
        kind_val = getattr(kind_caps, field, False)
        se_val = getattr(se_caps, field, False)
        setattr(caps, field, kind_val or se_val)

    # Derive risk
    risk_level, risk_signals, risk_rationale = _ir_risk_to_card_risk(node.risk)

    # Derive profiles
    trust = _derive_trust_profile(node, caps)
    audit = _derive_audit_profile(node, caps)
    replay = _derive_replay_profile(node)

    # Derive additional metadata
    mcp = _derive_mcp_capability(node)
    cost = _derive_cost_capability(node)
    permissions = _derive_permissions(node, caps)
    data_access = _derive_data_access(node, caps)

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="ir_node",
        ir_graph_id=graph.id if include_graph_provenance else None,
        ir_graph_hash=graph.graph_hash if include_graph_provenance else None,
        ir_node_id=node.id,
    )

    # Build card
    card = CapabilityCard(
        id=f"ir-node-{graph.id}-{node.id}",
        name=node.label or node.id,
        entity_type=EntityType.IR_NODE,
        description=f"IR node '{node.id}' of type '{node.kind.value}' in graph '{graph.id}'",
        capabilities=caps,
        permissions=permissions,
        data_access=data_access,
        side_effects=side_effect_profiles,
        mcp=mcp,
        cost=cost,
        trust=trust,
        audit=audit,
        replay=replay,
        risk_level=risk_level,
        risk_signals=risk_signals,
        risk_rationale=risk_rationale,
        provenance=provenance,
        metadata={
            "ir_node_kind": node.kind.value,
            "ir_graph_id": graph.id,
            "ir_graph_runtime": graph.runtime,
            "privileged": node.privileged,
        },
        opaque=node.kind == IRNodeKind.UNKNOWN,
        requires_review=node.kind == IRNodeKind.UNKNOWN
        or risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def card_from_ir_graph(graph: IRGraph) -> CapabilityCard:
    """Generate a CapabilityCard from an IRGraph.

    Args:
        graph: The IRGraph to convert.

    Returns:
        A CapabilityCard representing the graph's aggregate capabilities.
    """
    # Aggregate capabilities from all nodes
    caps = CapabilitySet()
    risk_signals: list[str] = []
    high_risk_nodes: list[str] = []
    has_mcp = False
    has_paid = False
    requires_hitl = False

    for node in graph.nodes:
        # Merge node capabilities
        node_caps = _node_kind_to_capabilities(node.kind)
        for field in CapabilitySet.model_fields:
            node_val = getattr(node_caps, field, False)
            existing = getattr(caps, field, False)
            setattr(caps, field, existing or node_val)

        # Aggregate risk signals
        if node.risk.signals:
            risk_signals.extend(node.risk.signals)

        # Track high-risk nodes
        if node.risk.level in ("high", "critical"):
            high_risk_nodes.append(node.id)

        # Check for MCP tools
        if node.mcp_tool:
            has_mcp = True

        # Check for paid calls
        if node.budget and node.budget.requires_paid_call:
            has_paid = True
        if node.model_call and node.model_call.paid:
            has_paid = True

        # Check for HITL gates
        if node.human_gate:
            requires_hitl = True

    # Derive aggregate risk
    risk_level = RiskLevel(graph.risk.level)

    # Derive trust profile
    trust = TrustProfile(
        requires_workspace_trust=bool(high_risk_nodes),
        requires_tool_approval=has_mcp,
        trust_level=TrustLevel.WORKSPACE if high_risk_nodes else TrustLevel.NONE,
        hitl_requirement=HitlRequirement.REQUIRED
        if requires_hitl
        and risk_level
        in (
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        )
        else HitlRequirement.NONE,
    )

    # Derive audit profile
    audit = AuditProfile(
        audit_required=has_paid or bool(high_risk_nodes),
        audit_level=AuditLevel.ARC_SHA256 if has_paid else AuditLevel.NONE,
        audit_event_types=["tool_call", "model_call"] if has_paid else [],
        receipt_required=has_paid,
        redact_fields=["key", "token", "secret"] if has_paid else [],
    )

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="ir_graph",
        ir_graph_id=graph.id,
        ir_graph_hash=graph.graph_hash,
        adapter_id=graph.provenance.adapter_id,
        adapter_name=graph.provenance.runtime,
    )

    # Build card
    card = CapabilityCard(
        id=f"ir-graph-{graph.id}",
        name=graph.name or graph.id,
        entity_type=EntityType.IR_GRAPH,
        description=f"SwarmGraph IR graph '{graph.id}' with {len(graph.nodes)} nodes, runtime: {graph.runtime}",
        capabilities=caps,
        trust=trust,
        audit=audit,
        replay=ReplayProfile(
            replayable=True,
            deterministic=False,
            non_replayable_reasons=["graph_contains_model_calls"] if has_paid else [],
        ),
        risk_level=risk_level,
        risk_signals=risk_signals[:20],  # Limit signals
        provenance=provenance,
        metadata={
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "runtime": graph.runtime,
            "high_risk_nodes": high_risk_nodes,
            "suggested_consensus": graph.consensus.suggested_protocol,
        },
        requires_review=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def cards_from_ir_graph(graph: IRGraph) -> list[CapabilityCard]:
    """Generate CapabilityCards from an IRGraph.

    Creates:
    - One card for the graph (entity_type: ir_graph)
    - One card per node (entity_type: ir_node)

    Args:
        graph: The IRGraph to convert.

    Returns:
        List of CapabilityCards, starting with the graph card followed by node cards.
    """
    cards: list[CapabilityCard] = []

    # Add graph card
    cards.append(card_from_ir_graph(graph))

    # Add node cards
    for node in graph.nodes:
        cards.append(card_from_ir_node(graph, node))

    return cards
