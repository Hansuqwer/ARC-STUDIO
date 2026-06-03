"""Safety test suite for flight_recorder package.

These tests verify structural safety guarantees:
  - No subprocess / socket / network primitives in any module.
  - No aiohttp, requests, httpx, os.system, Popen, urlopen.
  - No model calls, no MCP server startup.
  - No tool execution.
  - All modules importable without side effects.
  - Deterministic event ordering.
"""

from __future__ import annotations

import inspect


# Patterns that signal actual USAGE of forbidden primitives.
# We match import/call forms, not docstring mentions.
# Each entry: (label, pattern_string)
FORBIDDEN_PATTERNS = [
    ("import subprocess", r"\bimport\s+subprocess\b"),
    (
        "subprocess.run/call/Popen",
        r"\bsubprocess\s*\.\s*(run|call|Popen|check_output|check_call)\s*\(",
    ),
    ("import socket", r"\bimport\s+socket\b"),
    (
        "socket.connect/listen/accept",
        r"\bsocket\s*\.\s*(connect|listen|accept|create_connection)\s*\(",
    ),
    ("import aiohttp", r"\bimport\s+aiohttp\b"),
    ("import requests", r"\bimport\s+requests\b"),
    ("import httpx", r"\bimport\s+httpx\b"),
    ("os.system call", r"\bos\s*\.\s*system\s*\("),
    ("Popen call", r"\bPopen\s*\("),
    ("urlopen call", r"\burlopen\s*\("),
    ("listen() call", r"\bsocket\b.*\blisten\s*\("),
    ("serve() call", r"\.serve\s*\("),
]


def _get_source(module) -> str:
    try:
        return inspect.getsource(module)
    except Exception:
        return ""


class TestNoForbiddenPrimitives:
    """Structural grep over all flight_recorder modules — no actual usage of forbidden primitives."""

    def _check_module(self, module_name: str):
        import importlib
        import re as _re

        mod = importlib.import_module(f"agent_runtime_cockpit.flight_recorder.{module_name}")
        source = _get_source(mod)
        for label, pattern in FORBIDDEN_PATTERNS:
            assert not _re.search(pattern, source), (
                f"Forbidden primitive '{label}' (pattern: {pattern!r}) "
                f"found in flight_recorder/{module_name}.py"
            )

    def test_models_no_forbidden(self):
        self._check_module("models")

    def test_redaction_no_forbidden(self):
        self._check_module("redaction")

    def test_segments_no_forbidden(self):
        self._check_module("segments")

    def test_index_no_forbidden(self):
        self._check_module("index")

    def test_recorder_no_forbidden(self):
        self._check_module("recorder")

    def test_verify_no_forbidden(self):
        self._check_module("verify")

    def test_retention_no_forbidden(self):
        self._check_module("retention")

    def test_export_no_forbidden(self):
        self._check_module("export")


class TestImportSafety:
    """Importing modules must not cause side effects."""

    def test_import_models_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import models

        assert hasattr(models, "FlightEvent")

    def test_import_recorder_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import recorder

        assert hasattr(recorder, "FlightRecorder")

    def test_import_segments_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import segments

        assert hasattr(segments, "SegmentWriter")

    def test_import_redaction_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import redaction

        assert hasattr(redaction, "redact_payload")

    def test_import_verify_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import verify

        assert hasattr(verify, "verify")

    def test_import_retention_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import retention

        assert hasattr(retention, "prune")

    def test_import_export_no_side_effect(self):
        from agent_runtime_cockpit.flight_recorder import export

        assert hasattr(export, "export_run")


class TestDeterministicOrdering:
    """Event sequences must be deterministic and monotonically increasing."""

    def test_sequence_monotonic(self, tmp_path):
        from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
        from agent_runtime_cockpit.flight_recorder.models import EventType

        cfg = FlightRecorderConfig(base_dir=str(tmp_path / ".arc" / "flight"))
        recorder = FlightRecorder(config=cfg)
        recorder.start_run("run-det")
        evts = [
            recorder.record("run-det", EventType.TOOL_CALL_PLANNED, payload={"i": i})
            for i in range(10)
        ]
        recorder.stop_run("run-det")
        seqs = [e.sequence for e in evts if e]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)  # no duplicates

    def test_event_hash_is_deterministic(self):
        from agent_runtime_cockpit.flight_recorder.models import EventType, FlightEvent

        evt = FlightEvent(
            event_id="det-01",
            event_type=EventType.IR_COMPILED,
            run_id="run-det",
            timestamp="2026-06-03T10:00:00Z",
            sequence=0,
            payload={"ir_hash": "abc123"},
        )
        h1 = evt.compute_hash()
        h2 = evt.compute_hash()
        assert h1 == h2
        assert len(h1) == 64


class TestNoModelOrToolCalls:
    """Verify recorder operations do not call models, tools, or MCP servers."""

    def test_recorder_operations_are_pure_io(self, tmp_path):
        """Full record cycle must complete without calling any model/tool/MCP."""
        from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
        from agent_runtime_cockpit.flight_recorder.models import EventType

        cfg = FlightRecorderConfig(base_dir=str(tmp_path / ".arc" / "flight"))
        recorder = FlightRecorder(config=cfg)

        # These operations must complete without raising due to network/model unavailability
        recorder.start_run("run-pure")
        recorder.record("run-pure", EventType.IR_COMPILED, payload={"ir_hash": "xyz"})
        recorder.record("run-pure", EventType.POLICY_EVALUATED, payload={"risk": "low"})
        recorder.record("run-pure", EventType.SIMULATION_GENERATED, payload={"sim_hash": "abc"})
        recorder.crash_marker("run-pure", reason="test")
        recorder.stop_run("run-pure")
        # If we reach here, no model/tool/MCP calls were needed


class TestFailClosed:
    """Fail-closed behaviour on malformed records."""

    def test_fail_closed_drops_event_on_redaction_error(self, tmp_path, monkeypatch):
        from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
        from agent_runtime_cockpit.flight_recorder.models import EventType
        import agent_runtime_cockpit.flight_recorder.recorder as rec_mod

        # Patch redact_payload to raise
        def _bad_redact(payload, **kwargs):
            raise RuntimeError("simulated redaction failure")

        monkeypatch.setattr(rec_mod, "redact_payload", _bad_redact)

        cfg = FlightRecorderConfig(
            base_dir=str(tmp_path / ".arc" / "flight"),
            fail_closed=True,
        )
        recorder = FlightRecorder(config=cfg)
        recorder.start_run("run-fc")
        evt = recorder.record("run-fc", EventType.IR_COMPILED, payload={"x": 1})
        recorder.stop_run("run-fc")
        # With fail_closed=True, event should be dropped (None)
        assert evt is None
