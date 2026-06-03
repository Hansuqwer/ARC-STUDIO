"""Capability Card-aware Policy Linter.

Extends the base policy linter to consume Capability Cards instead of raw
WorkflowInfo metadata. This provides structured, typed capability metadata
for more accurate policy analysis.

Rules implemented:
  C1  card_capability_mismatch — card says can_write but no write permission
  C2  missing_trust_requirement — high-capability card has no trust level
  C3  unapproved_mcp_tool — MCP tool card is blocked or not approved
  C4  drifted_mcp_manifest — MCP card has drifted from pinned manifest
  C5  missing_hitl_for_dangerous — card with dangerous caps requires HITL
  C6  unpaid_paid_call — card can make paid calls but has no budget
  C7  secret_access_without_scope — card can read secrets but no secret scope
  C8  network_without_audit — card can network but audit not required
  C9  replay_disallowed_on_dangerous — dangerous card not replayable
  C10 unknown_entity_review — opaque/unknown entity card requires review

Usage:
    from agent_runtime_cockpit.capabilities.policy import lint_cards
    cards = cards_from_ir_graph(graph)
    report = lint_cards(cards, workspace_root=Path.cwd())
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    AuditLevel,
    CapabilityCard,
    EntityType,
    HitlRequirement,
    RiskLevel,
    TrustLevel,
)
from .registry import CardRegistry


# ─── Output schema ────────────────────────────────────────────────────────────


class CardPolicyIssue(BaseModel):
    """A single policy issue found in a Capability Card."""

    rule: str
    severity: str  # "error" | "warning" | "info"
    card_id: str | None = None
    message: str
    remediation: str
    capability_affected: str | None = None


class CardPolicyReport(BaseModel):
    """Policy report for a set of Capability Cards."""

    workflow_id: str
    workflow_name: str
    card_count: int
    high_risk_cards: int
    issues: list[CardPolicyIssue] = Field(default_factory=list)
    can_run: bool = True  # Set by lint_cards based on errors
    requires_review: bool = False  # Set by lint_cards based on cards

    model_config = ConfigDict(extra="ignore")

    @property
    def ok(self) -> bool:
        """Report is ok if no errors and can_run."""
        return self.can_run and not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[CardPolicyIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[CardPolicyIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def mcp_issues(self) -> list[CardPolicyIssue]:
        return [
            i
            for i in self.issues
            if i.rule.startswith("untrusted_mcp") or i.rule.startswith("drifted_mcp")
        ]

    @property
    def trust_issues(self) -> list[CardPolicyIssue]:
        return [
            i
            for i in self.issues
            if i.rule
            in (
                "missing_trust_requirement",
                "secret_access_without_scope",
                "unpaid_paid_call",
            )
        ]


# ─── Rule implementations ─────────────────────────────────────────────────────


def _c1_capability_mismatch(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for capability/permission mismatches."""
    issues = []
    caps = card.capabilities

    # Write without write permission
    if caps.can_write:
        has_permission = any(p.kind == "fs.write" or p.kind == "exec.run" for p in card.permissions)
        if not has_permission:
            issues.append(
                CardPolicyIssue(
                    rule="card_capability_mismatch",
                    severity="warning",
                    card_id=card.id,
                    message=f"Card '{card.id}' can write but has no write permission.",
                    remediation="Add write permission or remove write capability.",
                    capability_affected="can_write",
                )
            )

    # Execute without exec permission
    if caps.can_execute:
        has_permission = any(
            p.kind.startswith("exec.") or p.kind.startswith("mcp.") for p in card.permissions
        )
        if not has_permission:
            issues.append(
                CardPolicyIssue(
                    rule="card_capability_mismatch",
                    severity="warning",
                    card_id=card.id,
                    message=f"Card '{card.id}' can execute but has no exec permission.",
                    remediation="Add exec permission or remove execute capability.",
                    capability_affected="can_execute",
                )
            )

    return issues


def _c2_missing_trust_requirement(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for missing trust requirements on high-capability cards."""
    issues = []
    caps = card.capabilities

    # Dangerous capabilities require trust
    dangerous_caps = [
        ("can_write", "write"),
        ("can_delete", "delete"),
        ("can_execute", "execute"),
        ("can_network", "network"),
        ("can_read_secrets", "read secrets"),
    ]

    for cap_field, cap_name in dangerous_caps:
        if getattr(caps, cap_field, False):
            trust = card.trust
            if trust.trust_level in (TrustLevel.NONE, TrustLevel.WORKSPACE):
                # Check if trust level is sufficient for the capability
                if cap_name in ("read secrets", "execute") and trust.trust_level == TrustLevel.NONE:
                    issues.append(
                        CardPolicyIssue(
                            rule="missing_trust_requirement",
                            severity="error",
                            card_id=card.id,
                            message=f"Card '{card.id}' can {cap_name} but has no trust requirement.",
                            remediation=f"Set trust.trust_level to 'explicit' or higher for {cap_name} capability.",
                            capability_affected=cap_field,
                        )
                    )
                elif trust.trust_level == TrustLevel.WORKSPACE:
                    issues.append(
                        CardPolicyIssue(
                            rule="missing_trust_requirement",
                            severity="warning",
                            card_id=card.id,
                            message=f"Card '{card.id}' can {cap_name} but only has workspace trust.",
                            remediation=f"Consider elevating trust level for {cap_name} capability.",
                            capability_affected=cap_field,
                        )
                    )

    return issues


def _c3_unapproved_mcp_tool(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for unapproved or blocked MCP tools."""
    issues = []

    if card.mcp:
        mcp = card.mcp

        # Blocked tool
        if mcp.blocked:
            issues.append(
                CardPolicyIssue(
                    rule="untrusted_mcp_tool",
                    severity="error",
                    card_id=card.id,
                    message=f"MCP tool '{mcp.tool_name}' on server '{mcp.server_id}' is blocked.",
                    remediation="Unblock the tool in the MCP registry or remove this capability.",
                    capability_affected="can_call_mcp",
                )
            )

        # Not approved (but not blocked either)
        elif not mcp.approved and mcp.tool_name:
            issues.append(
                CardPolicyIssue(
                    rule="untrusted_mcp_tool",
                    severity="warning",
                    card_id=card.id,
                    message=f"MCP tool '{mcp.tool_name}' on server '{mcp.server_id}' is not approved.",
                    remediation="Approve the tool in the MCP registry.",
                    capability_affected="can_call_mcp",
                )
            )

        # Not pinned
        if not mcp.pinned:
            issues.append(
                CardPolicyIssue(
                    rule="untrusted_mcp_tool",
                    severity="warning",
                    card_id=card.id,
                    message=f"MCP tool '{mcp.tool_name}' has no manifest pin.",
                    remediation="Pin the MCP manifest to track drift.",
                    capability_affected="can_call_mcp",
                )
            )

    return issues


def _c4_drifted_mcp_manifest(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for MCP manifest drift."""
    issues = []

    if card.mcp and card.mcp.drifted:
        issues.append(
            CardPolicyIssue(
                rule="drifted_mcp_manifest",
                severity="error",
                card_id=card.id,
                message=f"MCP manifest for '{card.mcp.server_id}' has drifted from pinned version.",
                remediation="Re-pin the MCP manifest or review the changes.",
                capability_affected="can_call_mcp",
            )
        )

    return issues


def _c5_missing_hitl_for_dangerous(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for missing HITL on dangerous capabilities."""
    issues = []
    caps = card.capabilities

    # Dangerous capabilities that should require HITL
    dangerous_with_hitl = [
        ("can_execute", "execute commands"),
        ("can_delete", "delete data"),
        ("can_read_secrets", "access secrets"),
    ]

    for cap_field, cap_name in dangerous_with_hitl:
        if getattr(caps, cap_field, False):
            trust = card.trust
            if trust.hitl_requirement == HitlRequirement.NONE:
                issues.append(
                    CardPolicyIssue(
                        rule="missing_hitl_for_dangerous",
                        severity="warning",
                        card_id=card.id,
                        message=f"Card '{card.id}' can {cap_name} but has no HITL requirement.",
                        remediation=f"Set trust.hitl_requirement to 'recommended' or 'required' for {cap_name}.",
                        capability_affected=cap_field,
                    )
                )

    return issues


def _c6_unpaid_paid_call(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for paid calls without budget."""
    issues = []

    if card.capabilities.can_make_paid_calls:
        cost = card.cost

        if not cost:
            issues.append(
                CardPolicyIssue(
                    rule="unpaid_paid_call",
                    severity="error",
                    card_id=card.id,
                    message=f"Card '{card.id}' can make paid calls but has no cost metadata.",
                    remediation="Add cost metadata with budget information.",
                    capability_affected="can_make_paid_calls",
                )
            )
        elif cost.paid and not cost.budget_required:
            issues.append(
                CardPolicyIssue(
                    rule="unpaid_paid_call",
                    severity="warning",
                    card_id=card.id,
                    message=f"Card '{card.id}' makes paid calls but doesn't require budget.",
                    remediation="Set cost.budget_required=True for paid calls.",
                    capability_affected="can_make_paid_calls",
                )
            )

    return issues


def _c7_secret_access_without_scope(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for secret access without secret scope."""
    issues = []

    if card.capabilities.can_read_secrets:
        trust = card.trust
        if not trust.requires_secret_scope:
            issues.append(
                CardPolicyIssue(
                    rule="secret_access_without_scope",
                    severity="error",
                    card_id=card.id,
                    message=f"Card '{card.id}' can read secrets but doesn't require secret scope.",
                    remediation="Set trust.requires_secret_scope=True.",
                    capability_affected="can_read_secrets",
                )
            )

    return issues


def _c8_network_without_audit(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for network access without audit."""
    issues = []

    if card.capabilities.can_network:
        audit = card.audit
        if audit.audit_level == AuditLevel.NONE:
            issues.append(
                CardPolicyIssue(
                    rule="network_without_audit",
                    severity="warning",
                    card_id=card.id,
                    message=f"Card '{card.id}' can make network requests but has no audit.",
                    remediation="Set audit.audit_level to 'arc_sha256' or higher for network calls.",
                    capability_affected="can_network",
                )
            )

    return issues


def _c9_replay_disallowed_on_dangerous(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for dangerous non-replayable cards."""
    issues = []

    caps = card.capabilities
    replay = card.replay

    # Dangerous capabilities that should be replayable
    dangerous_non_replayable = [
        ("can_write", "write"),
        ("can_delete", "delete"),
        ("can_execute", "execute"),
    ]

    for cap_field, cap_name in dangerous_non_replayable:
        if getattr(caps, cap_field, False):
            if not replay.replayable and replay.non_replayable_reasons:
                issues.append(
                    CardPolicyIssue(
                        rule="replay_disallowed_on_dangerous",
                        severity="warning",
                        card_id=card.id,
                        message=f"Card '{card.id}' can {cap_name} but is not replayable: {', '.join(replay.non_replayable_reasons)}.",
                        remediation=f"Make {cap_name} capability replayable or add replay marker.",
                        capability_affected=cap_field,
                    )
                )

    return issues


def _c10_unknown_entity_review(card: CapabilityCard) -> list[CardPolicyIssue]:
    """Check for opaque/unknown entity cards requiring review."""
    issues = []

    if card.opaque or card.requires_review:
        issues.append(
            CardPolicyIssue(
                rule="unknown_entity_review",
                severity="warning",
                card_id=card.id,
                message=f"Card '{card.id}' is opaque or requires review (entity: {card.entity_type.value}).",
                remediation="Review and approve this capability card before execution.",
                capability_affected=None,
            )
        )

    return issues


# ─── Public API ───────────────────────────────────────────────────────────────


def lint_cards(
    cards: list[CapabilityCard],
    *,
    workflow_id: str = "unknown",
    workflow_name: str = "Unknown Workflow",
    workspace_root: Path | None = None,
) -> CardPolicyReport:
    """Run all policy rules against a list of CapabilityCards.

    Args:
        cards: List of CapabilityCards to lint.
        workflow_id: ID of the workflow these cards belong to.
        workflow_name: Name of the workflow.
        workspace_root: Optional workspace root for context.

    Returns:
        CardPolicyReport with issues and can_run flag.
    """
    issues: list[CardPolicyIssue] = []

    for card in cards:
        issues += _c1_capability_mismatch(card)
        issues += _c2_missing_trust_requirement(card)
        issues += _c3_unapproved_mcp_tool(card)
        issues += _c4_drifted_mcp_manifest(card)
        issues += _c5_missing_hitl_for_dangerous(card)
        issues += _c6_unpaid_paid_call(card)
        issues += _c7_secret_access_without_scope(card)
        issues += _c8_network_without_audit(card)
        issues += _c9_replay_disallowed_on_dangerous(card)
        issues += _c10_unknown_entity_review(card)

    # Count high-risk cards
    high_risk_cards = sum(1 for c in cards if c.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))

    # Check if any card requires review
    requires_review = any(c.requires_review for c in cards)

    # Determine if workflow can run
    can_run = not any(i.severity == "error" for i in issues)

    return CardPolicyReport(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        card_count=len(cards),
        high_risk_cards=high_risk_cards,
        issues=issues,
        can_run=can_run,
        requires_review=requires_review,
    )


def lint_ir_cards(
    ir_cards: list[CapabilityCard],
    *,
    workspace_root: Path | None = None,
) -> CardPolicyReport:
    """Run policy linting on IR-generated capability cards.

    Extracts workflow metadata from the graph card if available.
    """
    # Find the graph card (if any)
    graph_card = next((c for c in ir_cards if c.entity_type == EntityType.IR_GRAPH), None)

    workflow_id = graph_card.id if graph_card else "unknown"
    workflow_name = graph_card.name if graph_card else "Unknown IR Graph"

    return lint_cards(
        ir_cards,
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        workspace_root=workspace_root,
    )


def lint_registry(
    registry: CardRegistry,
    *,
    entity_type: Optional[str] = None,
    workspace_root: Path | None = None,
) -> list[CardPolicyReport]:
    """Run policy linting on all cards in a registry.

    Returns a list of reports, one per unique workflow/graph.
    """
    cards = registry.list_cards(entity_type=entity_type)

    # Group cards by workflow/graph
    workflows: dict[str, list[CapabilityCard]] = {}
    for card in cards:
        # Extract workflow ID from card ID
        if card.entity_type == EntityType.IR_GRAPH:
            workflow_id = card.id
        elif card.entity_type == EntityType.IR_NODE:
            # Extract graph ID from node ID
            parts = card.id.split("-")
            if len(parts) >= 3:
                workflow_id = f"ir-graph-{parts[2]}"
            else:
                workflow_id = "unknown"
        else:
            workflow_id = card.id

        if workflow_id not in workflows:
            workflows[workflow_id] = []
        workflows[workflow_id].append(card)

    # Generate reports for each workflow
    reports = []
    for workflow_id, workflow_cards in workflows.items():
        # Get workflow name from graph card if available
        graph_card = next((c for c in workflow_cards if c.entity_type == EntityType.IR_GRAPH), None)
        workflow_name = graph_card.name if graph_card else workflow_id

        report = lint_cards(
            workflow_cards,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            workspace_root=workspace_root,
        )
        reports.append(report)

    return reports
