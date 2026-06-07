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


# ─── CR-017: cycle detection (advisory) ──────────────────────────────────────


def test_cycle_is_warning_not_error() -> None:
    # a -> b -> a is a directed cycle. Advisory only — loop-capable runtimes
    # (e.g. LangGraph) legitimately use cycles, so it must not block.
    g = _base(
        [IRNode(id="a", kind=IRNodeKind.AGENT), IRNode(id="b", kind=IRNodeKind.AGENT)],
        [
            IREdge(id="a2b", from_node="a", to_node="b"),
            IREdge(id="b2a", from_node="b", to_node="a"),
        ],
        entry=["a"],
    )
    r = validate_graph(g)
    assert r.ok is True
    assert any("cycle" in w.lower() for w in r.warnings)


def test_self_loop_is_cycle_warning() -> None:
    g = _base(
        [IRNode(id="a", kind=IRNodeKind.AGENT)],
        [IREdge(id="a2a", from_node="a", to_node="a")],
        entry=["a"],
    )
    r = validate_graph(g)
    assert any("cycle" in w.lower() for w in r.warnings)


def test_acyclic_linear_graph_has_no_cycle_warning() -> None:
    g = _base(
        [IRNode(id=x, kind=IRNodeKind.AGENT) for x in ("a", "b", "c")],
        [
            IREdge(id="a2b", from_node="a", to_node="b"),
            IREdge(id="b2c", from_node="b", to_node="c"),
        ],
        entry=["a"],
    )
    r = validate_graph(g)
    assert not any("cycle" in w.lower() for w in r.warnings)


def test_diamond_dag_is_not_a_cycle() -> None:
    # a->b, a->c, b->d, c->d revisits d but is acyclic (no false positive).
    g = _base(
        [IRNode(id=x, kind=IRNodeKind.AGENT) for x in ("a", "b", "c", "d")],
        [
            IREdge(id="a2b", from_node="a", to_node="b"),
            IREdge(id="a2c", from_node="a", to_node="c"),
            IREdge(id="b2d", from_node="b", to_node="d"),
            IREdge(id="c2d", from_node="c", to_node="d"),
        ],
        entry=["a"],
    )
    r = validate_graph(g)
    assert not any("cycle" in w.lower() for w in r.warnings)
