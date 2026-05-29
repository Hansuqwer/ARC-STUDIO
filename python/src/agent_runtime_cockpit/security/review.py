"""Review evidence models for trace-aware review mode (Phase 74).

Each ReviewEvidenceSummary collects available provenance from existing
producers. Missing/absent producers render explicit unknown or absent
states - never fabricated.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .redaction import Redactor


_redactor = Redactor()


class ProvenanceSource(str, Enum):
    """Known provenance categories for a review evidence item."""

    TRACE_EVENT = "trace_event"
    TOOL_CALL = "tool_call"
    HITL_DECISION = "hitl_decision"
    AUDIT_RECORD = "audit_record"
    SANDBOX_RESULT = "sandbox_result"
    EVAL_RESULT = "eval_result"
    TEST_RESULT = "test_result"
    PLAN_STEP = "plan_step"
    EDIT_PLAN = "edit_plan"
    UNKNOWN = "unknown"
    MANUAL = "manual"


class HunkProvenance(BaseModel):
    """Provenance for one diff hunk or change region."""

    file_path: str
    source: ProvenanceSource = ProvenanceSource.UNKNOWN
    source_run_id: str | None = None
    source_step_id: str | None = None
    source_tool: str | None = None
    source_approval_id: str | None = None
    source_audit_id: str | None = None
    source_test_run_id: str | None = None
    classification: str | None = None
    policy_name: str | None = None
    decision_allowed: bool | None = None
    reason: str | None = None
    detail: str | None = None

    @field_validator("source_tool", "reason", "detail")
    @classmethod
    def _redact_free_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _redactor.redact_string(value)


class ReviewEvidenceHeader(BaseModel):
    """Overall review summary for a run or session."""

    run_id: str
    session_id: str | None = None
    workflow_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    total_hunks: int = 0
    unknown_hunks: int = 0
    manual_hunks: int = 0
    classified_hunks: int = 0
    producers_available: list[str] = Field(default_factory=list)
    producers_missing: list[str] = Field(default_factory=list)
    approval_count: int = 0
    sandbox_decision_count: int = 0
    audit_records_count: int = 0
    test_result_count: int = 0
    provenance: list[HunkProvenance] = Field(default_factory=list)


class ReviewEnvelope(BaseModel):
    """Stable JSON envelope for review evidence output."""

    version: Literal[1] = 1
    ok: bool
    data: ReviewEvidenceHeader | None = None
    error: str | None = None


def build_review_summary(
    run_id: str,
    *,
    session_id: str | None = None,
    workflow_name: str | None = None,
    provenance_items: list[HunkProvenance] | None = None,
    available_producers: list[str] | None = None,
    missing_producers: list[str] | None = None,
    approval_count: int = 0,
    sandbox_decision_count: int = 0,
    audit_records_count: int = 0,
    test_result_count: int = 0,
) -> ReviewEvidenceHeader:
    """Build a ReviewEvidenceHeader from whatever provenance is available.

    Missing producers must be listed explicitly so callers know evidence
    gaps without fabricating data.
    """
    provenance = provenance_items or []
    total = len(provenance)
    unknown = sum(1 for p in provenance if p.source == ProvenanceSource.UNKNOWN)
    manual = sum(1 for p in provenance if p.source == ProvenanceSource.MANUAL)
    classified = total - unknown - manual

    return ReviewEvidenceHeader(
        run_id=run_id,
        session_id=session_id,
        workflow_name=workflow_name,
        total_hunks=total,
        unknown_hunks=unknown,
        manual_hunks=manual,
        classified_hunks=classified,
        producers_available=sorted(set(available_producers or [])),
        producers_missing=sorted(set(missing_producers or [])),
        approval_count=approval_count,
        sandbox_decision_count=sandbox_decision_count,
        audit_records_count=audit_records_count,
        test_result_count=test_result_count,
        provenance=provenance,
    )
