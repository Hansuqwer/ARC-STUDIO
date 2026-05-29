"""Tests for review evidence models and CLI (Phase 74)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.security.review import (
    HunkProvenance,
    ProvenanceSource,
    build_review_summary,
)

runner = CliRunner()


class TestReviewEvidenceModels:
    def test_hunk_provenance_unknown_default(self) -> None:
        h = HunkProvenance(file_path="src/foo.py")
        assert h.source == ProvenanceSource.UNKNOWN
        assert h.file_path == "src/foo.py"
        assert h.source_run_id is None

    def test_hunk_provenance_with_trace(self) -> None:
        h = HunkProvenance(
            file_path="src/bar.py",
            source=ProvenanceSource.TRACE_EVENT,
            source_run_id="run-123",
            source_step_id="step-1",
            classification="read_only",
        )
        assert h.source == ProvenanceSource.TRACE_EVENT
        assert h.source_run_id == "run-123"
        assert h.classification == "read_only"

    def test_hunk_provenance_redacts_secret_text(self) -> None:
        h = HunkProvenance(
            file_path="src/bar.py",
            detail="api_key=abcdefghijklmnop",
            reason="password=secret-value",
        )
        assert "abcdefghijklmnop" not in (h.detail or "")
        assert h.detail == "[REDACTED]"
        assert h.reason == "[REDACTED]"

    def test_build_review_summary_empty(self) -> None:
        header = build_review_summary(run_id="run-1")
        assert header.run_id == "run-1"
        assert header.total_hunks == 0
        assert header.unknown_hunks == 0
        assert header.classified_hunks == 0
        assert header.provenance == []

    def test_build_review_summary_with_provenance(self) -> None:
        items = [
            HunkProvenance(
                file_path="a.py",
                source=ProvenanceSource.TOOL_CALL,
                source_run_id="r1",
            ),
            HunkProvenance(file_path="b.py", source=ProvenanceSource.UNKNOWN),
            HunkProvenance(file_path="c.py", source=ProvenanceSource.MANUAL),
        ]
        header = build_review_summary(
            run_id="r1",
            provenance_items=items,
            available_producers=["tool_call", "sandbox_audit"],
            missing_producers=["eval", "test"],
        )
        assert header.total_hunks == 3
        assert header.unknown_hunks == 1
        assert header.manual_hunks == 1
        assert header.classified_hunks == 1
        assert header.producers_available == ["sandbox_audit", "tool_call"]
        assert header.producers_missing == ["eval", "test"]

    def test_review_evidence_header_serialization(self) -> None:
        header = build_review_summary(
            run_id="r1",
            provenance_items=[
                HunkProvenance(file_path="x.py", source=ProvenanceSource.AUDIT_RECORD),
            ],
            approval_count=2,
            sandbox_decision_count=3,
        )
        data = header.model_dump(mode="json")
        assert data["run_id"] == "r1"
        assert data["total_hunks"] == 1
        assert data["approval_count"] == 2
        assert data["sandbox_decision_count"] == 3
        assert len(data["provenance"]) == 1

    def test_provenance_source_enum_values(self) -> None:
        assert ProvenanceSource.TRACE_EVENT.value == "trace_event"
        assert ProvenanceSource.TOOL_CALL.value == "tool_call"
        assert ProvenanceSource.HITL_DECISION.value == "hitl_decision"
        assert ProvenanceSource.UNKNOWN.value == "unknown"
        assert ProvenanceSource.MANUAL.value == "manual"
        assert ProvenanceSource.PLAN_STEP.value == "plan_step"
        assert ProvenanceSource.EDIT_PLAN.value == "edit_plan"

    def test_no_fabricated_data(self) -> None:
        """Missing producers must render explicit absent/unknown states."""
        header = build_review_summary(
            run_id="r1",
            missing_producers=["sandbox_audit", "hitl", "eval"],
        )
        assert header.producers_missing == ["eval", "hitl", "sandbox_audit"]
        assert header.producers_available == []
        assert header.total_hunks == 0


class TestReviewCli:
    def test_review_summarize_help(self) -> None:
        result = runner.invoke(app, ["review", "summarize", "--help"])
        assert result.exit_code == 0
        assert "summarize" in result.output.lower() or "review" in result.output.lower()

    def test_review_summarize_json(self) -> None:
        result = runner.invoke(app, ["review", "summarize", "--json", "--run-id", "test-run-1"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["run_id"] == "test-run-1"
        assert "provenance" in data["data"]
        assert "producers_available" in data["data"]
        assert "producers_missing" in data["data"]

    def test_review_summarize_with_command(self) -> None:
        result = runner.invoke(
            app,
            [
                "review",
                "summarize",
                "--json",
                "--run-id",
                "test-run-2",
                "--",
                "ls",
                "-la",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        provenance = data["data"]["provenance"]
        plan_items = [p for p in provenance if p["source"] == "plan_step"]
        assert len(plan_items) >= 1
        assert plan_items[0]["classification"] == "read_only"

    def test_review_summarize_destructive_command(self) -> None:
        result = runner.invoke(
            app,
            ["review", "summarize", "--json", "--run-id", "test-run-3", "--", "rm", "-rf", "."],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        provenance = data["data"]["provenance"]
        plan_items = [p for p in provenance if p["source"] == "plan_step"]
        assert len(plan_items) >= 1
        assert plan_items[0]["classification"] == "destructive"
        assert plan_items[0]["decision_allowed"] is False

    def test_review_summarize_includes_edit_plan(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "note.txt").write_text("old\n", encoding="utf-8")
        plan = runner.invoke(
            app, ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"]
        )
        assert plan.exit_code == 0, plan.output

        result = runner.invoke(app, ["review", "summarize", "--json", "--run-id", "r-edit"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)["data"]
        assert "edit_plan" in data["producers_available"]
        edit_items = [p for p in data["provenance"] if p["source"] == "edit_plan"]
        assert edit_items
        assert edit_items[0]["file_path"] == "note.txt"
        assert edit_items[0]["classification"] == "writes_workspace"

    def test_review_summarize_marks_edit_plan_missing(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["review", "summarize", "--json", "--run-id", "r-empty"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)["data"]
        assert "edit_plan" in data["producers_missing"]
