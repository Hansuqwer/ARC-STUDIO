"""ARC Composer — visual SwarmGraph builder codegen (R98).

Generates SwarmGraph Python code from an IR graph representation.
Includes validation (cycle/dead-node detection) via swarmgraph_ir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..swarmgraph_ir.models import IRGraph, IRNode, IRNodeKind, IREdge
from ..swarmgraph_ir.validation import validate_graph

log = logging.getLogger(__name__)


@dataclass
class CodeGenResult:
    code: str
    graph_id: str
    node_count: int
    edge_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _node_kind_to_swarmgraph(kind: IRNodeKind) -> str:
    """Map IR node kind to SwarmGraph node type string."""
    mapping = {
        IRNodeKind.AGENT: "AgentNode",
        IRNodeKind.TOOL: "ToolNode",
        IRNodeKind.MCP_TOOL: "MCPToolNode",
        IRNodeKind.MODEL_CALL: "ModelCallNode",
        IRNodeKind.HUMAN_GATE: "HumanGateNode",
        IRNodeKind.CONSENSUS: "ConsensusNode",
        IRNodeKind.ROUTER: "RouterNode",
        IRNodeKind.FAN_OUT: "FanOutNode",
        IRNodeKind.FAN_IN: "FanInNode",
        IRNodeKind.START: "StartNode",
        IRNodeKind.END: "EndNode",
        IRNodeKind.UNKNOWN: "UnknownNode",
    }
    return mapping.get(kind, "UnknownNode")


def _generate_node_code(node: IRNode) -> str:
    """Generate Python code for a single IR node."""
    node_type = _node_kind_to_swarmgraph(node.kind)
    lines = [
        f"    {node.id} = {node_type}(",
        f'        id="{node.id}",',
        f'        label="{node.label}",',
    ]
    desc = getattr(node, "description", None) or node.metadata.get("description", "")
    if desc:
        lines.append(f'        description="{desc}",')
    if node.risk and node.risk.level != "low":
        lines.append(f'        risk_level="{node.risk.level}",')
    lines.append("    )")
    return "\n".join(lines)


def _generate_edge_code(edge: IREdge) -> str:
    """Generate Python code for a single IR edge."""
    label = edge.label or ""
    return f'    graph.add_edge("{edge.from_node}", "{edge.to_node}", label="{label}")'


def generate_swarmgraph_code(graph: IRGraph) -> CodeGenResult:
    """Generate SwarmGraph Python code from an IR graph.

    Performs validation first. Returns errors if validation fails.
    """
    report = validate_graph(graph)

    if not report.ok:
        return CodeGenResult(
            code="",
            graph_id=graph.id,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            errors=report.errors,
            warnings=report.warnings,
        )

    lines = [
        '"""Auto-generated SwarmGraph workflow.',
        f"Graph ID: {graph.id}",
        f"Runtime: {graph.runtime}",
        f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}",
        '"""',
        "",
        "from swarmgraph import SwarmGraph",
        "from swarmgraph.nodes import (",
        "    AgentNode, ToolNode, MCPToolNode, ModelCallNode,",
        "    HumanGateNode, ConsensusNode, RouterNode,",
        "    FanOutNode, FanInNode, StartNode, EndNode,",
        ")",
        "",
        "",
        f"def build_{graph.id.replace('-', '_')}():",
        '    """Build the SwarmGraph workflow."""',
        f'    graph = SwarmGraph(id="{graph.id}", runtime="{graph.runtime}")',
        "",
        "    # Nodes",
    ]

    for node in graph.nodes:
        lines.append(_generate_node_code(node))
        lines.append("")

    lines.append("    # Edges")
    for edge in graph.edges:
        lines.append(_generate_edge_code(edge))

    lines.append("")
    lines.append("    return graph")
    lines.append("")

    code = "\n".join(lines)

    return CodeGenResult(
        code=code,
        graph_id=graph.id,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
        warnings=report.warnings,
    )


def validate_composer_graph(graph: IRGraph) -> dict[str, Any]:
    """Validate a graph for the composer (cycle/dead-node detection)."""
    report = validate_graph(graph)
    return {
        "ok": report.ok,
        "graph_id": graph.id,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "errors": report.errors,
        "warnings": report.warnings,
        "has_cycles": any("cycle" in w.lower() for w in report.warnings),
        "has_dead_nodes": any(
            "isolated" in w.lower() or "dead" in w.lower() for w in report.warnings
        ),
    }


__all__ = [
    "CodeGenResult",
    "generate_swarmgraph_code",
    "validate_composer_graph",
]
