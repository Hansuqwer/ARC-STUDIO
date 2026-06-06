"""R-03 / B-OTel: semconv 1.41.1 alignment tests.

gen_ai.operation.name (Required), gen_ai.provider.name (Required),
gen_ai.usage.reasoning.output_tokens (Recommended), error.type on failure.
"""

from __future__ import annotations

from agent_runtime_cockpit.observability.loaders import LoadedTrace
from agent_runtime_cockpit.observability.models import ObservabilityExportConfig
from agent_runtime_cockpit.observability.otel_mapping import (
    GENAI_REQUIRED_MODEL,
    map_events_to_spans,
)


def _model_call_event(usage: dict, provider: str = "openai") -> dict:
    return {
        "type": "llm.request",
        "run_id": "r-semconv-test",
        "sequence": 1,
        "data": {"provider": provider, "model": "gpt-4o", "usage": usage},
    }


def _run_failed_event() -> dict:
    return {
        "type": "run.failed",
        "run_id": "r-fail-test",
        "sequence": 99,
        "data": {"status": "failed", "error_type": "ProviderError"},
    }


def _spans(events: list[dict]) -> tuple[dict, list]:
    """Return (root_attrs, [model_span, ...])."""
    trace = LoadedTrace(
        run_id="r-semconv-test",
        runtime="test",
        workflow_id="wf-1",
        status="completed",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:01:00Z",
        events=events,
    )
    cfg = ObservabilityExportConfig()
    spans, _w, _c = map_events_to_spans(trace, cfg)
    root_attrs = next(s.attributes for s in spans if s.name == "arc.run")
    model_attrs = [s.attributes for s in spans if "model" in s.name]
    return root_attrs, model_attrs


# ── gen_ai.operation.name (Required) ──────────────────────────────────────────


def test_operation_name_is_chat():
    _, model = _spans([_model_call_event({"input_tokens": 10, "output_tokens": 5})])
    assert model and model[0]["gen_ai.operation.name"] == "chat"


def test_operation_name_in_required_tuple():
    assert "gen_ai.operation.name" in GENAI_REQUIRED_MODEL


# ── gen_ai.provider.name (Required, new discriminator) ────────────────────────


def test_provider_name_emitted():
    _, model = _spans([_model_call_event({"input_tokens": 10, "output_tokens": 5}, "anthropic")])
    assert model and model[0]["gen_ai.provider.name"] == "anthropic"


def test_provider_name_equals_system_for_back_compat():
    """gen_ai.provider.name and gen_ai.system must have the same value."""
    _, model = _spans([_model_call_event({"input_tokens": 10, "output_tokens": 5}, "openai")])
    assert model and model[0]["gen_ai.provider.name"] == model[0]["gen_ai.system"]


def test_provider_name_in_required_tuple():
    assert "gen_ai.provider.name" in GENAI_REQUIRED_MODEL


# ── gen_ai.usage.reasoning.output_tokens (Recommended) ───────────────────────


def test_reasoning_tokens_from_reasoning_output_tokens_field():
    _, model = _spans(
        [
            _model_call_event(
                {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "reasoning_output_tokens": 50,
                }
            )
        ]
    )
    assert model and model[0]["gen_ai.usage.reasoning.output_tokens"] == 50


def test_reasoning_tokens_from_reasoning_alias():
    """Accepts 'reasoning' as an alias for 'reasoning_output_tokens'."""
    _, model = _spans(
        [
            _model_call_event(
                {
                    "input_tokens": 100,
                    "output_tokens": 200,
                    "reasoning": 30,
                }
            )
        ]
    )
    assert model and model[0]["gen_ai.usage.reasoning.output_tokens"] == 30


def test_reasoning_tokens_defaults_to_zero():
    """When not present, reasoning tokens defaults to 0 (not omitted)."""
    _, model = _spans([_model_call_event({"input_tokens": 10, "output_tokens": 5})])
    assert model and model[0]["gen_ai.usage.reasoning.output_tokens"] == 0


# ── error.type (Conditionally Required on failure) ───────────────────────────


def test_error_type_on_failed_run():
    trace = LoadedTrace(
        run_id="r-fail-test",
        runtime="test",
        workflow_id="wf-1",
        status="failed",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:01:00Z",
        events=[_run_failed_event()],
    )
    cfg = ObservabilityExportConfig()
    spans, _, _ = map_events_to_spans(trace, cfg)
    root = next(s for s in spans if s.name == "arc.run")
    assert root.status == "ERROR"
    assert "error.type" in root.attributes
    assert root.attributes["error.type"] == "ProviderError"


def test_no_error_type_on_success():
    trace = LoadedTrace(
        run_id="r-ok-test",
        runtime="test",
        workflow_id="wf-1",
        status="completed",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:01:00Z",
        events=[
            {
                "type": "run.completed",
                "run_id": "r-ok-test",
                "sequence": 99,
                "data": {"status": "completed"},
            }
        ],
    )
    cfg = ObservabilityExportConfig()
    spans, _, _ = map_events_to_spans(trace, cfg)
    root = next(s for s in spans if s.name == "arc.run")
    assert root.status == "OK"
    assert "error.type" not in root.attributes


def test_error_type_fallback_to_other_when_no_error_type_field():
    """If error_type is absent, fall back to status string or '_OTHER'."""
    trace = LoadedTrace(
        run_id="r-fail2-test",
        runtime="test",
        workflow_id="wf-1",
        status="failed",
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:01:00Z",
        events=[
            {
                "type": "run.failed",
                "run_id": "r-fail2-test",
                "sequence": 99,
                "data": {"status": "failed"},  # no error_type key
            }
        ],
    )
    cfg = ObservabilityExportConfig()
    spans, _, _ = map_events_to_spans(trace, cfg)
    root = next(s for s in spans if s.name == "arc.run")
    assert "error.type" in root.attributes
    assert root.attributes["error.type"]  # non-empty
