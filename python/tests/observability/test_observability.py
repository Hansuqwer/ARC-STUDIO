"""Tests for the observability export package."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _export(fixture: str, **kwargs):
    from agent_runtime_cockpit.observability import ObservabilityExportConfig, export_trace

    cfg = ObservabilityExportConfig(
        **{k: v for k, v in kwargs.items() if k in ObservabilityExportConfig.model_fields}
    )
    return export_trace(str(FIXTURES / fixture), cfg=cfg)


# ── Loader tests ──────────────────────────────────────────────────────────────


class TestLoaders:
    def test_load_run_record_format(self):
        from agent_runtime_cockpit.observability import load_trace_file

        t = load_trace_file(FIXTURES / "minimal_run.jsonl")
        assert t.run_id == "run-001"
        assert t.workflow_id == "wf-test"
        assert len(t.events) == 2

    def test_load_raw_events_format(self):
        from agent_runtime_cockpit.observability import load_trace_file

        t = load_trace_file(FIXTURES / "run_with_hitl.jsonl")
        assert t.run_id == "run-hitl"
        assert len(t.events) >= 4

    def test_corrupt_lines_tolerated(self):
        from agent_runtime_cockpit.observability import load_trace_file

        t = load_trace_file(FIXTURES / "corrupt_run.jsonl")
        assert t.skipped_lines == 1
        assert len(t.events) == 2  # 2 valid lines

    def test_missing_file_raises(self):
        from agent_runtime_cockpit.observability import load_trace_file

        with pytest.raises(FileNotFoundError):
            load_trace_file("/nonexistent/path.jsonl")


# ── Span generation ───────────────────────────────────────────────────────────


class TestSpanGeneration:
    def test_root_run_span_created(self):
        export = _export("minimal_run.jsonl")
        names = [s.name for s in export.spans]
        assert "arc.run" in names

    def test_root_span_has_run_id(self):
        export = _export("minimal_run.jsonl")
        root = next(s for s in export.spans if s.name == "arc.run")
        assert root.attributes.get("arc.run.id") == "run-001"

    def test_tool_call_creates_child_span(self):
        export = _export("run_with_tool.jsonl")
        names = [s.name for s in export.spans]
        assert "arc.tool.call" in names

    def test_mcp_tool_creates_child_span(self):
        export = _export("run_with_tool.jsonl")
        names = [s.name for s in export.spans]
        assert "arc.mcp.tool" in names

    def test_hitl_creates_span_event(self):
        export = _export("run_with_hitl.jsonl")
        root = next(s for s in export.spans if s.name == "arc.run")
        event_names = [e.name for e in root.events]
        assert "arc.hitl.gate" in event_names

    def test_consensus_creates_span_event(self):
        export = _export("run_with_hitl.jsonl")
        root = next(s for s in export.spans if s.name == "arc.run")
        event_names = [e.name for e in root.events]
        assert "arc.consensus.select" in event_names

    def test_policy_creates_span_event(self):
        export = _export("run_with_hitl.jsonl")
        root = next(s for s in export.spans if s.name == "arc.run")
        event_names = [e.name for e in root.events]
        assert "arc.policy.evaluate" in event_names

    def test_unknown_event_preserved_as_opaque(self):
        export = _export("run_with_hitl.jsonl")
        root = next(s for s in export.spans if s.name == "arc.run")
        [e for e in root.events if "unknown" in e.name or "custom" in e.name or "arc.arc" in e.name]
        # The arc.unknown.custom event should become an opaque span event
        assert any(
            "arc_unknown" in e.name or "arc.arc" in e.name or "opaque" in e.name
            for e in root.events
        ), f"No opaque event found in {[e.name for e in root.events]}"

    def test_parent_child_references_valid(self):
        export = _export("run_with_tool.jsonl")
        span_ids = {s.span_id for s in export.spans}
        for span in export.spans:
            if span.parent_span_id:
                assert span.parent_span_id in span_ids, (
                    f"Span {span.span_id} references missing parent {span.parent_span_id}"
                )


# ── Redaction ─────────────────────────────────────────────────────────────────


class TestRedaction:
    def test_api_key_redacted_in_export(self):
        export = _export("secret_trace.jsonl", redact_secrets=True)
        serialized = export.model_dump_json()
        # The fake API key value must not appear in output
        assert "sk-testFAKEKEYabcdef1234567890NOTREAL" not in serialized

    def test_redaction_summary_populated(self):
        export = _export("secret_trace.jsonl", redact_secrets=True)
        # With redaction, we should have captured some tokens
        assert export.redaction_summary is not None

    def test_no_secrets_in_exported_file(self, tmp_path):
        out = str(tmp_path / "out.json")
        _export("secret_trace.jsonl", redact_secrets=True)
        from agent_runtime_cockpit.observability.exporters import export_trace
        from agent_runtime_cockpit.observability import ObservabilityExportConfig

        export_trace(
            str(FIXTURES / "secret_trace.jsonl"),
            cfg=ObservabilityExportConfig(redact_secrets=True),
            out=out,
        )
        content = Path(out).read_text()
        assert "sk-testFAKEKEYabcdef1234567890NOTREAL" not in content

    def test_key_named_fields_redacted(self):
        from agent_runtime_cockpit.observability.redaction import redact_dict

        result, tokens = redact_dict({"api_key": "supersecret", "name": "test"})
        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"
        assert tokens == 1


# ── Determinism ───────────────────────────────────────────────────────────────


class TestDeterminism:
    def test_export_hash_is_deterministic(self):
        export1 = _export("minimal_run.jsonl")
        export2 = _export("minimal_run.jsonl")
        # export_hash excludes created_at so must be identical
        assert export1.export_hash == export2.export_hash

    def test_different_traces_different_hash(self):
        e1 = _export("minimal_run.jsonl")
        e2 = _export("run_with_tool.jsonl")
        assert e1.export_hash != e2.export_hash


# ── Format ────────────────────────────────────────────────────────────────────


class TestFormats:
    def test_openinference_format_adds_oi_attrs(self):
        from agent_runtime_cockpit.observability import ObservabilityExportConfig
        from agent_runtime_cockpit.observability.exporters import export_trace

        export = export_trace(
            str(FIXTURES / "run_with_tool.jsonl"),
            cfg=ObservabilityExportConfig(format="openinference-json"),
        )
        assert export.format == "openinference-json"
        # At least one span should have openinference.span.kind
        oi_spans = [s for s in export.spans if "openinference.span.kind" in s.attributes]
        assert len(oi_spans) > 0

    def test_arc_otel_format_works(self):
        from agent_runtime_cockpit.observability import ObservabilityExportConfig
        from agent_runtime_cockpit.observability.exporters import export_trace

        export = export_trace(
            str(FIXTURES / "minimal_run.jsonl"),
            cfg=ObservabilityExportConfig(format="arc-otel-json"),
        )
        assert export.format == "arc-otel-json"

    def test_json_serializable(self):
        export = _export("minimal_run.jsonl")
        data = json.loads(export.model_dump_json())
        assert "spans" in data
        assert "export_hash" in data


# ── Validation ────────────────────────────────────────────────────────────────


class TestValidation:
    def test_valid_export_passes(self):
        from agent_runtime_cockpit.observability.validation import validate_export

        export = _export("minimal_run.jsonl")
        report = validate_export(export)
        assert report.ok

    def test_invalid_format_fails(self):
        from agent_runtime_cockpit.observability.models import ArcTraceExport
        from agent_runtime_cockpit.observability.validation import validate_export

        export = ArcTraceExport(export_id="test", format="invalid-format")
        report = validate_export(export)
        assert not report.ok
        assert any("Unknown format" in e for e in report.errors)

    def test_corrupt_file_validation(self, tmp_path):
        from agent_runtime_cockpit.observability.validation import validate_export_file

        p = tmp_path / "bad.json"
        p.write_text("not valid json")
        report = validate_export_file(str(p))
        assert not report.ok

    def test_missing_export_id_fails(self):
        from agent_runtime_cockpit.observability.models import ArcTraceExport
        from agent_runtime_cockpit.observability.validation import validate_export

        export = ArcTraceExport(export_id="", format="openinference-json")
        report = validate_export(export)
        assert not report.ok


# ── Source mutation guard ─────────────────────────────────────────────────────


class TestSourceMutation:
    def test_source_file_not_mutated(self):
        fixture = FIXTURES / "minimal_run.jsonl"
        original = fixture.read_text()
        _export("minimal_run.jsonl")
        assert fixture.read_text() == original

    def test_output_written_to_out_path(self, tmp_path):
        from agent_runtime_cockpit.observability import ObservabilityExportConfig
        from agent_runtime_cockpit.observability.exporters import export_trace

        out = str(tmp_path / "export.json")
        export_trace(str(FIXTURES / "minimal_run.jsonl"), cfg=ObservabilityExportConfig(), out=out)
        assert Path(out).exists()
        data = json.loads(Path(out).read_text())
        assert data["export_id"]


# ── Corrupt JSONL tolerance ───────────────────────────────────────────────────


class TestCorruptTolerance:
    def test_corrupt_line_skipped_with_warning(self):
        export = _export("corrupt_run.jsonl")
        warning_codes = [w.code for w in export.warnings]
        assert "corrupt_lines_skipped" in warning_codes

    def test_valid_events_still_exported(self):
        export = _export("corrupt_run.jsonl")
        root = next((s for s in export.spans if s.name == "arc.run"), None)
        assert root is not None


# ── Safety tests ─────────────────────────────────────────────────────────────


class TestSafety:
    """Structural safety: no network/process primitives in the observability package."""

    _FORBIDDEN = [
        r"\bsubprocess\b",
        r"\bsocket\b",
        r"\baiohttp\b",
        r"\brequests\b",
        r"\bhttpx\b",
        r"\bos\.system\b",
        r"\bPopen\b",
        r"\burlopen\b",
        r"\blisten\(",
        r"\bserve\(",
    ]
    _SRC = Path(__file__).parent.parent.parent / "src" / "agent_runtime_cockpit" / "observability"

    @pytest.mark.parametrize("pattern", _FORBIDDEN)
    def test_no_forbidden_primitive(self, pattern):
        compiled = re.compile(pattern)
        violations = []
        for f in self._SRC.glob("**/*.py"):
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if line.strip().startswith("#"):
                    continue
                if compiled.search(line):
                    violations.append(f"{f.name}:{i}: {line.rstrip()}")
        assert not violations, f"Forbidden {pattern!r}:\n" + "\n".join(violations)

    def test_export_trace_is_local_only(self):
        """export_trace must not open any network connection."""
        from agent_runtime_cockpit.observability.exporters import export_trace
        import inspect

        src = inspect.getsource(export_trace)
        for term in ("http://", "https://", "grpc://", "socket."):
            assert term not in src, f"Network term {term!r} found in export_trace"
