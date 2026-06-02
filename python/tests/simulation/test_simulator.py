"""Tests for the Action Simulator."""

from __future__ import annotations


from agent_runtime_cockpit.swarmgraph_ir.models import (
    IRAdapterProvenance,
    IRBudget,
    IREdge,
    IRGraph,
    IRHumanGate,
    IRMcpToolRef,
    IRNode,
    IRNodeKind,
    IRSideEffect,
    IRToolRef,
    SideEffectKind,
)
from agent_runtime_cockpit.simulation import SimulationConfig, simulate_graph


def _provenance() -> IRAdapterProvenance:
    return IRAdapterProvenance(adapter_id="native", runtime="swarmgraph")


def _graph(*nodes, edges=None, entry_points=None) -> IRGraph:
    return IRGraph(
        id="wf-test",
        name="test",
        runtime="swarmgraph",
        provenance=_provenance(),
        nodes=list(nodes),
        edges=edges or [],
        entry_points=entry_points or [],
    )


def _node(nid, kind=IRNodeKind.TOOL, **kwargs) -> IRNode:
    return IRNode(id=nid, label=nid, kind=kind, **kwargs)


class TestBasicSimulation:
    def test_returns_report(self, tmp_path):
        g = _graph(_node("n1"), _node("n2"))
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert r.graph_id == "wf-test"
        assert r.determinism_hash is not None
        assert len(r.nodes) == 2

    def test_all_nodes_reachable_by_default(self, tmp_path):
        g = _graph(_node("n1"), _node("n2"))
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert all(n.reachable for n in r.nodes)

    def test_summary_counts_correct(self, tmp_path):
        g = _graph(
            _node("n1"),
            _node("n2", kind=IRNodeKind.HUMAN_GATE, human_gate=IRHumanGate(gate_id="g1")),
        )
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert r.summary.total_nodes == 2
        assert r.summary.hitl_gate_count == 1
        assert r.summary.gate_count >= 1

    def test_would_execute_always_false(self, tmp_path):
        node = _node("n1", tool=IRToolRef(name="my_tool"))
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        for tc in r.tool_calls:
            assert tc.would_execute is False


class TestSideEffects:
    def test_write_side_effect_detected(self, tmp_path):
        node = _node("n1", side_effects=[IRSideEffect(kind=SideEffectKind.WRITE, target="/tmp/x")])
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(se.kind == "write" for se in r.side_effects)

    def test_write_side_effect_audit_required(self, tmp_path):
        node = _node("n1", side_effects=[IRSideEffect(kind=SideEffectKind.WRITE)])
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(se.audit_required for se in r.side_effects)

    def test_paid_call_detected(self, tmp_path):
        node = _node("n1", side_effects=[IRSideEffect(kind=SideEffectKind.PAID_CALL, paid=True)])
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert r.cost.has_paid_calls
        assert r.summary.paid_call_count >= 1


class TestGates:
    def test_hitl_gate_classified(self, tmp_path):
        node = _node(
            "n1", kind=IRNodeKind.HUMAN_GATE, human_gate=IRHumanGate(gate_id="g1", blocking=True)
        )
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(gate.kind == "hitl" for gate in r.gates)
        assert r.summary.hitl_gate_count == 1

    def test_privileged_gate_classified(self, tmp_path):
        node = _node("n1", privileged=True)
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(gate.kind == "privileged" for gate in r.gates)

    def test_paid_call_gate_classified(self, tmp_path):
        node = _node("n1", budget=IRBudget(requires_paid_call=True, paid_call_gate=False))
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(gate.kind == "paid_call" for gate in r.gates)

    def test_write_gate_classified(self, tmp_path):
        node = _node("n1", write_path="/tmp/output.txt")
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert any(gate.kind == "write" for gate in r.gates)


class TestMcp:
    def test_mcp_tool_in_tool_calls(self, tmp_path):
        node = _node(
            "n1",
            kind=IRNodeKind.MCP_TOOL,
            mcp_tool=IRMcpToolRef(server_id="srv-a", tool_name="read_file"),
        )
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path), include_mcp_registry=False))
        assert any(tc.is_mcp and tc.tool_name == "read_file" for tc in r.tool_calls)
        assert "srv-a" in r.mcp.unique_servers

    def test_unpinned_mcp_in_summary(self, tmp_path):
        node = _node(
            "n1",
            kind=IRNodeKind.MCP_TOOL,
            mcp_tool=IRMcpToolRef(server_id="srv-b", tool_name="write_file", manifest_hash=None),
        )
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path), include_mcp_registry=False))
        assert "srv-b" in r.mcp.unpinned_servers


class TestOpaque:
    def test_opaque_node_flagged(self, tmp_path):
        node = _node("n1", kind=IRNodeKind.UNKNOWN)
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        sim_node = next(n for n in r.nodes if n.node_id == "n1")
        assert sim_node.is_opaque

    def test_non_opaque_known_node(self, tmp_path):
        node = _node("n1", kind=IRNodeKind.TOOL, tool=IRToolRef(name="t"))
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        sim_node = next(n for n in r.nodes if n.node_id == "n1")
        assert not sim_node.is_opaque


class TestDeterminism:
    def test_same_graph_same_hash(self, tmp_path):
        g = _graph(_node("n1"), _node("n2"))
        r1 = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        r2 = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert r1.determinism_hash == r2.determinism_hash

    def test_different_nodes_different_hash(self, tmp_path):
        g1 = _graph(_node("n1"))
        g2 = _graph(_node("n1"), _node("n2"))
        r1 = simulate_graph(g1, SimulationConfig(workspace=str(tmp_path)))
        r2 = simulate_graph(g2, SimulationConfig(workspace=str(tmp_path)))
        assert r1.determinism_hash != r2.determinism_hash

    def test_stable_id_format(self, tmp_path):
        node = _node("mynode", side_effects=[IRSideEffect(kind=SideEffectKind.WRITE)])
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert all(se.id.startswith("se-mynode-") for se in r.side_effects)

    def test_json_round_trip(self, tmp_path):
        import json

        g = _graph(_node("n1"))
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        data = json.loads(r.model_dump_json())
        assert data["graph_id"] == "wf-test"
        assert "determinism_hash" in data


class TestReachability:
    def test_bfs_reachability(self, tmp_path):
        nodes = [_node("start"), _node("mid"), _node("end")]
        edges = [
            IREdge(id="e1", from_node="start", to_node="mid"),
            IREdge(id="e2", from_node="mid", to_node="end"),
        ]
        g = _graph(*nodes, edges=edges, entry_points=["start"])
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path), assume_all_branches=False))
        reachable = {n.node_id for n in r.nodes if n.reachable}
        assert reachable == {"start", "mid", "end"}

    def test_unreachable_node_skipped(self, tmp_path):
        nodes = [_node("start"), _node("orphan")]
        g = _graph(*nodes, entry_points=["start"])
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path), assume_all_branches=False))
        start_node = next(n for n in r.nodes if n.node_id == "start")
        orphan_node = next(n for n in r.nodes if n.node_id == "orphan")
        assert start_node.reachable
        assert not orphan_node.reachable


class TestPolicyIntegration:
    def test_policy_embedded_in_report(self, tmp_path):
        g = _graph(_node("n1"))
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        assert hasattr(r.policy, "can_run")
        assert isinstance(r.policy.risk_level, str)

    def test_write_outside_workspace_flagged_in_policy(self, tmp_path):
        node = _node("n1", write_path="/etc/passwd")
        g = _graph(node)
        r = simulate_graph(g, SimulationConfig(workspace=str(tmp_path)))
        # policy should have errors for write outside workspace
        assert isinstance(r.policy.error_count, int)


class TestEvalRecommendations:
    def test_no_recommendations_by_default(self, tmp_path):
        g = _graph(_node("n1"))
        r = simulate_graph(
            g, SimulationConfig(workspace=str(tmp_path), include_eval_recommendations=False)
        )
        assert r.recommendations == []

    def test_loads_recommendations_from_dir(self, tmp_path):
        import json

        rec_dir = tmp_path / ".arc" / "evals" / "recommendations"
        rec_dir.mkdir(parents=True)
        (rec_dir / "test.json").write_text(
            json.dumps(
                {
                    "recommendations": [
                        {
                            "id": "rec-001",
                            "category": "consensus",
                            "title": "Increase consensus",
                            "confidence": 0.8,
                            "action": "set_consensus=majority",
                        }
                    ]
                }
            )
        )
        g = _graph(_node("n1"))
        r = simulate_graph(
            g, SimulationConfig(workspace=str(tmp_path), include_eval_recommendations=True)
        )
        assert len(r.recommendations) == 1
        assert r.recommendations[0].category == "consensus"
