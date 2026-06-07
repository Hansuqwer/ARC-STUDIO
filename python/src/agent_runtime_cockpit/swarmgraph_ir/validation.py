"""Graph validation for SwarmGraph IR.

Fail-closed: any structural error sets ``ok=False`` so callers (compiler, CLI)
can refuse to proceed. Validation is pure — no I/O, no execution.
"""

from __future__ import annotations

from .models import IRGraph, IRValidationReport


def _has_cycle(adjacency: dict[str, list[str]], node_ids: list[str]) -> bool:
    """Return True if the directed graph contains a cycle (iterative 3-colour DFS).

    Iterative (explicit stack) so deep graphs cannot overflow the recursion
    limit. ``color``: 0=unvisited, 1=on current path, 2=done.
    """
    color: dict[str, int] = dict.fromkeys(node_ids, 0)
    for root in node_ids:
        if color[root] != 0:
            continue
        stack: list[tuple[str, bool]] = [(root, False)]
        while stack:
            node, post_visit = stack.pop()
            if post_visit:
                color[node] = 2
                continue
            if color[node] == 1:
                continue
            color[node] = 1
            stack.append((node, True))  # mark for post-visit (→ black)
            for nxt in adjacency.get(node, ()):
                nxt_color = color.get(nxt, 0)
                if nxt_color == 1:
                    return True  # back-edge to a node on the current path
                if nxt_color == 0:
                    stack.append((nxt, False))
    return False


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
      - graph contains a directed cycle (advisory: legitimate for loop-capable
        runtimes such as LangGraph; DAG-only compilers may escalate to an error)
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

    # Cycle detection (advisory). A directed cycle makes execution
    # non-terminating for DAG runtimes; loop-capable runtimes may allow it.
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_id_set}
    for e in graph.edges:
        if e.from_node in adjacency and e.to_node in node_id_set:
            adjacency[e.from_node].append(e.to_node)
    if _has_cycle(adjacency, node_ids):
        warnings.append("graph contains a directed cycle (not a DAG)")

    return IRValidationReport(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )
