"""Validation report (Commit 2) — fail-closed behaviour."""

from __future__ import annotations

from agent_runtime_cockpit.swarmgraph_ir import (
    IRAdapterProvenance,
    IREdge,
    IRGraph,
    IRNode,
    IRNodeKind,
    validate_graph,
)


def _base(nodes, edges, entry=None) -> IRGraph:
    return IRGraph(
        id="g",
        runtime="native",
        provenance=IRAdapterProvenance(adapter_id="native", runtime="native"),
        nodes=nodes,
        edges=edges,
        entry_points=entry or [],
    )


def test_valid_graph_ok() -> None:
    g = _base(
        [IRNode(id="a", kind=IRNodeKind.AGENT), IRNode(id="b", kind=IRNodeKind.AGENT)],
        [IREdge(id="a\u2192b", from_node="a", to_node="b")],
        entry=["a"],
    )
    r = validate_graph(g)
    assert r.ok is True
    assert r.errors == []
    assert r.node_count == 2 and r.edge_count == 1


def test_duplicate_node_id_is_error() -> None:
    g = _base([IRNode(id="a"), IRNode(id="a")], [])
    r = validate_graph(g)
    assert r.ok is False
    assert any("duplicate node id" in e for e in r.errors)


def test_dangling_edge_is_error() -> None:
    g = _base([IRNode(id="a")], [IREdge(id="a\u2192z", from_node="a", to_node="z")])
    r = validate_graph(g)
    assert r.ok is False
    assert any("missing to_node" in e for e in r.errors)


def test_entry_point_missing_node_is_error() -> None:
    g = _base([IRNode(id="a")], [], entry=["zzz"])
    r = validate_graph(g)
    assert r.ok is False
    assert any("entry_point references missing node" in e for e in r.errors)


def test_empty_runtime_is_error() -> None:
    g = _base([IRNode(id="a")], [])
    g.runtime = ""
    r = validate_graph(g)
    assert r.ok is False
    assert any("graph.runtime is empty" in e for e in r.errors)


def test_isolated_node_is_warning_not_error() -> None:
    g = _base(
        [IRNode(id="a", kind=IRNodeKind.AGENT), IRNode(id="island", kind=IRNodeKind.AGENT)],
        [],
        entry=["a"],
    )
    r = validate_graph(g)
    assert r.ok is True  # warnings do not block
    assert any("isolated" in w for w in r.warnings)
