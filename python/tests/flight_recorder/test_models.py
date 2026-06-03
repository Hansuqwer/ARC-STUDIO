"""Tests for flight_recorder.models — typing, hashing, event construction."""

from __future__ import annotations

import json


from agent_runtime_cockpit.flight_recorder.models import (
    SCHEMA_VERSION,
    EventType,
    FlightEvent,
    FlightExportBundle,
    FlightIndex,
    FlightRecorderConfig,
    FlightSegment,
    FlightVerificationReport,
    RedactionSummary,
    RunEntry,
    SegmentRef,
)


# ---------------------------------------------------------------------------
# EventType
# ---------------------------------------------------------------------------


class TestEventType:
    def test_all_types_are_strings(self):
        for et in EventType:
            assert isinstance(et.value, str)
            assert "." in et.value  # namespace.action format

    def test_run_lifecycle_types(self):
        assert EventType.RUN_STARTED.value == "run.started"
        assert EventType.RUN_COMPLETED.value == "run.completed"
        assert EventType.RUN_FAILED.value == "run.failed"

    def test_ir_compiled(self):
        assert EventType.IR_COMPILED.value == "ir.compiled"

    def test_crash_marker(self):
        assert EventType.CRASH_MARKER.value == "crash.marker"


# ---------------------------------------------------------------------------
# FlightEvent
# ---------------------------------------------------------------------------


class TestFlightEvent:
    def _make_event(self, **kwargs) -> FlightEvent:
        defaults = dict(
            event_id="evt-001",
            event_type=EventType.RUN_STARTED,
            run_id="run-abc",
            timestamp="2026-06-03T10:00:00Z",
            sequence=0,
        )
        defaults.update(kwargs)
        return FlightEvent(**defaults)

    def test_basic_construction(self):
        evt = self._make_event()
        assert evt.schema_version == SCHEMA_VERSION
        assert evt.event_type == EventType.RUN_STARTED
        assert evt.run_id == "run-abc"

    def test_hash_is_deterministic(self):
        evt = self._make_event()
        h1 = evt.compute_hash()
        h2 = evt.compute_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_hash_changes_with_payload(self):
        evt1 = self._make_event(payload={"a": 1})
        evt2 = self._make_event(payload={"a": 2})
        assert evt1.compute_hash() != evt2.compute_hash()

    def test_with_hash_populates_field(self):
        evt = self._make_event(payload={"x": "y"})
        assert evt.hash == ""
        evt2 = evt.with_hash()
        assert evt2.hash == evt.compute_hash()
        assert len(evt2.hash) == 64

    def test_hash_excludes_hash_field(self):
        """Two events identical except for hash field should have same computed hash."""
        evt1 = self._make_event()
        evt2 = evt1.model_copy(update={"hash": "something_else"})
        assert evt1.compute_hash() == evt2.compute_hash()

    def test_event_is_json_serialisable(self):
        evt = self._make_event(payload={"key": "value"}).with_hash()
        data = json.loads(evt.model_dump_json())
        assert data["event_type"] == "run.started"
        assert data["hash"] != ""

    def test_redaction_summary_embedded(self):
        red = RedactionSummary(fields_redacted=["token"], redact_applied=True)
        evt = self._make_event(redaction=red)
        assert evt.redaction.redact_applied is True

    def test_optional_refs(self):
        evt = self._make_event(audit_ref="audit-xyz", trace_ref="run-abc")
        assert evt.audit_ref == "audit-xyz"
        assert evt.trace_ref == "run-abc"

    def test_schema_version(self):
        evt = self._make_event()
        assert evt.schema_version == "1"


# ---------------------------------------------------------------------------
# FlightSegment
# ---------------------------------------------------------------------------


class TestFlightSegment:
    def test_construction(self):
        seg = FlightSegment(
            segment_id="seg-001",
            run_id="run-abc",
            created_at="2026-06-03T10:00:00Z",
        )
        assert seg.previous_segment_hash == "GENESIS"
        assert seg.corrupt is False
        assert seg.event_count == 0

    def test_mutable(self):
        seg = FlightSegment(
            segment_id="seg-001", run_id="run-abc", created_at="2026-06-03T10:00:00Z"
        )
        seg.event_count = 5
        assert seg.event_count == 5


# ---------------------------------------------------------------------------
# FlightIndex
# ---------------------------------------------------------------------------


class TestFlightIndex:
    def test_empty_index(self):
        idx = FlightIndex()
        assert idx.segments == []
        assert idx.runs == {}
        assert idx.retention.max_segments == 200

    def test_serialise_round_trip(self):
        idx = FlightIndex(
            runs={"run-1": RunEntry(run_id="run-1", started_at="2026-06-03T10:00:00Z")},
        )
        data = json.loads(idx.model_dump_json())
        idx2 = FlightIndex.model_validate(data)
        assert "run-1" in idx2.runs

    def test_segment_refs(self):
        seg = SegmentRef(
            segment_id="seg-1",
            run_id="run-1",
            created_at="2026-06-03T10:00:00Z",
        )
        idx = FlightIndex(segments=[seg])
        assert idx.segments[0].segment_id == "seg-1"


# ---------------------------------------------------------------------------
# FlightRecorderConfig
# ---------------------------------------------------------------------------


class TestFlightRecorderConfig:
    def test_defaults(self):
        cfg = FlightRecorderConfig()
        assert cfg.enabled is True
        assert cfg.redact_secrets is True
        assert cfg.fail_closed is True
        assert cfg.max_segment_bytes == 5 * 1024 * 1024
        assert cfg.max_age_days == 30

    def test_custom(self):
        cfg = FlightRecorderConfig(base_dir="/tmp/test", max_segments=10)
        assert cfg.max_segments == 10


# ---------------------------------------------------------------------------
# FlightExportBundle
# ---------------------------------------------------------------------------


class TestFlightExportBundle:
    def test_construction(self):
        bundle = FlightExportBundle(
            bundle_id="bnd-001",
            created_at="2026-06-03T10:00:00Z",
            runs=["run-abc"],
        )
        assert bundle.schema_version == SCHEMA_VERSION
        assert bundle.total_events == 0


# ---------------------------------------------------------------------------
# FlightVerificationReport
# ---------------------------------------------------------------------------


class TestFlightVerificationReport:
    def test_defaults(self):
        report = FlightVerificationReport(ok=True)
        assert report.ok is True
        assert report.hash_chain_valid is True
        assert report.corrupt_segments == []
        assert report.missing_segments == []

    def test_not_ok(self):
        from agent_runtime_cockpit.flight_recorder.models import VerificationIssue

        report = FlightVerificationReport(ok=False)
        issue = VerificationIssue(segment_id="seg-1", issue_type="hash_mismatch", detail="bad hash")
        report.issues.append(issue)
        assert len(report.issues) == 1
