"""Generate Capability Cards from local MCP registry and manifests.

This module provides functions to convert MCP server records, tool manifests,
and registry entries into CapabilityCard instances.

Design rules:
- One card per MCP server (entity_type: mcp_server)
- One card per MCP tool (entity_type: mcp_tool)
- Use existing risk classification from mcp/manifests.py
- Include manifest_hash for drift detection
- Include approved/blocked state from mcp/registry.py
- Never start MCP servers or make network calls
- Read only from local registry files
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..mcp.manifests import ManifestStore, McpServerManifest, McpToolRisk
from ..mcp.registry import McpRegistryStore, McpServerRecord

from .hashing import card_hash
from .models import (
    ApprovalMode,
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
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


def _tool_risk_to_capabilities(risk: McpToolRisk) -> tuple[CapabilitySet, list[str]]:
    """Convert MCP tool risk classification to CapabilitySet flags."""
    caps = CapabilitySet()

    risk_flags: list[str] = []

    if risk.can_write:
        caps.can_write = True
        risk_flags.append("can_write")
    if risk.can_network:
        caps.can_network = True
        risk_flags.append("can_network")
    if risk.can_read_secrets:
        caps.can_read_secrets = True
        risk_flags.append("can_read_secrets")
    if risk.accesses_outside_workspace:
        caps.can_access_outside_workspace = True
        risk_flags.append("accesses_outside_workspace")

    # MCP tools can call other tools via MCP
    caps.can_call_mcp = True

    return caps, risk_flags


def card_from_mcp_server(
    server_record: McpServerRecord,
    manifest: Optional[McpServerManifest] = None,
) -> CapabilityCard:
    """Generate a CapabilityCard from an MCP server record.

    Args:
        server_record: The MCP server record from the registry.
        manifest: Optional manifest for tool inventory.

    Returns:
        A CapabilityCard representing the server's capabilities.
    """
    # Aggregate capabilities from all tools
    caps = CapabilitySet()
    risk_flags: list[str] = []
    high_risk_tools: list[str] = []
    total_tools = 0

    if manifest:
        for tool_risk in manifest.tool_risks:
            total_tools += 1
            tool_caps, tool_flags = _tool_risk_to_capabilities(tool_risk)

            # Merge capabilities
            for field in caps.model_fields:
                val = getattr(tool_caps, field, False)
                existing = getattr(caps, field, False)
                setattr(caps, field, existing or val)

            risk_flags.extend(tool_flags)

            if tool_risk.risk_level == "high":
                high_risk_tools.append(tool_risk.tool_name)

    # Determine risk level
    risk_level = RiskLevel.LOW
    if any(f in risk_flags for f in ["can_write", "can_read_secrets"]):
        risk_level = RiskLevel.HIGH
    elif any(f in risk_flags for f in ["can_network", "accesses_outside_workspace"]):
        risk_level = RiskLevel.MEDIUM

    # Derive trust profile
    trust = TrustProfile(
        requires_workspace_trust=bool(high_risk_tools),
        requires_manifest_pin=manifest is not None,
        trust_level=TrustLevel.WORKSPACE if high_risk_tools else TrustLevel.NONE,
        hitl_requirement=HitlRequirement.RECOMMENDED if high_risk_tools else HitlRequirement.NONE,
        approval_mode=ApprovalMode.MANUAL_APPROVAL if high_risk_tools else ApprovalMode.NONE,
    )

    # Derive audit profile
    audit = AuditProfile(
        audit_required=bool(high_risk_tools),
        audit_level=AuditLevel.ARC_SHA256 if high_risk_tools else AuditLevel.NONE,
        audit_event_types=["mcp_tool_call"] if high_risk_tools else [],
        redact_fields=["key", "token", "secret"] if "can_read_secrets" in risk_flags else [],
        receipt_required=bool(high_risk_tools),
    )

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="mcp_server",
        mcp_server_id=server_record.server_id,
        mcp_manifest_hash=manifest.manifest_hash if manifest else server_record.manifest_hash,
    )

    # Build MCP capability
    mcp = McpCapability(
        server_id=server_record.server_id,
        pinned=manifest is not None,
        drifted=False,
        approved=len(server_record.approved_tools) > 0,
        blocked=False,
        risk_flags=risk_flags,
        risk_level=risk_level,
        approved_tools=list(server_record.approved_tools),
        blocked_tools=list(server_record.blocked_tools),
    )

    # Build permissions
    permissions: list[PermissionRequirement] = []
    if caps.can_network:
        permissions.append(
            PermissionRequirement(
                kind=f"mcp.{server_record.server_id}.network",
                required=True,
                reason="MCP server can make network requests",
                default_decision="deny",
            )
        )
    if caps.can_write:
        permissions.append(
            PermissionRequirement(
                kind=f"mcp.{server_record.server_id}.write",
                required=True,
                reason="MCP server can write data",
                default_decision="deny",
            )
        )

    # Build card
    card = CapabilityCard(
        id=f"mcp-server-{server_record.server_id}",
        name=server_record.server_id,
        entity_type=EntityType.MCP_SERVER,
        description=f"MCP server '{server_record.server_id}' with {total_tools} tools, transport: {server_record.transport}",
        capabilities=caps,
        permissions=permissions,
        mcp=mcp,
        trust=trust,
        audit=audit,
        replay=ReplayProfile(
            replayable=True,
            deterministic=False,
            non_replayable_reasons=["mcp_tool_side_effects"] if high_risk_tools else [],
        ),
        risk_level=risk_level,
        risk_signals=[f"tool:{t}" for t in high_risk_tools[:10]],
        provenance=provenance,
        metadata={
            "transport": server_record.transport,
            "tool_count": total_tools,
            "high_risk_tools": high_risk_tools,
            "approved_tool_count": len(server_record.approved_tools),
            "blocked_tool_count": len(server_record.blocked_tools),
            "notes": server_record.notes,
        },
        requires_review=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def card_from_mcp_tool(
    server_id: str,
    tool_name: str,
    tool_risk: McpToolRisk,
    server_record: Optional[McpServerRecord] = None,
    manifest_hash: Optional[str] = None,
) -> CapabilityCard:
    """Generate a CapabilityCard from an MCP tool.

    Args:
        server_id: The MCP server ID.
        tool_name: The tool name.
        tool_risk: The tool risk classification.
        server_record: Optional server record for approval state.
        manifest_hash: Optional manifest hash for drift detection.

    Returns:
        A CapabilityCard representing the tool's capabilities.
    """
    caps, risk_flags = _tool_risk_to_capabilities(tool_risk)

    # Determine risk level
    risk_level_map = {"low": RiskLevel.LOW, "medium": RiskLevel.MEDIUM, "high": RiskLevel.HIGH}
    risk_level = risk_level_map.get(tool_risk.risk_level, RiskLevel.LOW)

    # Check approval/block status
    is_approved = False
    is_blocked = False
    if server_record:
        is_approved = tool_name in server_record.approved_tools
        is_blocked = tool_name in server_record.blocked_tools

    # Derive trust profile
    trust = TrustProfile(
        requires_workspace_trust=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
        requires_manifest_pin=True,
        trust_level=TrustLevel.WORKSPACE
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        else TrustLevel.NONE,
        hitl_requirement=HitlRequirement.RECOMMENDED
        if risk_level == RiskLevel.HIGH
        else HitlRequirement.NONE,
        approval_mode=ApprovalMode.MANUAL_APPROVAL if is_blocked else ApprovalMode.AUTO_APPROVED,
    )

    # Derive audit profile
    audit = AuditProfile(
        audit_required=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
        audit_level=AuditLevel.ARC_SHA256
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        else AuditLevel.NONE,
        audit_event_types=["mcp_tool_call"],
        redact_fields=["key", "token", "secret"] if "can_read_secrets" in risk_flags else [],
        receipt_required=risk_level == RiskLevel.HIGH,
    )

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="mcp_tool",
        mcp_server_id=server_id,
        mcp_manifest_hash=manifest_hash,
    )

    # Build MCP capability
    mcp = McpCapability(
        server_id=server_id,
        tool_name=tool_name,
        manifest_hash=manifest_hash,
        pinned=manifest_hash is not None,
        drifted=False,
        approved=is_approved,
        blocked=is_blocked,
        risk_flags=risk_flags,
        risk_level=risk_level,
    )

    # Build side effects
    side_effects: list[SideEffectProfile] = []
    if tool_risk.can_write:
        side_effects.append(
            SideEffectProfile(kind="write", requires_trust=True, requires_audit=True)
        )
    if tool_risk.can_network:
        side_effects.append(SideEffectProfile(kind="network", requires_trust=True))
    if tool_risk.can_read_secrets:
        side_effects.append(SideEffectProfile(kind="secret_read", requires_trust=True))

    # Build permissions
    permissions: list[PermissionRequirement] = [
        PermissionRequirement(
            kind=f"mcp.{server_id}.{tool_name}",
            required=True,
            reason=f"Invoke MCP tool {tool_name}",
            approval_mode=ApprovalMode.MANUAL_APPROVAL
            if is_blocked
            else ApprovalMode.AUTO_APPROVED,
            default_decision="deny" if is_blocked else "allow",
        )
    ]

    if tool_risk.can_network:
        permissions.append(
            PermissionRequirement(
                kind="net.http",
                required=True,
                reason="Tool makes network requests",
                default_decision="deny",
            )
        )

    # Build card
    card = CapabilityCard(
        id=f"mcp-tool-{server_id}-{tool_name}",
        name=tool_name,
        entity_type=EntityType.MCP_TOOL,
        description=f"MCP tool '{tool_name}' on server '{server_id}'",
        capabilities=caps,
        permissions=permissions,
        side_effects=side_effects,
        mcp=mcp,
        trust=trust,
        audit=audit,
        replay=ReplayProfile(
            replayable=True,
            deterministic=False,
            non_replayable_reasons=["tool_side_effects"] if side_effects else [],
        ),
        risk_level=risk_level,
        risk_signals=risk_flags,
        provenance=provenance,
        metadata={
            "server_id": server_id,
            "tool_name": tool_name,
            "is_approved": is_approved,
            "is_blocked": is_blocked,
        },
        requires_review=is_blocked or risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def cards_from_mcp_registry(workspace: Optional[Path] = None) -> list[CapabilityCard]:
    """Generate CapabilityCards from the local MCP registry.

    Creates:
    - One card per registered MCP server
    - One card per tool in the manifest (if available)

    Args:
        workspace: Workspace root for local registry storage.

    Returns:
        List of CapabilityCards for all MCP servers and tools.
    """
    cards: list[CapabilityCard] = []

    # Load registry
    registry = McpRegistryStore()

    # Load manifest store if workspace provided
    manifest_store = ManifestStore(workspace=workspace) if workspace else None

    # Get all server records
    for server_record in registry.list_servers():
        # Load manifest
        manifest = manifest_store.load(server_record.server_id) if manifest_store else None

        # Check for drift
        if manifest:
            drift_report = (
                manifest_store.check_drift(server_record.server_id, [])
                if manifest_store
                else {"drifted": False}
            )
            is_drifted = drift_report.get("drifted", False)
        else:
            is_drifted = False

        # Create server card
        server_card = card_from_mcp_server(server_record, manifest)
        if is_drifted:
            server_card.mcp.drifted = True  # type: ignore
            server_card.requires_review = True
            server_card.risk_signals.append("manifest_drift_detected")

        # Recompute hash after drift update
        server_card.card_hash = card_hash(server_card)

        cards.append(server_card)

        # Create tool cards
        if manifest:
            for tool_risk in manifest.tool_risks:
                tool_card = card_from_mcp_tool(
                    server_id=server_record.server_id,
                    tool_name=tool_risk.tool_name,
                    tool_risk=tool_risk,
                    server_record=server_record,
                    manifest_hash=manifest.manifest_hash,
                )

                # Check for drift on tool card too
                if is_drifted:
                    tool_card.mcp.drifted = True  # type: ignore
                    tool_card.requires_review = True
                    tool_card.card_hash = card_hash(tool_card)

                cards.append(tool_card)

    return cards


def cards_from_mcp_tools(
    server_id: str,
    tools: list[dict[str, Any]],
    manifest_hash: Optional[str] = None,
) -> list[CapabilityCard]:
    """Generate CapabilityCards from a list of MCP tools.

    Args:
        server_id: The MCP server ID.
        tools: List of tool definitions (as returned by MCP inspection).
        manifest_hash: Optional manifest hash for drift detection.

    Returns:
        List of CapabilityCards for all tools.
    """
    cards: list[CapabilityCard] = []

    for tool in tools:
        tool_name = tool.get("name", "")
        if not tool_name:
            continue

        # Create tool risk from metadata
        tool_risk = McpToolRisk.from_tool_meta(tool_name, tool)

        # Create tool card
        tool_card = card_from_mcp_tool(
            server_id=server_id,
            tool_name=tool_name,
            tool_risk=tool_risk,
            manifest_hash=manifest_hash,
        )

        cards.append(tool_card)

    return cards
