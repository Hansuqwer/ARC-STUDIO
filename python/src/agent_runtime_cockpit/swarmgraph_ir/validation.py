"""Graph validation for SwarmGraph IR.

Fail-closed: any structural error sets ``ok=False`` so callers (compiler, CLI)
can refuse to proceed. Validation is pure — no I/O, no execution.
"""

from __future__ import annotations

from .models import IRGraph, IRValidationReport


def validate_graph(graph: IRGraph) -> IRValidationReport:
    """Structurally validate an IRGraph.

    Errors (block use):
      - duplicate node ids
      - duplicate edge ids
      - edge references a non-existent node
      - entry point references a non-existent node
      - empty runtime / empty graph id

    Warnings (advisory):
      - graph has no nodes
      - graph has no entry points (but has nodes)
      - node has no incoming/outgoing edges (isolated), excluding start/end
    """
    errors: list[str] = []
    warnings: list[str] = []

    node_ids: list[str] = [n.id for n in graph.nodes]
    node_id_set = set(node_ids)

    if not graph.id:
        errors.append("graph.id is empty")
    if not graph.runtime:
        errors.append("graph.runtime is empty")

    # Duplicate node ids
    seen: set[str] = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(f"duplicate node id: {nid!r}")
        seen.add(nid)

    # Duplicate edge ids + dangling edge endpoints
    edge_seen: set[str] = set()
    for e in graph.edges:
        if e.id in edge_seen:
            errors.append(f"duplicate edge id: {e.id!r}")
        edge_seen.add(e.id)
        if e.from_node not in node_id_set:
            errors.append(f"edge {e.id!r} references missing from_node {e.from_node!r}")
        if e.to_node not in node_id_set:
            errors.append(f"edge {e.id!r} references missing to_node {e.to_node!r}")

    # Entry points must exist
    for ep in graph.entry_points:
        if ep not in node_id_set:
            errors.append(f"entry_point references missing node {ep!r}")

    # Advisory checks
    if not graph.nodes:
        warnings.append("graph has no nodes")
    elif not graph.entry_points:
        warnings.append("graph has no entry_points")

    connected: set[str] = set()
    for e in graph.edges:
        connected.add(e.from_node)
        connected.add(e.to_node)
    for n in graph.nodes:
        if n.id not in connected and n.kind.value not in ("start", "end"):
            warnings.append(f"node {n.id!r} is isolated (no edges)")

    return IRValidationReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )
