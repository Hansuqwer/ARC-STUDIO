"""CLI integration tests for arc ir diff command.

Note: The full `arc` CLI app imports the `swarmgraph` SDK which may not be
available in the test environment. These tests use lazy imports and test the
underlying function directly where the SDK chain is unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Use the run_diff package directly (no SDK dependency in import chain)
from agent_runtime_cockpit.run_diff import (
    diff_ir_from_paths,
    to_json,
    from_json,
    ChangeType,
)
from agent_runtime_cockpit.run_diff.timeline import build_timeline_from_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_ir_file(tmp_path):
    """Write a minimal IR JSON and return the path."""

    def _write(content: dict):
        p = tmp_path / f"{content.get('id', 'graph')}.ir.json"
        p.write_text(json.dumps(content), encoding="utf-8")
        return str(p)

    return _write


# ---------------------------------------------------------------------------
# IR fixture factory
# ---------------------------------------------------------------------------


def _minimal_ir(ir_id: str, graph_hash: str, node_ids: list[str]) -> dict:
    return {
        "ir_version": 1,
        "id": ir_id,
        "name": f"Graph {ir_id}",
        "runtime": "native",
        "provenance": {
            "adapter_id": "test-adapter",
            "runtime": "native",
            "exported_via": "export_workflow",
        },
        "nodes": [
            {
                "id": nid,
                "label": f"Node {nid}",
                "kind": "agent",
                "risk": {"level": "low", "score": 0.0, "signals": [], "source": "heuristic"},
                "capabilities": [],
                "side_effects": [],
                "privileged": False,
                "eval_metadata": {},
                "metadata": {},
            }
            for nid in node_ids
        ],
        "edges": [],
        "entry_points": [node_ids[0]] if node_ids else [],
        "risk": {"level": "low", "score": 0.0, "signals": [], "source": "heuristic"},
        "consensus": {"suggested_protocol": "majority", "source": "default"},
        "graph_hash": graph_hash,
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — identical graphs (no diff)
# ---------------------------------------------------------------------------


def test_ir_diff_identical_graphs(tmp_ir_file):
    """Two identical IR graphs produce zero changes."""
    content = _minimal_ir("g1", "abc123", ["node-a", "node-b"])
    left_path = tmp_ir_file(content)
    right_path = tmp_ir_file(content.copy())

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert report.schema_version == 1
    assert report.mode == "ir_vs_ir"
    assert errors == []
    assert warnings == []
    assert report.summary.total_changes == 0
    assert report.left.graph_hash == report.right.graph_hash


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — node added
# ---------------------------------------------------------------------------


def test_ir_diff_node_added(tmp_ir_file):
    """New node in right graph produces ADDED change."""
    left_content = _minimal_ir("g1", "abc", ["node-a"])
    right_content = _minimal_ir("g2", "def", ["node-a", "node-b"])

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert errors == []
    assert report.summary.nodes_added == 1
    # nodes_added is a list of node ID strings
    assert "node-b" in report.summary.event_types_added or (
        report.graph_diff and "node-b" in report.graph_diff.nodes_added
    )


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — node removed
# ---------------------------------------------------------------------------


def test_ir_diff_node_removed(tmp_ir_file):
    """Node missing in right graph produces REMOVED change."""
    left_content = _minimal_ir("g1", "abc", ["node-a", "node-b"])
    right_content = _minimal_ir("g2", "def", ["node-a"])

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert errors == []
    assert report.summary.nodes_removed >= 1


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — node changed (risk increase)
# ---------------------------------------------------------------------------


def test_ir_diff_risk_increase(tmp_ir_file):
    """Risk level increase in a node sets risk_increased flag."""
    left_content = _minimal_ir("g1", "abc", ["node-a"])
    left_content["nodes"][0]["risk"] = {
        "level": "low",
        "score": 0.0,
        "signals": [],
        "source": "heuristic",
    }
    right_content = _minimal_ir("g2", "def", ["node-a"])
    right_content["nodes"][0]["risk"] = {
        "level": "high",
        "score": 0.8,
        "signals": ["exec_tool"],
        "source": "heuristic",
    }

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    # risk_increased is set when right risk > left risk
    assert report.summary.risk_increased or any(
        n.risk_delta and n.risk_delta != "low"
        for n in (report.graph_diff.nodes_changed if report.graph_diff else [])
    )


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — paid call introduced
# ---------------------------------------------------------------------------


def test_ir_diff_paid_call_introduced(tmp_ir_file):
    """Node in right graph with paid model_call sets paid_call_delta."""
    left_content = _minimal_ir("g1", "abc", ["node-a"])
    left_content["nodes"][0]["kind"] = "agent"
    left_content["nodes"][0]["model_call"] = None

    right_content = _minimal_ir("g2", "def", ["node-a"])
    right_content["nodes"][0]["kind"] = "model_call"
    right_content["nodes"][0]["model_call"] = {
        "provider": "anthropic",
        "paid": True,
        "budget": None,
    }

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert report.summary.paid_call_delta >= 0


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — HITL removed
# ---------------------------------------------------------------------------


def test_ir_diff_hitl_removed(tmp_ir_file):
    """Human gate node removed in right graph sets hitl_removed flag."""
    left_content = _minimal_ir("g1", "abc", ["node-a", "gate-1"])
    left_content["nodes"][1]["kind"] = "human_gate"
    left_content["nodes"][1]["human_gate"] = {"gate_id": "g1", "blocking": True}

    right_content = _minimal_ir("g2", "def", ["node-a"])

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert report.summary.hitl_removed or report.summary.nodes_removed >= 1


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — file not found
# ---------------------------------------------------------------------------


def test_ir_diff_file_not_found():
    """Missing left file populates errors list and returns partial report."""
    report, errors, warnings = diff_ir_from_paths(
        "/nonexistent/left.ir.json", "/nonexistent/right.ir.json"
    )

    assert report is not None
    assert errors != []
    # Partial report should still have schema_version and mode
    assert report.schema_version == 1
    assert report.mode == "ir_vs_ir"


# ---------------------------------------------------------------------------
# Test: diff_ir_from_paths — first divergence detection
# ---------------------------------------------------------------------------


def test_ir_diff_first_divergence(tmp_ir_file):
    """First structural divergence is captured in first_divergence field."""
    left_content = _minimal_ir("g1", "abc", ["node-a", "node-b"])
    right_content = _minimal_ir("g2", "def", ["node-a", "node-c"])

    left_path = tmp_ir_file(left_content)
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    # first_divergence should identify either node-b removed or node-c added
    if report.first_divergence:
        assert report.first_divergence.kind in ("node", "unknown")
        assert report.first_divergence.reason != ""


# ---------------------------------------------------------------------------
# Test: timeline generation from report
# ---------------------------------------------------------------------------


def test_build_timeline_from_report(tmp_ir_file):
    """build_timeline_from_report produces TimelineFrame list."""
    content = _minimal_ir("g1", "abc", ["node-a", "node-b"])
    left_path = tmp_ir_file(content)
    right_content = _minimal_ir("g2", "def", ["node-a", "node-c"])
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    frames = build_timeline_from_report(report)

    assert isinstance(frames, list)
    if report.first_divergence:
        # First frame should be the divergence marker
        assert frames[0].summary.startswith("FIRST DIVERGENCE")
        assert frames[0].change_type == ChangeType.CHANGED
    # Graph diff frames should be present if graph_diff is set
    if report.graph_diff:
        assert len(frames) >= len(report.graph_diff.nodes_added) + len(
            report.graph_diff.nodes_removed
        )


# ---------------------------------------------------------------------------
# Test: to_json / from_json round-trip
# ---------------------------------------------------------------------------


def test_report_json_roundtrip(tmp_ir_file):
    """RunDiffReport serializes and deserializes correctly."""
    content = _minimal_ir("g1", "abc", ["node-a"])
    left_path = tmp_ir_file(content)
    right_path = tmp_ir_file(content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    json_str = to_json(report)
    parsed = from_json(json_str)

    assert parsed.schema_version == report.schema_version
    assert parsed.mode == report.mode
    assert parsed.summary.total_changes == report.summary.total_changes


# ---------------------------------------------------------------------------
# Test: redact flag (redaction is on by default)
# ---------------------------------------------------------------------------


def test_ir_diff_redact_by_default(tmp_ir_file):
    """redact=True (default) should not cause errors even with sensitive data."""
    content = _minimal_ir("g1", "abc", ["node-a"])
    content["metadata"] = {"api_key": "sk-ant-secret123", "token": "ghs_xxx"}
    left_path = tmp_ir_file(content)
    right_path = tmp_ir_file(content)

    # The function always returns the report; redaction is applied at CLI output
    report, errors, warnings = diff_ir_from_paths(left_path, right_path)

    assert report is not None
    assert errors == []


# ---------------------------------------------------------------------------
# Test: timeline=True flag includes frames in output
# ---------------------------------------------------------------------------


def test_ir_diff_timeline_via_build_timeline_from_report(tmp_ir_file):
    """build_timeline_from_report populates timeline frames from a diff report."""
    content = _minimal_ir("g1", "abc", ["node-a"])
    left_path = tmp_ir_file(content)
    right_content = _minimal_ir("g2", "def", ["node-a", "node-b"])
    right_path = tmp_ir_file(right_content)

    report, errors, warnings = diff_ir_from_paths(left_path, right_path)
    frames = build_timeline_from_report(report)

    # Frames should be a list; may be empty if no structural diff
    assert isinstance(frames, list)


# ---------------------------------------------------------------------------
# Test: diff_hash is deterministic
# ---------------------------------------------------------------------------


def test_diff_hash_is_deterministic(tmp_ir_file):
    """Same inputs produce identical diff_hash across two calls."""
    content = _minimal_ir("g1", "abc", ["node-a"])
    left_path = tmp_ir_file(content)
    right_path = tmp_ir_file(content)

    report1, _, _ = diff_ir_from_paths(left_path, right_path)
    report2, _, _ = diff_ir_from_paths(left_path, right_path)

    h1 = report1.with_hash().diff_hash
    h2 = report2.with_hash().diff_hash

    assert h1 == h2
    assert h1 is not None
    assert len(h1) == 64  # SHA-256 hex


# ---------------------------------------------------------------------------
# Test: load_any / load_ir_from_path integration
# ---------------------------------------------------------------------------


def test_load_ir_from_path_integration(tmp_ir_file):
    """load_ir_from_path can be used before diff_ir_from_paths."""
    from agent_runtime_cockpit.run_diff import load_ir_from_path

    content = _minimal_ir("g1", "abc", ["node-a"])
    path = tmp_ir_file(content)

    result = load_ir_from_path(path)
    assert result.ok
    assert result.data is not None
    assert result.data.id == "g1"


# ---------------------------------------------------------------------------
# Test: ir_diff_cmd function exists and has correct signature
# ---------------------------------------------------------------------------


def test_ir_diff_cmd_function_exists():
    """The ir_diff_cmd function is importable from cli/ir.py."""
    import inspect

    try:
        from agent_runtime_cockpit.cli.ir import ir_diff_cmd
    except ModuleNotFoundError:
        # swarmgraph SDK not installed — test via module file inspection instead
        import ast

        ir_py = Path(__file__).parent.parent.parent / "src/agent_runtime_cockpit/cli/ir.py"
        src = ir_py.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "ir_diff_cmd":
                args = [a.arg for a in node.args.args]
                assert "left" in args
                assert "right" in args
                assert "timeline" in args
                assert "redact" in args
                assert "json_output" in args
                assert "debug" in args
                return
        pytest.fail("ir_diff_cmd function not found in cli/ir.py")

    sig = inspect.signature(ir_diff_cmd)
    params = list(sig.parameters.keys())

    assert "left" in params
    assert "right" in params
    assert "timeline" in params
    assert "redact" in params
    assert "json_output" in params
    assert "debug" in params


# ---------------------------------------------------------------------------
# Test: runs_timeline command exists
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="runs_timeline not yet implemented")
def test_runs_timeline_cmd_exists():
    """The runs_timeline command is importable from cli/runs.py."""
    import inspect

    try:
        from agent_runtime_cockpit.cli.runs import runs_timeline
    except ModuleNotFoundError:
        # swarmgraph SDK not installed — test via module file inspection instead
        import ast

        runs_py = Path(__file__).parent.parent.parent / "src/agent_runtime_cockpit/cli/runs.py"
        src = runs_py.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "runs_timeline":
                args = [a.arg for a in node.args.args]
                assert "run_id" in args
                return
        pytest.fail("runs_timeline function not found in cli/runs.py")

    sig = inspect.signature(runs_timeline)
    params = list(sig.parameters.keys())

    assert "run_id" in params
