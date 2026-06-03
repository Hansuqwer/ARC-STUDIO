"""Tests for run_diff models and deterministic hashing (Commit 1)."""

from __future__ import annotations


from agent_runtime_cockpit.run_diff import (
    RUN_DIFF_SCHEMA_VERSION,
    ChangeType,
    DiffSubject,
    DiffSubjectKind,
    DiffSummary,
    FirstDivergence,
    GraphDiff,
    NodeDiff,
    PolicyIssueDiff,
    RunDiffReport,
    TimelineFrame,
)


def test_schema_version_bumped():
    assert RUN_DIFF_SCHEMA_VERSION == 1


def test_run_diff_report_empty():
    report = RunDiffReport()
    assert report.schema_version == RUN_DIFF_SCHEMA_VERSION
    assert report.mode == "run_vs_run"


def test_run_diff_report_with_subjects():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="graph-a", hash="aaa", graph_hash="aaa")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="graph-b", hash="bbb", graph_hash="bbb")
    report = RunDiffReport(left=left, right=right, mode="ir_vs_ir")
    assert report.left.id == "graph-a"
    assert report.right.id == "graph-b"


def test_deterministic_hash_same_inputs():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1", hash="abc")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2", hash="def")
    r1 = RunDiffReport(left=left, right=right, mode="ir_vs_ir")
    r2 = RunDiffReport(left=left, right=right, mode="ir_vs_ir")
    h1 = r1.compute_hash()
    h2 = r2.compute_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_deterministic_hash_different_inputs():
    left_a = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1", hash="abc")
    right_a = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2", hash="def")
    r_a = RunDiffReport(left=left_a, right=right_a, mode="ir_vs_ir")
    left_b = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g3", hash="xyz")
    right_b = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g4", hash="uvw")
    r_b = RunDiffReport(left=left_b, right=right_b, mode="ir_vs_ir")
    assert r_a.compute_hash() != r_b.compute_hash()


def test_hash_ignores_generated_at():
    left = DiffSubject(kind=DiffSubjectKind.RUN_RECORD, id="r1")
    right = DiffSubject(kind=DiffSubjectKind.RUN_RECORD, id="r2")
    r1 = RunDiffReport(left=left, right=right, mode="run_vs_run")
    r1.generated_at = "2026-01-01T00:00:00Z"
    r2 = RunDiffReport(left=left, right=right, mode="run_vs_run")
    r2.generated_at = "2099-12-31T23:59:59Z"
    assert r1.compute_hash() == r2.compute_hash()


def test_hash_ignores_diff_hash_field():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2")
    r1 = RunDiffReport(left=left, right=right)
    h1 = r1.compute_hash()
    r2 = r1.model_copy(deep=True)
    r2.diff_hash = "FAKE_HASH"
    h2 = r2.compute_hash()
    assert h1 == h2


def test_hash_changes_with_graph_diff():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2")
    r1 = RunDiffReport(left=left, right=right, mode="ir_vs_ir")
    r2 = RunDiffReport(
        left=left,
        right=right,
        mode="ir_vs_ir",
        graph_diff=GraphDiff(nodes_added=["new-node"], node_count_left=3, node_count_right=4),
    )
    assert r1.compute_hash() != r2.compute_hash()


def test_hash_changes_with_summary():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2")
    r1 = RunDiffReport(left=left, right=right)
    r1.summary.compute_total()
    r2 = RunDiffReport(left=left, right=right, summary=DiffSummary(nodes_added=1))
    r2.summary.compute_total()
    assert r1.compute_hash() != r2.compute_hash()


def test_with_hash_sets_field():
    report = RunDiffReport(
        left=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1"),
        right=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2"),
    )
    result = report.with_hash()
    assert result.diff_hash is not None
    assert len(result.diff_hash) == 64
    assert report.diff_hash is None


def test_summary_compute_total():
    s = DiffSummary(
        nodes_added=2, nodes_removed=1, events_added=5, events_changed=3, policy_issues_added=1
    )
    s.compute_total()
    assert s.total_changes == 2 + 1 + 5 + 3 + 1
    assert s.has_changes is True


def test_summary_has_changes_false_when_empty():
    s = DiffSummary()
    s.compute_total()
    assert s.has_changes is False


def test_node_diff_semantic_regression():
    nd = NodeDiff(
        node_id="write-node",
        change_type=ChangeType.CHANGED,
        hitl_delta="removed",
        is_semantic_regression=True,
        regression_reason="HITL gate removed",
    )
    assert nd.is_semantic_regression is True
    assert nd.regression_reason == "HITL gate removed"
    assert nd.hitl_delta == "removed"


def test_first_divergence_model():
    fd = FirstDivergence(
        kind="node",
        node_id="write-node",
        reason="HITL gate removed",
        left_value={"human_gate": {"blocking": True}},
        right_value={"human_gate": None},
    )
    assert fd.kind == "node"
    assert fd.node_id == "write-node"
    assert fd.left_value["human_gate"]["blocking"] is True
    assert fd.right_value["human_gate"] is None


def test_timeline_frame_model():
    frame = TimelineFrame(
        frame_id="frame-001",
        sequence=0,
        subject="ir",
        node_id="agent",
        summary="Node added: agent",
        change_type=ChangeType.ADDED,
        left_label=None,
        right_label="right",
        redacted=False,
    )
    assert frame.frame_id == "frame-001"
    assert frame.change_type == ChangeType.ADDED
    assert frame.redacted is False


def test_graph_diff_model():
    gd = GraphDiff(
        nodes_added=["new-node"],
        nodes_removed=["old-node"],
        node_count_left=3,
        node_count_right=4,
        risk_level_left="low",
        risk_level_right="high",
    )
    assert gd.nodes_added == ["new-node"]
    assert gd.risk_level_left == "low"
    assert gd.risk_level_right == "high"


def test_policy_issue_diff_model():
    diff = PolicyIssueDiff(
        rule="missing_hitl",
        left_severity=None,
        right_severity="error",
        left_present=False,
        right_present=True,
        is_regression=True,
        regression_type="blocker_introduced",
    )
    assert diff.rule == "missing_hitl"
    assert diff.is_regression is True


def test_extra_fields_ignored():
    data = {
        "schema_version": 1,
        "left": {"kind": "ir_graph", "id": "g1"},
        "right": {"kind": "ir_graph", "id": "g2"},
        "mode": "ir_vs_ir",
        "future_field": {"x": 1},
        "summary": {},
    }
    report = RunDiffReport.model_validate(data)
    assert report.left.id == "g1"
    assert report.right.id == "g2"


def test_round_trip_json():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1", hash="aaa")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2", hash="bbb")
    report = RunDiffReport(
        left=left,
        right=right,
        mode="ir_vs_ir",
        summary=DiffSummary(nodes_added=1, nodes_removed=0),
        first_divergence=FirstDivergence(kind="node", node_id="new-node", reason="Node added"),
    )
    report.summary.compute_total()
    h = report.compute_hash()
    report.diff_hash = h
    json_str = report.model_dump_json()
    restored = RunDiffReport.model_validate_json(json_str)
    assert restored.left.id == "g1"
    assert restored.right.id == "g2"
    assert restored.summary.nodes_added == 1
    assert restored.first_divergence.node_id == "new-node"
    assert restored.diff_hash == h


def test_hash_excludes_timeline():
    left = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1")
    right = DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2")
    r1 = RunDiffReport(left=left, right=right)
    h1 = r1.compute_hash()
    r2 = r1.model_copy(deep=True)
    r2.timeline = [
        TimelineFrame(
            frame_id="f1",
            sequence=0,
            subject="ir",
            summary="Node added",
            change_type=ChangeType.ADDED,
        )
    ]
    h2 = r2.compute_hash()
    assert h1 == h2


def test_changetype_enum_values():
    assert ChangeType.ADDED.value == "added"
    assert ChangeType.REMOVED.value == "removed"
    assert ChangeType.CHANGED.value == "changed"
    assert ChangeType.UNCHANGED.value == "unchanged"
