"""R-03: OTel cache field surface tests."""

from __future__ import annotations

from agent_runtime_cockpit.observability.loaders import LoadedTrace
from agent_runtime_cockpit.observability.models import ObservabilityExportConfig
from agent_runtime_cockpit.observability.otel_mapping import (
    GENAI_REQUIRED_MODEL,
    map_events_to_spans,
)


def _model_call_event(usage: dict) -> dict:
    return {
        "type": "llm.request",
        "run_id": "r-cache-test",
        "sequence": 1,
        "data": {"provider": "anthropic", "model": "claude-3-haiku", "usage": usage},
    }


def _span_attrs(usage: dict) -> dict:
    trace = LoadedTrace(
        run_id="r-cache-test",
        runtime="test",
        workflow_id="wf-1",
        status="completed",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:01:00Z",
        events=[_model_call_event(usage)],
    )
    cfg = ObservabilityExportConfig()
    spans, _warnings, _count = map_events_to_spans(trace, cfg)
    model_spans = [s for s in spans if "model" in s.name]
    assert model_spans, f"no model span; all: {[s.name for s in spans]}"
    return model_spans[0].attributes


def test_cache_read_attr_set_when_present() -> None:
    attrs = _span_attrs({"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 42})
    assert attrs["gen_ai.usage.cache_read_input_tokens"] == 42


def test_cache_attrs_default_to_zero_when_absent() -> None:
    attrs = _span_attrs({"input_tokens": 100, "output_tokens": 50})
    assert attrs["gen_ai.usage.cache_read_input_tokens"] == 0
    assert attrs["gen_ai.usage.cache_creation_input_tokens"] == 0


def test_genai_required_model_includes_cache_fields() -> None:
    assert "gen_ai.usage.cache_read_input_tokens" in GENAI_REQUIRED_MODEL
    assert "gen_ai.usage.cache_creation_input_tokens" in GENAI_REQUIRED_MODEL


def test_dotted_form_attr_names_emitted() -> None:
    """Dotted-form spec-aligned attr names emitted alongside underscored form."""
    attrs = _span_attrs({"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 42})
    assert attrs["gen_ai.usage.cache_read.input_tokens"] == 42
    assert attrs["gen_ai.usage.cache_creation.input_tokens"] == 0


def test_anthropic_input_tokens_includes_cached_per_spec() -> None:
    """gen_ai.usage.input_tokens = raw + cache_read + cache_creation per spec."""
    attrs = _span_attrs(
        {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 30,
            "cache_creation_input_tokens": 20,
        }
    )
    assert attrs["gen_ai.usage.input_tokens"] == 150  # 100 + 30 + 20
