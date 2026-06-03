"""Tests for SwarmGraph IR graph diff (Commit 2)."""

from __future__ import annotations

import json
import sys
import time


sys.path.insert(0, "/home/user/arc-theia-studio/python/src")

from agent_runtime_cockpit.run_diff import DiffSubjectKind
from agent_runtime_cockpit.run_diff.diff_ir import (
    build_graph_diff,
    diff_ir_from_paths,
    diff_ir_graphs,
    diff_nodes,
    diff_edges,
    find_first_divergence,
)
from agent_runtime_cockpit.swarmgraph_ir import from_json


class TestDiffNodes:
    def test_identical_graphs_no_diff(self, native_minimal_ir_data):
        g = from_json(json.dumps(native_minimal_ir_data))
        changed, added, removed = diff_nodes(g.nodes, g.nodes)
        assert changed == []
        assert added == []
        assert removed == []

    def test_node_added(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        changed, added, removed = diff_nodes(left_g.nodes, right_g.nodes)
        assert "new-node" in added
        assert "new-node" not in removed
        assert changed == []

    def test_node_removed(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        right_data["nodes"] = [n for n in right_data["nodes"] if n["id"] != "agent"]
        right_g = from_json(json.dumps(right_data))
        changed, added, removed = diff_nodes(left_g.nodes, right_g.nodes)
        assert "agent" in removed

    def test_node_changed_fields(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        for n in right_data["nodes"]:
            if n["id"] == "agent":
                n["label"] = "Modified Agent"
        right_g = from_json(json.dumps(right_data))
        changed, added, removed = diff_nodes(left_g.nodes, right_g.nodes)
        assert len(changed) == 1
        assert changed[0].node_id == "agent"
        assert any(f.field_name == "label" for f in changed[0].changed_fields)


class TestDiffEdges:
    def test_identical_edges_no_diff(self, native_minimal_ir_data):
        g = from_json(json.dumps(native_minimal_ir_data))
        added, removed, changed = diff_edges(g.edges, g.edges)
        assert added == []
        assert removed == []
        assert changed == []

    def test_edge_added(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        right_data["edges"].append(
            {
                "id": "agent->new-node",
                "from_node": "agent",
                "to_node": "new-node",
                "conditional": False,
            }
        )
        right_g = from_json(json.dumps(right_data))
        added, removed, changed = diff_edges(left_g.edges, right_g.edges)
        assert "agent->new-node" in added

    def test_edge_removed(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        right_data["edges"] = []
        right_g = from_json(json.dumps(right_data))
        added, removed, changed = diff_edges(left_g.edges, right_g.edges)
        assert len(removed) >= 1


class TestBuildGraphDiff:
    def test_graph_diff_counts(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        gd = build_graph_diff(left_g, right_g)
        assert gd.node_count_left == len(left_g.nodes)
        assert gd.node_count_right == len(right_g.nodes)
        assert "new-node" in gd.nodes_added

    def test_graph_diff_risk_level(self, native_minimal_ir_data, paid_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(paid_ir_data))
        gd = build_graph_diff(left_g, right_g)
        assert gd.risk_level_left == "low"
        assert gd.risk_level_right == "high"


class TestFindFirstDivergence:
    def test_identical_no_divergence(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(native_minimal_ir_data))
        fd = find_first_divergence(left_g, right_g)
        assert fd is None

    def test_node_removed_is_first_divergence(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        right_data["nodes"] = [n for n in right_data["nodes"] if n["id"] != "__start__"]
        right_g = from_json(json.dumps(right_data))
        fd = find_first_divergence(left_g, right_g)
        assert fd is not None
        assert fd.kind == "node"
        assert fd.node_id == "__start__"

    def test_node_added_is_first_divergence(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        fd = find_first_divergence(left_g, right_g)
        assert fd is not None
        assert fd.kind == "node"
        assert fd.node_id == "new-node"


class TestDiffIrGraphs:
    def test_report_has_correct_mode(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.mode == "ir_vs_ir"

    def test_report_has_graph_diff(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.graph_diff is not None
        assert "new-node" in report.graph_diff.nodes_added

    def test_report_has_summary(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.summary.nodes_added == 1
        assert report.summary.has_changes is True

    def test_report_has_hash(self, native_minimal_ir_data, modified_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(modified_ir_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.diff_hash is not None
        assert len(report.diff_hash) == 64

    def test_paid_call_introduced(self, native_minimal_ir_data, paid_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_g = from_json(json.dumps(paid_ir_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.summary.risk_increased is True

    def test_consensus_removed(self, native_minimal_ir_data):
        left_g = from_json(json.dumps(native_minimal_ir_data))
        right_data = json.loads(json.dumps(native_minimal_ir_data))
        right_data["consensus"] = {"suggested_protocol": "raft", "source": "metadata"}
        right_g = from_json(json.dumps(right_data))
        report = diff_ir_graphs(left_g, right_g)
        assert report.summary.consensus_changed is True, (
            f"consensus_left={report.graph_diff.consensus_left!r} consensus_right={report.graph_diff.consensus_right!r}"
        )


class TestDiffIrFromPaths:
    def test_missing_left_file(self, tmp_path):
        report, errors, warnings = diff_ir_from_paths(
            "/nonexistent/a.ir.json", "/nonexistent/b.ir.json"
        )
        assert len(errors) >= 1

    def test_missing_right_file(self, tmp_ir_file, tmp_path):
        report, errors, warnings = diff_ir_from_paths(str(tmp_ir_file), "/nonexistent/b.ir.json")
        assert len(errors) >= 1

    def test_valid_files(self, tmp_ir_file, tmp_ir_file_b):
        report, errors, warnings = diff_ir_from_paths(str(tmp_ir_file), str(tmp_ir_file_b))
        assert len(errors) == 0
        assert report.graph_diff is not None
        assert "new-node" in report.graph_diff.nodes_added

    def test_deterministic_hash(self, tmp_ir_file, tmp_ir_file_b):
        r1, _, _ = diff_ir_from_paths(str(tmp_ir_file), str(tmp_ir_file_b))
        r2, _, _ = diff_ir_from_paths(str(tmp_ir_file), str(tmp_ir_file_b))
        assert r1.diff_hash == r2.diff_hash

    def test_no_mutation_of_input_files(self, tmp_ir_file, tmp_ir_file_b):
        mtime_before = tmp_ir_file.stat().st_mtime
        time.sleep(0.01)
        diff_ir_from_paths(str(tmp_ir_file), str(tmp_ir_file_b))
        mtime_after = tmp_ir_file.stat().st_mtime
        assert mtime_after == mtime_before

    def test_existing_minimal_fixture(self, native_minimal_ir_path, mcp_graph_ir_path):
        report, errors, warnings = diff_ir_from_paths(
            str(native_minimal_ir_path), str(mcp_graph_ir_path)
        )
        assert len(errors) == 0
        assert report.left.kind == DiffSubjectKind.IR_GRAPH
        assert report.right.kind == DiffSubjectKind.IR_GRAPH
        assert report.summary.has_changes is True


class TestNoNetworkPrimitives:
    def test_no_subprocess_in_diff_modules(self):
        import agent_runtime_cockpit.run_diff as run_diff_pkg

        for name in dir(run_diff_pkg):
            mod = getattr(run_diff_pkg, name, None)
            if mod and hasattr(mod, "__file__") and mod.__file__:
                content = open(mod.__file__).read()
                for f in ["subprocess", "socket", "aiohttp", "requests", "httpx", "Popen"]:
                    assert f not in content, f"Found {f} in {mod.__file__}"
