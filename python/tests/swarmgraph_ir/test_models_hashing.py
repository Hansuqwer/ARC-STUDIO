"""IR models + deterministic hashing (Commit 1)."""

from __future__ import annotations

from agent_runtime_cockpit.swarmgraph_ir import (
    IR_SCHEMA_VERSION,
    IRAdapterProvenance,
    IREdge,
    IRGraph,
    IRNode,
    IRNodeKind,
    graph_hash,
)
from agent_runtime_cockpit.swarmgraph_ir.exporters import from_json, to_json


def _graph(node_id: str = "agent") -> IRGraph:
    return IRGraph(
        id="g1",
        name="g",
        runtime="native",
        provenance=IRAdapterProvenance(adapter_id="native", runtime="native"),
        nodes=[
            IRNode(id="__start__", label="START", kind=IRNodeKind.START),
            IRNode(id=node_id, label="Agent", kind=IRNodeKind.AGENT),
            IRNode(id="__end__", label="END", kind=IRNodeKind.END),
        ],
        edges=[
            IREdge(id="__start__\u2192" + node_id, from_node="__start__", to_node=node_id),
            IREdge(id=node_id + "\u2192__end__", from_node=node_id, to_node="__end__"),
        ],
        entry_points=["__start__"],
    )


def test_schema_version_stamped() -> None:
    assert _graph().ir_version == IR_SCHEMA_VERSION


def test_hash_is_deterministic_for_equal_graphs() -> None:
    assert graph_hash(_graph()) == graph_hash(_graph())


def test_hash_changes_when_structure_changes() -> None:
    assert graph_hash(_graph("agent")) != graph_hash(_graph("worker"))


def test_hash_ignores_volatile_fields() -> None:
    a = _graph()
    b = _graph()
    b.compiled_at = "2026-06-02T00:00:00Z"
    b.graph_hash = "deadbeef"
    a.provenance.imported_at = "later"
    assert graph_hash(a) == graph_hash(b)


def test_hash_is_full_sha256_hex() -> None:
    h = graph_hash(_graph())
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_json_round_trip_preserves_structure() -> None:
    g = _graph()
    restored = from_json(to_json(g))
    assert restored.id == g.id
    assert [n.id for n in restored.nodes] == [n.id for n in g.nodes]
    # Round-trip is hash-stable (ignoring the embedded hash field itself).
    assert graph_hash(restored) == graph_hash(g)


def test_unknown_fields_are_ignored_for_forward_compat() -> None:
    data = to_json(_graph())
    import json

    obj = json.loads(data)
    obj["some_future_field"] = {"x": 1}
    obj["nodes"][0]["future_node_field"] = True
    restored = from_json(json.dumps(obj))
    assert restored.id == "g1"
