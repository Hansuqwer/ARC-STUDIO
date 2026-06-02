"""Workflow-level policy linter.

Scores a workflow against 8 deterministic rules and returns a structured
PolicyReport before execution starts.  Read-only; never modifies state.

Rules implemented:
  R1  missing_hitl         — no HITL node on a high-risk branch
  R2  weak_consensus       — high-risk workflow uses default/weak consensus
  R3  paid_call_unguarded  — network/install nodes without explicit paid gate
  R4  untrusted_mcp_tool   — MCP tool node without manifest pin
  R5  write_outside_workspace — write node targets path outside workspace
  R6  privileged_node      — privileged node type without trust annotation
  R7  no_consensus_node    — multi-worker graph with no consensus node
  R8  unbounded_fan_out    — fan-out > 10 without an aggregation node

Usage:
    from agent_runtime_cockpit.swarmgraph.policy_linter import lint_workflow
    report = lint_workflow(workflow_info, workspace_root=Path.cwd())
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..protocol.schemas import NodeType, WorkflowInfo


# ─── Output schema ────────────────────────────────────────────────────────────


class PolicyIssue(BaseModel):
    rule: str
    severity: str  # "error" | "warning" | "info"
    node_id: str | None = None
    message: str
    remediation: str


class PolicyReport(BaseModel):
    workflow_id: str
    workflow_name: str
    runtime: str
    risk_level: str  # "low" | "medium" | "high" | "critical"
    suggested_consensus: str | None = None
    issues: list[PolicyIssue] = []
    can_run: bool = True  # False if any error-severity issue present

    @property
    def errors(self) -> list[PolicyIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[PolicyIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

_HITL_NODE_TYPES = {NodeType.ROUTER}  # nodes labelled hitl/approval match by label
_NETWORK_NODE_TYPES = {NodeType.TOOL}
_WRITE_NODE_TYPES = {NodeType.TOOL, NodeType.UNKNOWN}
_CONSENSUS_LABELS = {"consensus", "vote", "majority", "quorum", "bft", "raft", "judge"}
_HITL_LABELS = {"hitl", "approval", "human", "review"}

_WEAK_CONSENSUS_PROTOCOLS = {"majority", "default", ""}


def _node_label(node: Any) -> str:
    return (node.label or "").lower()


def _node_is_consensus(node: Any) -> bool:
    lbl = _node_label(node)
    return any(kw in lbl for kw in _CONSENSUS_LABELS)


def _node_is_hitl(node: Any) -> bool:
    lbl = _node_label(node)
    return any(kw in lbl for kw in _HITL_LABELS)


def _node_is_mcp(node: Any) -> bool:
    return "mcp" in _node_label(node) or node.metadata.get("is_mcp", False)


def _node_has_manifest_pin(node: Any) -> bool:
    return bool(node.metadata.get("mcp_manifest_hash") or node.metadata.get("manifest_pin"))


def _outgoing_edges(node_id: str, workflow: WorkflowInfo) -> list[Any]:
    return [e for e in workflow.edges if e.from_node == node_id]


# ─── Rule implementations ─────────────────────────────────────────────────────


def _r1_missing_hitl(wf: WorkflowInfo, risk_level: str) -> list[PolicyIssue]:
    if risk_level not in ("high", "critical"):
        return []
    has_hitl = any(_node_is_hitl(n) for n in wf.nodes)
    if not has_hitl:
        return [
            PolicyIssue(
                rule="missing_hitl",
                severity="error",
                message=f"Workflow risk={risk_level} but no HITL/approval node found.",
                remediation="Add a HITL or approval node before high-risk write/tool branches.",
            )
        ]
    return []


def _r2_weak_consensus(
    wf: WorkflowInfo, risk_level: str, suggested: str | None
) -> list[PolicyIssue]:
    if risk_level not in ("high", "critical"):
        return []
    consensus_nodes = [n for n in wf.nodes if _node_is_consensus(n)]
    for n in consensus_nodes:
        protocol = (n.metadata.get("consensus_protocol") or "").lower()
        if protocol in _WEAK_CONSENSUS_PROTOCOLS and suggested:
            return [
                PolicyIssue(
                    rule="weak_consensus",
                    severity="warning",
                    node_id=n.id,
                    message=f"Consensus node uses weak protocol '{protocol}' for risk={risk_level}.",
                    remediation=f"Switch to '{suggested}' (recommended for this risk level).",
                )
            ]
    return []


def _r3_paid_call_unguarded(wf: WorkflowInfo) -> list[PolicyIssue]:
    issues = []
    for n in wf.nodes:
        if n.type == NodeType.TOOL and n.metadata.get("requires_paid_call"):
            if not n.metadata.get("paid_call_gate"):
                issues.append(
                    PolicyIssue(
                        rule="paid_call_unguarded",
                        severity="warning",
                        node_id=n.id,
                        message=f"Node '{n.label}' requires a paid call but has no explicit paid-call gate.",
                        remediation="Set 'paid_call_gate: true' on this node or run with --allow-paid-calls.",
                    )
                )
    return issues


def _r4_untrusted_mcp_tool(wf: WorkflowInfo) -> list[PolicyIssue]:
    issues = []
    for n in wf.nodes:
        if _node_is_mcp(n) and not _node_has_manifest_pin(n):
            issues.append(
                PolicyIssue(
                    rule="untrusted_mcp_tool",
                    severity="warning",
                    node_id=n.id,
                    message=f"MCP tool node '{n.label}' has no manifest pin.",
                    remediation="Run 'arc mcp pin <server-id>' to record the manifest hash for this tool.",
                )
            )
    return issues


def _r5_write_outside_workspace(wf: WorkflowInfo, workspace_root: Path) -> list[PolicyIssue]:
    issues = []
    for n in wf.nodes:
        write_path = n.metadata.get("write_path")
        if write_path:
            candidate = Path(write_path).expanduser()
            if candidate.is_absolute():
                try:
                    candidate.resolve(strict=False).relative_to(workspace_root.resolve())
                except ValueError:
                    issues.append(
                        PolicyIssue(
                            rule="write_outside_workspace",
                            severity="error",
                            node_id=n.id,
                            message=f"Node '{n.label}' writes to '{write_path}' outside workspace.",
                            remediation="Confine writes to within the trusted workspace root.",
                        )
                    )
    return issues


def _r6_privileged_node(wf: WorkflowInfo) -> list[PolicyIssue]:
    issues = []
    for n in wf.nodes:
        if n.metadata.get("privileged") and not n.metadata.get("trust_annotation"):
            issues.append(
                PolicyIssue(
                    rule="privileged_node",
                    severity="error",
                    node_id=n.id,
                    message=f"Node '{n.label}' is marked privileged but has no trust annotation.",
                    remediation="Add 'trust_annotation' to this node or remove the privileged flag.",
                )
            )
    return issues


def _r7_no_consensus_node(wf: WorkflowInfo) -> list[PolicyIssue]:
    worker_count = wf.metadata.get("num_workers", 0)
    if worker_count <= 1:
        return []
    has_consensus = any(_node_is_consensus(n) for n in wf.nodes)
    if not has_consensus:
        return [
            PolicyIssue(
                rule="no_consensus_node",
                severity="warning",
                message=f"Workflow has {worker_count} workers but no consensus node.",
                remediation="Add a consensus node or set num_workers=1 for single-worker execution.",
            )
        ]
    return []


def _r8_unbounded_fan_out(wf: WorkflowInfo) -> list[PolicyIssue]:
    issues = []
    FAN_OUT_LIMIT = 10
    for n in wf.nodes:
        outs = len(_outgoing_edges(n.id, wf))
        if outs > FAN_OUT_LIMIT:
            has_agg = any(
                _node_is_consensus(wf_n) or "aggregat" in _node_label(wf_n)
                for edge in _outgoing_edges(n.id, wf)
                for wf_n in wf.nodes
                if wf_n.id == edge.to_node
            )
            if not has_agg:
                issues.append(
                    PolicyIssue(
                        rule="unbounded_fan_out",
                        severity="warning",
                        node_id=n.id,
                        message=f"Node '{n.label}' fans out to {outs} children with no aggregation.",
                        remediation="Add a consensus or aggregation node downstream.",
                    )
                )
    return issues


# ─── Public API ───────────────────────────────────────────────────────────────


def lint_workflow(
    workflow: WorkflowInfo,
    workspace_root: Path | None = None,
) -> PolicyReport:
    """Run all policy rules against a WorkflowInfo and return a PolicyReport.

    Args:
        workflow: The WorkflowInfo to lint.
        workspace_root: Confine write-path checks to this directory (default: cwd).

    Returns:
        PolicyReport with issues, risk level, suggested consensus, and can_run flag.
    """
    from swarmgraph import assess_prompt_risk, select_consensus_protocol

    ws = (workspace_root or Path.cwd()).resolve()

    # Derive risk from workflow name/description heuristic + metadata
    description = f"{workflow.name} {' '.join(n.label for n in workflow.nodes)}"
    risk_assessment = assess_prompt_risk(description)
    risk_level = risk_assessment.risk  # "low" | "medium" | "high" | "critical"

    # Suggested consensus from the SDK
    try:
        consensus_result = select_consensus_protocol(risk_assessment)
        suggested = consensus_result.protocol.value if consensus_result else None
    except Exception:
        suggested = None

    # Run all rules
    issues: list[PolicyIssue] = []
    issues += _r1_missing_hitl(workflow, risk_level)
    issues += _r2_weak_consensus(workflow, risk_level, suggested)
    issues += _r3_paid_call_unguarded(workflow)
    issues += _r4_untrusted_mcp_tool(workflow)
    issues += _r5_write_outside_workspace(workflow, ws)
    issues += _r6_privileged_node(workflow)
    issues += _r7_no_consensus_node(workflow)
    issues += _r8_unbounded_fan_out(workflow)

    can_run = not any(i.severity == "error" for i in issues)

    return PolicyReport(
        workflow_id=workflow.id,
        workflow_name=workflow.name,
        runtime=workflow.runtime,
        risk_level=risk_level,
        suggested_consensus=suggested,
        issues=issues,
        can_run=can_run,
    )
