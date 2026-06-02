"""Serialization + the WorkflowInfo bridge for the policy linter.

``to_workflow_info`` projects an IRGraph back into a ``WorkflowInfo`` whose node
and edge ``metadata`` carry exactly the keys that
``security.policy_linter.lint_workflow`` reads. This lets the existing linter run
against IR graphs without any change to the linter itself.
"""

from __future__ import annotations

import json
from typing import Any

from ..protocol.schemas import (
    NodeType,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)
from .hashing import graph_hash
from .models import IRGraph, IRNode, IRNodeKind

# IR node kind -> WorkflowInfo NodeType (the linter's coarser vocabulary).
_KIND_TO_NODETYPE: dict[IRNodeKind, NodeType] = {
    IRNodeKind.AGENT: NodeType.AGENT,
    IRNodeKind.TOOL: NodeType.TOOL,
    IRNodeKind.MCP_TOOL: NodeType.TOOL,
    IRNodeKind.MODEL_CALL: NodeType.AGENT,
    IRNodeKind.HUMAN_GATE: NodeType.ROUTER,
    IRNodeKind.CONSENSUS: NodeType.ROUTER,
    IRNodeKind.ROUTER: NodeType.ROUTER,
    IRNodeKind.FAN_OUT: NodeType.ROUTER,
    IRNodeKind.FAN_IN: NodeType.ROUTER,
    IRNodeKind.START: NodeType.START,
    IRNodeKind.END: NodeType.END,
    IRNodeKind.UNKNOWN: NodeType.UNKNOWN,
}


# ── JSON round-trip ──────────────────────────────────────────────────────────


def to_json(graph: IRGraph, *, indent: int | None = 2, recompute_hash: bool = True) -> str:
    """Serialize an IRGraph to canonical JSON text.

    When ``recompute_hash`` is True the ``graph_hash`` field is (re)computed first
    so the persisted file always carries its own digest.
    """
    if recompute_hash:
        graph = graph.model_copy(update={"graph_hash": None})
        graph.graph_hash = graph_hash(graph)
    return graph.model_dump_json(indent=indent)


def from_json(text: str) -> IRGraph:
    """Parse IR JSON text into an IRGraph (unknown fields ignored)."""
    return IRGraph.model_validate_json(text)


def from_dict(data: dict[str, Any]) -> IRGraph:
    return IRGraph.model_validate(data)


# ── WorkflowInfo bridge (policy-linter input) ────────────────────────────────


def _node_metadata(node: IRNode) -> dict[str, Any]:
    """Build linter-compatible metadata for a single IR node."""
    md: dict[str, Any] = dict(node.metadata)

    # MCP tool flags (linter R4: untrusted_mcp_tool)
    if node.mcp_tool is not None:
        md["is_mcp"] = True
        if node.mcp_tool.manifest_hash:
            md["mcp_manifest_hash"] = node.mcp_tool.manifest_hash

    # Paid-call flags (linter R3: paid_call_unguarded)
    if node.budget is not None:
        if node.budget.requires_paid_call:
            md["requires_paid_call"] = True
        if node.budget.paid_call_gate:
            md["paid_call_gate"] = True

    # Write-path (linter R5: write_outside_workspace)
    if node.write_path:
        md["write_path"] = node.write_path

    # Privileged / trust (linter R6: privileged_node)
    if node.privileged:
        md["privileged"] = True
    if node.trust_annotation:
        md["trust_annotation"] = node.trust_annotation

    # Consensus protocol (linter R2: weak_consensus)
    if node.consensus is not None and node.consensus.protocol:
        md["consensus_protocol"] = node.consensus.protocol

    return md


def to_workflow_info(graph: IRGraph) -> WorkflowInfo:
    """Project an IRGraph into a WorkflowInfo for the policy linter.

    Labels for HITL/consensus nodes embed the keyword the linter matches on so
    label-based rules (R1/R7) keep working.
    """
    nodes: list[WorkflowNode] = []
    for n in graph.nodes:
        label = n.label
        # Ensure label-based linter detection works even if upstream label was bare.
        if (
            n.kind is IRNodeKind.HUMAN_GATE
            and "hitl" not in label.lower()
            and "approval" not in label.lower()
        ):
            label = f"{label} (hitl)".strip()
        if n.kind is IRNodeKind.CONSENSUS and not any(
            kw in label.lower() for kw in ("consensus", "vote", "quorum")
        ):
            label = f"{label} (consensus)".strip()

        nodes.append(
            WorkflowNode(
                id=n.id,
                label=label,
                type=_KIND_TO_NODETYPE.get(n.kind, NodeType.UNKNOWN),
                metadata=_node_metadata(n),
            )
        )

    edges = [
        WorkflowEdge(
            id=e.id,
            from_node=e.from_node,
            to_node=e.to_node,
            label=e.label,
            conditional=e.conditional,
            metadata=dict(e.metadata),
        )
        for e in graph.edges
    ]

    wf_metadata: dict[str, Any] = dict(graph.metadata)
    if graph.consensus.min_workers is not None and "num_workers" not in wf_metadata:
        wf_metadata["num_workers"] = graph.consensus.min_workers

    return WorkflowInfo(
        id=graph.id,
        name=graph.name or graph.id,
        runtime=graph.runtime,
        source_file=graph.provenance.source_file,
        nodes=nodes,
        edges=edges,
        entry_points=list(graph.entry_points),
        metadata=wf_metadata,
    )


def to_dict(graph: IRGraph) -> dict[str, Any]:
    return json.loads(to_json(graph))
