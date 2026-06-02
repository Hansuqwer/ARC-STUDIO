"""Native importer: WorkflowInfo -> IRGraph, and raw IR JSON passthrough.

This is the MVP importer. It reads the metadata keys ARC adapters already place on
``WorkflowInfo`` nodes/edges and lifts them into typed IR objects. It performs no
execution and no I/O.
"""

from __future__ import annotations

from typing import Any

from ...protocol.schemas import NodeType, WorkflowInfo, WorkflowNode
from ...security.redaction import redact_secrets
from ..models import (
    IRBudget,
    IRConsensusHint,
    IREdge,
    IRGraph,
    IRMcpToolRef,
    IRNode,
    IRNodeKind,
    IRToolRef,
)
from ..provenance import build_provenance

# Keyword sets mirror security/policy_linter.py so classification stays consistent.
_HITL_LABELS = {"hitl", "approval", "human", "review"}
_CONSENSUS_LABELS = {"consensus", "vote", "majority", "quorum", "bft", "raft", "judge"}


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    return value


def _classify_kind(node: WorkflowNode) -> IRNodeKind:
    label = (node.label or "").lower()
    md = node.metadata or {}

    if md.get("is_mcp") or "mcp" in label:
        return IRNodeKind.MCP_TOOL
    if any(kw in label for kw in _HITL_LABELS):
        return IRNodeKind.HUMAN_GATE
    if any(kw in label for kw in _CONSENSUS_LABELS):
        return IRNodeKind.CONSENSUS

    mapping = {
        NodeType.AGENT: IRNodeKind.AGENT,
        NodeType.TOOL: IRNodeKind.TOOL,
        NodeType.ROUTER: IRNodeKind.ROUTER,
        NodeType.START: IRNodeKind.START,
        NodeType.END: IRNodeKind.END,
    }
    return mapping.get(node.type, IRNodeKind.UNKNOWN)


def _build_node(node: WorkflowNode) -> IRNode:
    md = node.metadata or {}
    kind = _classify_kind(node)

    ir = IRNode(
        id=node.id,
        label=node.label or node.id,
        kind=kind,
        metadata={k: _redact(v) for k, v in md.items()},
    )

    # Tool / MCP refs
    if kind is IRNodeKind.MCP_TOOL:
        ir.mcp_tool = IRMcpToolRef(
            server_id=str(md.get("mcp_server_id") or md.get("server_id") or "unknown"),
            tool_name=str(md.get("mcp_tool_name") or md.get("tool_name") or node.label or node.id),
            manifest_hash=md.get("mcp_manifest_hash") or md.get("manifest_pin"),
        )
    elif kind is IRNodeKind.TOOL:
        ir.tool = IRToolRef(name=str(md.get("tool_name") or node.label or node.id))

    # Budget / paid-call
    if md.get("requires_paid_call") or md.get("paid_call_gate"):
        ir.budget = IRBudget(
            requires_paid_call=bool(md.get("requires_paid_call")),
            paid_call_gate=bool(md.get("paid_call_gate")),
        )

    # Write path (redacted)
    if md.get("write_path"):
        ir.write_path = _redact(str(md["write_path"]))

    # Privileged / trust
    if md.get("privileged"):
        ir.privileged = True
    if md.get("trust_annotation"):
        ir.trust_annotation = str(md["trust_annotation"])

    # Consensus protocol hint carried on the node
    if md.get("consensus_protocol"):
        ir.consensus = IRConsensusHint(protocol=str(md["consensus_protocol"]), source="metadata")

    return ir


def from_workflow_info(
    workflow: WorkflowInfo,
    *,
    adapter_id: str | None = None,
    workspace: str | None = None,
) -> IRGraph:
    """Convert a single WorkflowInfo into an IRGraph (no enrichment, no exec)."""
    runtime = workflow.runtime or (adapter_id or "unknown")
    provenance = build_provenance(
        adapter_id=adapter_id or runtime,
        runtime=runtime,
        source_file=workflow.source_file,
        workspace=workspace,
    )

    nodes = [_build_node(n) for n in workflow.nodes]
    edges = [
        IREdge(
            id=e.id or f"{e.from_node}\u2192{e.to_node}",
            from_node=e.from_node,
            to_node=e.to_node,
            conditional=e.conditional,
            label=e.label,
            metadata=dict(e.metadata or {}),
        )
        for e in workflow.edges
    ]

    graph = IRGraph(
        id=workflow.id,
        name=workflow.name,
        runtime=runtime,
        provenance=provenance,
        nodes=nodes,
        edges=edges,
        entry_points=list(workflow.entry_points),
        metadata=dict(workflow.metadata or {}),
    )

    num_workers = (workflow.metadata or {}).get("num_workers")
    if isinstance(num_workers, int):
        graph.consensus = IRConsensusHint(min_workers=num_workers, source="metadata")

    return graph


def from_ir_dict(data: dict[str, Any]) -> IRGraph:
    """Passthrough importer for documents already in IR shape."""
    return IRGraph.model_validate(data)
