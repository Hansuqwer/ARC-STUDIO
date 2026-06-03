"""Tests for redaction and timeline (Commit 5 & 6)."""

from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/arc-theia-studio/python/src")

from pathlib import Path

from agent_runtime_cockpit.run_diff import (
    ChangeType,
    RunDiffReport,
    TimelineFrame,
    TimeTravelCursor,
)


class TestRedaction:
    def test_redact_api_key(self):
        from agent_runtime_cockpit.run_diff import redact_text

        text = "Authorization: Bearer sk-ant-api03-xxxx"
        redacted = redact_text(text)
        assert "[REDACTED]" in redacted
        assert "sk-ant" not in redacted

    def test_redact_dict(self):
        from agent_runtime_cockpit.run_diff import redact_dict

        data = {
            "tool": "write_file",
            "parameters": {"path": "/tmp/test", "api_key": "sk-ant-secret123"},
        }
        redacted = redact_dict(data)
        assert redacted["parameters"]["api_key"] == "[REDACTED]"
        assert redacted["parameters"]["path"] == "/tmp/test"

    def test_redact_report(self):
        from agent_runtime_cockpit.run_diff import redact_report

        report = {
            "left": {"id": "graph-a"},
            "right": {"id": "graph-b"},
            "mode": "ir_vs_ir",
            "graph_diff": {
                "nodes_changed": [{"node_id": "agent", "metadata": {"api_key": "sk-ant-secret"}}]
            },
        }
        redacted = redact_report(report)
        assert redacted["graph_diff"]["nodes_changed"][0]["metadata"]["api_key"] == "[REDACTED]"

    def test_is_safe_true_for_clean_text(self):
        from agent_runtime_cockpit.run_diff import is_safe

        assert is_safe("This is a normal string") is True
        assert is_safe('{"node_id": "agent", "label": "Agent"}') is True

    def test_is_safe_false_for_secret(self):
        from agent_runtime_cockpit.run_diff import is_safe

        assert (
            is_safe(
                "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
            )
            is False
        )

    def test_no_mutation_on_redact(self):
        from agent_runtime_cockpit.run_diff import redact_dict

        original = {"key": "value", "secret": "sk-secret123"}
        original_copy = dict(original)
        redact_dict(original)
        assert original == original_copy


class TestTimeline:
    def test_build_timeline_from_report(self):
        from agent_runtime_cockpit.run_diff.diff_ir import diff_ir_from_paths
        from agent_runtime_cockpit.run_diff.timeline import build_timeline_from_report

        fixtures_dir = Path(__file__).parent.parent / "swarmgraph_ir" / "fixtures"
        a_path = fixtures_dir / "native_minimal.ir.json"
        b_path = fixtures_dir / "mcp_graph.ir.json"

        report, _, _ = diff_ir_from_paths(str(a_path), str(b_path))
        frames = build_timeline_from_report(report)
        assert len(frames) > 0
        assert all(hasattr(f, "frame_id") for f in frames)

    def test_timeline_cursor_step_forward_back(self):
        frames = [
            TimelineFrame(
                frame_id="f" + str(i),
                sequence=i,
                subject="ir",
                summary="Frame " + str(i),
                change_type=ChangeType.UNCHANGED,
            )
            for i in range(5)
        ]
        cursor = TimeTravelCursor(frames)
        assert cursor.can_step_forward is True
        assert cursor.can_step_back is False
        cursor.step_forward()
        assert cursor.sequence == 1
        cursor.step_back()
        assert cursor.sequence == 0

    def test_timeline_cursor_seek_to(self):
        frames = [
            TimelineFrame(
                frame_id="f" + str(i),
                sequence=i,
                subject="ir",
                summary="Frame " + str(i),
                change_type=ChangeType.UNCHANGED,
            )
            for i in range(10)
        ]
        cursor = TimeTravelCursor(frames)
        frame = cursor.seek_to("f5")
        assert frame is not None
        assert cursor.sequence == 5

    def test_timeline_cursor_context(self):
        frames = [
            TimelineFrame(
                frame_id="f" + str(i),
                sequence=i,
                subject="ir",
                summary="Frame " + str(i),
                change_type=ChangeType.UNCHANGED,
            )
            for i in range(10)
        ]
        cursor = TimeTravelCursor(frames)
        cursor.seek_to("f5")
        ctx = cursor.context(before=2, after=2)
        assert len(ctx) == 5
        assert ctx[0].sequence == 3

    def test_timeline_cursor_as_dict(self):
        frames = [
            TimelineFrame(
                frame_id="f0",
                sequence=0,
                subject="ir",
                summary="Frame 0",
                change_type=ChangeType.UNCHANGED,
            )
        ]
        cursor = TimeTravelCursor(frames)
        d = cursor.as_dict()
        assert d["frame_id"] == "f0"
        assert d["sequence"] == 0


class TestExport:
    def test_to_json_serialization(self):
        from agent_runtime_cockpit.run_diff import DiffSubject, DiffSubjectKind
        from agent_runtime_cockpit.run_diff.export import to_json

        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1"),
            right=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2"),
        )
        json_str = to_json(report)
        import json

        data = json.loads(json_str)
        assert data["schema_version"] == 1
        assert data["left"]["id"] == "g1"

    def test_to_json_redact_secrets(self):
        from agent_runtime_cockpit.run_diff import DiffSubject, DiffSubjectKind
        from agent_runtime_cockpit.run_diff.export import to_json

        report = RunDiffReport(
            left=DiffSubject(
                kind=DiffSubjectKind.RUN_RECORD,
                id="r1",
                metadata={"secret": "sk-ant-test123456789"},
            ),
            right=DiffSubject(kind=DiffSubjectKind.RUN_RECORD, id="r2"),
        )
        json_str = to_json(report, redact=True)
        assert "sk-ant" not in json_str

    def test_from_json_round_trip(self):
        from agent_runtime_cockpit.run_diff import DiffSubject, DiffSubjectKind
        from agent_runtime_cockpit.run_diff.export import from_json, to_json

        original = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1"),
            right=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2"),
        )
        h = original.compute_hash()
        original.diff_hash = h
        json_str = to_json(original)
        restored = from_json(json_str)
        assert restored.left.id == "g1"
        assert restored.diff_hash == h

    def test_summary_text_output(self):
        from agent_runtime_cockpit.run_diff import DiffSubject, DiffSubjectKind
        from agent_runtime_cockpit.run_diff.export import summary_text

        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g1"),
            right=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id="g2"),
        )
        report.summary.nodes_added = 2
        report.summary.compute_total()
        text = summary_text(report)
        assert "=== Run Diff Report ===" in text
        assert "Nodes:" in text
