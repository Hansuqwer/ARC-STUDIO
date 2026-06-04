"""Tests for gen_ai.* semconv conformance in OTel mapping.

Every span must have required gen_ai.* attributes.
Prompt/completion content must NEVER appear by default.
"""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _export_spans(fixture: str = "minimal_run.jsonl"):
    from agent_runtime_cockpit.observability import ObservabilityExportConfig, export_trace

    export = export_trace(
        str(FIXTURES / fixture),
        cfg=ObservabilityExportConfig(format="openinference-json"),
    )
    return export.spans


def _export_spans_with_model():
    """Export from a trace that includes an llm.request event."""
    from agent_runtime_cockpit.observability import ObservabilityExportConfig
    from agent_runtime_cockpit.observability.loaders import LoadedTrace
    from agent_runtime_cockpit.observability.otel_mapping import map_events_to_spans

    trace = LoadedTrace(
        run_id="test-genai-001",
        runtime="test-agent",
        workflow_id="wf-check",
        status="completed",
        started_at="2025-01-01T00:00:00Z",
        ended_at="2025-01-01T00:01:00Z",
        events=[
            {
                "type": "llm.request",
                "run_id": "test-genai-001",
                "sequence": 1,
                "timestamp": "2025-01-01T00:00:10Z",
                "data": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "finish_reasons": ["stop"],
                },
            },
            {
                "type": "tool_call",
                "run_id": "test-genai-001",
                "sequence": 2,
                "timestamp": "2025-01-01T00:00:20Z",
                "data": {
                    "tool_name": "read_file",
                    "description": "Read a file from workspace",
                },
            },
        ],
        source_file="<synthetic>",
    )
    cfg = ObservabilityExportConfig(format="openinference-json")
    spans, _, _ = map_events_to_spans(trace, cfg)
    return spans


class TestGenAiSemconvRoot:
    def test_root_has_agent_name(self):
        spans = _export_spans()
        root = next(s for s in spans if s.name == "arc.run")
        assert "gen_ai.agent.name" in root.attributes

    def test_root_has_agent_description(self):
        spans = _export_spans()
        root = next(s for s in spans if s.name == "arc.run")
        assert "gen_ai.agent.description" in root.attributes


class TestGenAiSemconvModel:
    def test_model_span_has_system(self):
        spans = _export_spans_with_model()
        model = next(s for s in spans if s.name == "arc.model.call")
        assert model.attributes["gen_ai.system"] == "openai"

    def test_model_span_has_request_model(self):
        spans = _export_spans_with_model()
        model = next(s for s in spans if s.name == "arc.model.call")
        assert model.attributes["gen_ai.request.model"] == "gpt-4"

    def test_model_span_has_input_tokens(self):
        spans = _export_spans_with_model()
        model = next(s for s in spans if s.name == "arc.model.call")
        assert model.attributes["gen_ai.usage.input_tokens"] == 100

    def test_model_span_has_output_tokens(self):
        spans = _export_spans_with_model()
        model = next(s for s in spans if s.name == "arc.model.call")
        assert model.attributes["gen_ai.usage.output_tokens"] == 50

    def test_model_span_has_finish_reasons(self):
        spans = _export_spans_with_model()
        model = next(s for s in spans if s.name == "arc.model.call")
        assert model.attributes["gen_ai.response.finish_reasons"] == ["stop"]


class TestGenAiSemconvTool:
    def test_tool_span_has_name(self):
        spans = _export_spans_with_model()
        tool = next(s for s in spans if s.name == "arc.tool.call")
        assert tool.attributes["gen_ai.tool.name"] == "read_file"

    def test_tool_span_has_description(self):
        spans = _export_spans_with_model()
        tool = next(s for s in spans if s.name == "arc.tool.call")
        assert tool.attributes["gen_ai.tool.description"] == "Read a file from workspace"


class TestNoContentLogged:
    """Prompt/completion content must NEVER be in spans by default."""

    def test_no_prompt_content(self):
        spans = _export_spans_with_model()
        for span in spans:
            assert "gen_ai.prompt" not in span.attributes
            assert "gen_ai.request.messages" not in span.attributes

    def test_no_completion_content(self):
        spans = _export_spans_with_model()
        for span in spans:
            assert "gen_ai.completion" not in span.attributes
            assert "gen_ai.response.messages" not in span.attributes


class TestSemconvCheck:
    def test_compliant_spans_pass(self):
        from agent_runtime_cockpit.observability.otel_mapping import check_genai_semconv

        spans = _export_spans_with_model()
        violations = check_genai_semconv(spans)
        assert violations == []

    def test_missing_attr_detected(self):
        from agent_runtime_cockpit.observability.otel_mapping import check_genai_semconv
        from agent_runtime_cockpit.observability.models import ArcSpan

        bad_span = ArcSpan(
            trace_id="a" * 32,
            span_id="b" * 16,
            name="arc.model.call",
            attributes={"gen_ai.system": "openai"},  # missing others
        )
        violations = check_genai_semconv([bad_span])
        assert len(violations) == 1
        assert "gen_ai.request.model" in violations[0]["missing"]

    def test_forbidden_content_detected(self):
        from agent_runtime_cockpit.observability.otel_mapping import check_genai_semconv
        from agent_runtime_cockpit.observability.models import ArcSpan

        bad_span = ArcSpan(
            trace_id="a" * 32,
            span_id="b" * 16,
            name="arc.model.call",
            attributes={
                "gen_ai.system": "openai",
                "gen_ai.request.model": "gpt-4",
                "gen_ai.usage.input_tokens": 10,
                "gen_ai.usage.output_tokens": 5,
                "gen_ai.response.finish_reasons": ["stop"],
                "gen_ai.prompt": "SECRET CONTENT",  # forbidden
            },
        )
        violations = check_genai_semconv([bad_span])
        assert len(violations) == 1
        assert "gen_ai.prompt" in violations[0]["forbidden"]
