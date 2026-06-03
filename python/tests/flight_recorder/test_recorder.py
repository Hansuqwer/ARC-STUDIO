"""Tests for flight_recorder.recorder — FlightRecorder public API.

Covers:
  - Start and stop run.
  - Record events.
  - Redaction before persistence.
  - Index updated on events.
  - Segment rotation.
  - Crash marker.
  - Status output.
  - Disabled recorder no-ops.
  - No network / subprocess / model calls.
"""

from __future__ import annotations

from pathlib import Path


from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
from agent_runtime_cockpit.flight_recorder.models import EventType
from agent_runtime_cockpit.flight_recorder import index as _index


def _make_recorder(tmp_path: Path, **kwargs) -> FlightRecorder:
    cfg = FlightRecorderConfig(
        base_dir=str(tmp_path / ".arc" / "flight"),
        max_segment_bytes=1024 * 1024,
        **kwargs,
    )
    return FlightRecorder(config=cfg)


class TestBasicRecording:
    def test_start_and_stop_run(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-001")
        recorder.stop_run("run-001", status="completed")
        # Index should have the run
        idx = _index.load_index(Path(recorder._config.base_dir))
        assert "run-001" in idx.runs
        assert idx.runs["run-001"].status == "completed"

    def test_record_event(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-002")
        evt = recorder.record("run-002", EventType.IR_COMPILED, payload={"ir_hash": "abc123"})
        recorder.stop_run("run-002")
        assert evt is not None
        assert evt.event_type == EventType.IR_COMPILED
        assert len(evt.hash) == 64

    def test_event_written_to_disk(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-003")
        recorder.record("run-003", EventType.POLICY_EVALUATED, payload={"risk": "low"})
        recorder.stop_run("run-003")

        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-003"
        events_files = list(seg_dir.glob("*.events.jsonl"))
        assert len(events_files) >= 1

        content = events_files[0].read_text()
        lines = [l for l in content.splitlines() if l.strip()]
        assert len(lines) >= 1

    def test_event_has_hash(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-004")
        evt = recorder.record("run-004", EventType.RUN_STARTED, payload={})
        recorder.stop_run("run-004")
        assert evt is not None
        assert evt.hash != ""

    def test_sequence_is_monotonic(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-005")
        evts = [
            recorder.record("run-005", EventType.TOOL_CALL_PLANNED, payload={"i": i})
            for i in range(5)
        ]
        recorder.stop_run("run-005")
        sequences = [e.sequence for e in evts if e]
        # Sequences should be strictly increasing
        for a, b in zip(sequences, sequences[1:]):
            assert b > a


class TestRedactionBeforePersistence:
    def test_api_key_not_in_persisted_file(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-redact")
        recorder.record(
            "run-redact",
            EventType.IR_COMPILED,
            payload={"api_key": "sk-proj-SUPERSECRETKEY12345678901234", "safe": "ok"},
        )
        recorder.stop_run("run-redact")

        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-redact"
        for events_file in seg_dir.glob("*.events.jsonl"):
            content = events_file.read_text()
            assert "sk-proj-SUPERSECRETKEY" not in content, (
                f"Secret found in {events_file}: {content[:200]}"
            )

    def test_bearer_token_not_in_file(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-bearer")
        recorder.record(
            "run-bearer",
            EventType.MCP_MANIFEST_CHECKED,
            payload={"auth": "Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"},
        )
        recorder.stop_run("run-bearer")

        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-bearer"
        for events_file in seg_dir.glob("*.events.jsonl"):
            content = events_file.read_text()
            assert "ghp_ABCDEFGHIJKLMNOPQ" not in content

    def test_safe_payload_preserved(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-safe")
        recorder.record(
            "run-safe",
            EventType.IR_COMPILED,
            payload={"ir_hash": "abc123def456", "node_count": 5},
        )
        recorder.stop_run("run-safe")

        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-safe"
        for events_file in seg_dir.glob("*.events.jsonl"):
            content = events_file.read_text()
            assert "abc123def456" in content


class TestSegmentRotation:
    def test_segment_rotates_on_size(self, tmp_path):
        # Use 1-byte segment size to force rotation
        cfg = FlightRecorderConfig(
            base_dir=str(tmp_path / ".arc" / "flight"),
            max_segment_bytes=1,  # Force rotation every event
        )
        recorder = FlightRecorder(config=cfg)
        recorder.start_run("run-rotate")
        for i in range(3):
            recorder.record("run-rotate", EventType.TOOL_CALL_PLANNED, payload={"i": i})
        recorder.stop_run("run-rotate")

        base = Path(cfg.base_dir)
        seg_dir = base / "segments" / "run-rotate"
        events_files = list(seg_dir.glob("*.events.jsonl"))
        assert len(events_files) > 1  # Should have multiple segments


class TestCrashMarker:
    def test_crash_marker_recorded(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        evt = recorder.crash_marker("run-crash", reason="SIGKILL")
        assert evt is not None
        assert evt.event_type == EventType.CRASH_MARKER
        assert evt.payload.get("reason") == "SIGKILL"

    def test_crash_marker_for_unregistered_run(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        # No start_run() called
        evt = recorder.crash_marker("run-unknown", reason="unexpected_crash")
        assert evt is not None


class TestErrorEvent:
    def test_error_raised_event(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-err")
        evt = recorder.record_error("run-err", "ValueError", "something went wrong")
        recorder.stop_run("run-err", status="failed")
        assert evt is not None
        assert evt.event_type == EventType.ERROR_RAISED


class TestDisabledRecorder:
    def test_disabled_recorder_returns_none(self, tmp_path):
        cfg = FlightRecorderConfig(
            base_dir=str(tmp_path / ".arc" / "flight"),
            enabled=False,
        )
        recorder = FlightRecorder(config=cfg)
        recorder.start_run("run-disabled")
        evt = recorder.record("run-disabled", EventType.RUN_STARTED, payload={})
        assert evt is None

    def test_disabled_recorder_no_files_created(self, tmp_path):
        cfg = FlightRecorderConfig(
            base_dir=str(tmp_path / ".arc" / "flight"),
            enabled=False,
        )
        recorder = FlightRecorder(config=cfg)
        recorder.start_run("run-disabled")
        recorder.stop_run("run-disabled")
        base = Path(cfg.base_dir)
        assert not (base / "segments").exists()


class TestStatus:
    def test_status_returns_dict(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        status = recorder.status()
        assert "enabled" in status
        assert "base_dir" in status
        assert "total_segments" in status
        assert "total_runs" in status

    def test_status_enabled(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        status = recorder.status()
        assert status["enabled"] is True

    def test_status_shows_active_runs(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-active")
        status = recorder.status()
        assert "run-active" in status["active_runs"]
        recorder.stop_run("run-active")


class TestIndexUpdated:
    def test_index_has_run_after_start(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-idx")
        idx = _index.load_index(Path(recorder._config.base_dir))
        assert "run-idx" in idx.runs
        recorder.stop_run("run-idx")

    def test_index_has_segment_after_event(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-seg")
        recorder.record("run-seg", EventType.IR_COMPILED, payload={})
        idx = _index.load_index(Path(recorder._config.base_dir))
        assert len(idx.segments) >= 1
        recorder.stop_run("run-seg")

    def test_run_status_updated_on_stop(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-finish")
        recorder.stop_run("run-finish", status="completed")
        idx = _index.load_index(Path(recorder._config.base_dir))
        assert idx.runs["run-finish"].status == "completed"


class TestNoForbiddenPrimitives:
    """Structural safety: no actual usage of subprocess/socket/network in recorder modules."""

    FORBIDDEN_PATTERNS = [
        ("import subprocess", r"\bimport\s+subprocess\b"),
        ("subprocess call", r"\bsubprocess\s*\.\s*(run|call|Popen|check_output)\s*\("),
        ("import socket", r"\bimport\s+socket\b"),
        ("import aiohttp", r"\bimport\s+aiohttp\b"),
        ("import requests", r"\bimport\s+requests\b"),
        ("import httpx", r"\bimport\s+httpx\b"),
        ("os.system", r"\bos\s*\.\s*system\s*\("),
        ("Popen call", r"\bPopen\s*\("),
        ("urlopen call", r"\burlopen\s*\("),
    ]

    def _check(self, source: str, module_name: str) -> None:
        import re

        for label, pattern in self.FORBIDDEN_PATTERNS:
            assert not re.search(pattern, source), f"Forbidden: '{label}' found in {module_name}"

    def test_no_subprocess_in_recorder(self):
        import inspect
        from agent_runtime_cockpit.flight_recorder import recorder as _recorder_module

        self._check(inspect.getsource(_recorder_module), "recorder.py")

    def test_no_subprocess_in_segments(self):
        import inspect
        from agent_runtime_cockpit.flight_recorder import segments as _seg_module

        self._check(inspect.getsource(_seg_module), "segments.py")

    def test_no_subprocess_in_redaction(self):
        import inspect
        from agent_runtime_cockpit.flight_recorder import redaction as _red_module

        self._check(inspect.getsource(_red_module), "redaction.py")
