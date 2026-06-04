"""Map ARC trace events to OpenTelemetry-style ArcSpan objects.

ARC event type → span/event mapping:
  run              → root span (arc.run)
  ir.compiled      → span event on root (arc.ir.graph)
  tool_call        → child span (arc.tool.call)
  mcp_tool_call    → child span (arc.mcp.tool)
  model_call       → child span (arc.model.call)
  policy.evaluated → span events on root (arc.policy.evaluate)
  hitl.*           → span event (arc.hitl.gate)
  consensus.*      → span event (arc.consensus.select)
  eval.*           → span event (arc.eval.recommend)
  <unknown>        → opaque span event (arc.opaque.event)

No execution, no network.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from .models import ArcSpan, ArcSpanEvent, ExportWarning, ObservabilityExportConfig
from .redaction import redact_attributes

log = logging.getLogger(__name__)


# Deterministic IDs derived from run_id + sequence
def _span_id(run_id: str, suffix: str) -> str:
    raw = f"{run_id}:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _trace_id(run_id: str) -> str:
    return hashlib.sha256(f"trace:{run_id}".encode()).hexdigest()[:32]


def _safe_attrs(data: dict[str, Any], redact: bool) -> dict[str, Any]:
    if not redact:
        return dict(data)
    result, _ = redact_attributes(data)
    return result


def _event_to_span_event(
    event: dict[str, Any], cfg: ObservabilityExportConfig
) -> tuple[Optional[ArcSpanEvent], int]:
    """Convert an ARC RunEvent dict to an ArcSpanEvent. Returns (event, tokens_redacted)."""
    etype = event.get("type", "unknown")
    attrs: dict[str, Any] = {
        "arc.event.type": etype,
        "arc.run.id": event.get("run_id", ""),
        "arc.event.sequence": event.get("sequence", 0),
    }
    tokens = 0
    if cfg.include_payloads:
        data = event.get("data") or {}
        if cfg.redact_secrets:
            data, tokens = redact_attributes(data)
        attrs["arc.event.data"] = data
    return ArcSpanEvent(
        name=f"arc.{etype.lower().replace('.', '_').replace('/', '_')}",
        timestamp=event.get("timestamp"),
        attributes=attrs,
    ), tokens


# ── Known event type handlers ─────────────────────────────────────────────────


def _handle_run_start(event: dict, root: ArcSpan, cfg: ObservabilityExportConfig) -> int:
    data = event.get("data") or {}
    root.start_time = event.get("timestamp")
    attrs: dict[str, Any] = {
        "arc.run.id": event.get("run_id", ""),
        "arc.runtime.name": data.get("runtime", ""),
        "arc.runtime.adapter": data.get("adapter", ""),
    }
    if cfg.redact_secrets:
        attrs, _ = redact_attributes(attrs)
    root.attributes.update(attrs)
    return 0


def _handle_run_end(event: dict, root: ArcSpan, cfg: ObservabilityExportConfig) -> int:
    root.end_time = event.get("timestamp")
    data = event.get("data") or {}
    status = data.get("status", "")
    root.status = "ERROR" if "fail" in status.lower() else "OK"
    return 0


def _handle_tool_call(
    event: dict, root: ArcSpan, spans: list[ArcSpan], cfg: ObservabilityExportConfig
) -> int:
    data = event.get("data") or {}
    run_id = event.get("run_id", "")
    seq = str(event.get("sequence", 0))
    sid = _span_id(run_id, f"tool:{seq}")
    tokens = 0
    tool_name = data.get("tool_name", data.get("name", ""))
    attrs: dict[str, Any] = {
        "arc.tool.name": tool_name,
        "arc.tool.can_write": data.get("can_write", False),
        "arc.tool.can_network": data.get("can_network", False),
        "arc.tool.can_read_secrets": False,  # never expose
        # OpenTelemetry GenAI semantic conventions
        "gen_ai.tool.name": tool_name,
        "gen_ai.tool.description": data.get("description", ""),
    }
    if cfg.redact_secrets:
        attrs, tokens = redact_attributes(attrs)
    spans.append(
        ArcSpan(
            trace_id=root.trace_id,
            span_id=sid,
            parent_span_id=root.span_id,
            name="arc.tool.call",
            start_time=event.get("timestamp"),
            end_time=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return tokens


def _handle_mcp_tool(
    event: dict, root: ArcSpan, spans: list[ArcSpan], cfg: ObservabilityExportConfig
) -> int:
    if not cfg.include_mcp:
        return 0
    data = event.get("data") or {}
    run_id = event.get("run_id", "")
    seq = str(event.get("sequence", 0))
    sid = _span_id(run_id, f"mcp:{seq}")
    tokens = 0
    attrs: dict[str, Any] = {
        "arc.mcp.server_id": data.get("server_id", ""),
        "arc.mcp.tool_name": data.get("tool_name", ""),
        "arc.mcp.manifest_hash": data.get("manifest_hash", ""),
        "arc.mcp.drifted": data.get("drifted", False),
    }
    if cfg.redact_secrets:
        attrs, tokens = redact_attributes(attrs)
    spans.append(
        ArcSpan(
            trace_id=root.trace_id,
            span_id=sid,
            parent_span_id=root.span_id,
            name="arc.mcp.tool",
            start_time=event.get("timestamp"),
            end_time=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return tokens


def _handle_model_call(
    event: dict, root: ArcSpan, spans: list[ArcSpan], cfg: ObservabilityExportConfig
) -> int:
    data = event.get("data") or {}
    run_id = event.get("run_id", "")
    seq = str(event.get("sequence", 0))
    sid = _span_id(run_id, f"model:{seq}")
    tokens = 0
    usage = data.get("usage") or {}
    finish_reasons = data.get("finish_reasons") or data.get("finish_reason")
    if isinstance(finish_reasons, str):
        finish_reasons = [finish_reasons]
    attrs: dict[str, Any] = {
        "arc.model.provider": data.get("provider", ""),
        "arc.model.name": data.get("model", ""),
        "arc.cost.requires_paid_calls": data.get("paid", False),
        # OpenTelemetry GenAI semantic conventions
        "gen_ai.system": data.get("provider", ""),
        "gen_ai.request.model": data.get("model", ""),
        "gen_ai.usage.input_tokens": usage.get("input_tokens", usage.get("prompt_tokens", 0)),
        "gen_ai.usage.output_tokens": usage.get("output_tokens", usage.get("completion_tokens", 0)),
        "gen_ai.usage.cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
        "gen_ai.usage.cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
        "gen_ai.response.finish_reasons": finish_reasons or ["stop"],
    }
    # NEVER log prompt/completion content by default (semconv compliance)
    # gen_ai.request.* content and gen_ai.completion.* content are excluded.
    if cfg.redact_secrets:
        attrs, tokens = redact_attributes(attrs)
    spans.append(
        ArcSpan(
            trace_id=root.trace_id,
            span_id=sid,
            parent_span_id=root.span_id,
            name="arc.model.call",
            kind="CLIENT",
            start_time=event.get("timestamp"),
            end_time=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return tokens


def _handle_hitl(event: dict, root: ArcSpan, cfg: ObservabilityExportConfig) -> int:
    data = event.get("data") or {}
    attrs: dict[str, Any] = {
        "arc.hitl.required": True,
        "arc.hitl.gate_id": data.get("gate_id", ""),
        "arc.hitl.blocking": data.get("blocking", True),
    }
    if cfg.redact_secrets:
        attrs, _ = redact_attributes(attrs)
    root.events.append(
        ArcSpanEvent(
            name="arc.hitl.gate",
            timestamp=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return 0


def _handle_consensus(event: dict, root: ArcSpan, cfg: ObservabilityExportConfig) -> int:
    data = event.get("data") or {}
    attrs: dict[str, Any] = {
        "arc.consensus.protocol": data.get("protocol", ""),
        "arc.consensus.risk_level": data.get("risk", ""),
    }
    if cfg.redact_secrets:
        attrs, _ = redact_attributes(attrs)
    root.events.append(
        ArcSpanEvent(
            name="arc.consensus.select",
            timestamp=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return 0


def _handle_policy(event: dict, root: ArcSpan, cfg: ObservabilityExportConfig) -> int:
    if not cfg.include_policy:
        return 0
    data = event.get("data") or {}
    attrs: dict[str, Any] = {
        "arc.policy.can_run": data.get("can_run", True),
        "arc.policy.risk_level": data.get("risk_level", "low"),
        "arc.policy.issue_count": data.get("issue_count", 0),
    }
    if cfg.redact_secrets:
        attrs, _ = redact_attributes(attrs)
    root.events.append(
        ArcSpanEvent(
            name="arc.policy.evaluate",
            timestamp=event.get("timestamp"),
            attributes=attrs,
        )
    )
    return 0


# ── Public API ────────────────────────────────────────────────────────────────


_EVENT_TYPE_MAP = {
    "run.started": "run_start",
    "run.completed": "run_end",
    "run.failed": "run_end",
    "run.cancelled": "run_end",
    "tool_call": "tool_call",
    "tool_call.result": "tool_call",
    "mcp.tool.call": "mcp_tool",
    "mcp.tool.result": "mcp_tool",
    "llm.request": "model_call",
    "llm.response": "model_call",
    "hitl.prompt": "hitl",
    "hitl.response": "hitl",
    "consensus.selected": "consensus",
    "policy.evaluated": "policy",
}


def map_events_to_spans(
    trace: "LoadedTrace",  # noqa: F821
    cfg: ObservabilityExportConfig,
) -> tuple[list[ArcSpan], list[ExportWarning], int]:
    """Map a LoadedTrace to a flat list of ArcSpans.

    Returns (spans, warnings, total_tokens_redacted).
    """

    run_id = trace.run_id or "unknown"
    tid = _trace_id(run_id)
    root_sid = _span_id(run_id, "root")

    root = ArcSpan(
        trace_id=tid,
        span_id=root_sid,
        name="arc.run",
        kind="SERVER",
        attributes={
            "arc.run.id": run_id,
            "arc.runtime.name": trace.runtime or "",
            "arc.workflow_id": trace.workflow_id or "",
            "arc.run.status": trace.status or "",
            # OpenTelemetry GenAI semantic conventions — agent
            "gen_ai.agent.name": trace.runtime or "",
            "gen_ai.agent.description": trace.workflow_id or "",
        },
        start_time=trace.started_at,
        end_time=trace.ended_at,
        status="OK",
    )

    child_spans: list[ArcSpan] = []
    warnings: list[ExportWarning] = []
    total_tokens = 0

    for event in trace.events:
        etype = (event.get("type") or "").lower()
        handler = _EVENT_TYPE_MAP.get(etype)

        try:
            if handler == "run_start":
                total_tokens += _handle_run_start(event, root, cfg)
            elif handler == "run_end":
                total_tokens += _handle_run_end(event, root, cfg)
            elif handler == "tool_call":
                total_tokens += _handle_tool_call(event, root, child_spans, cfg)
            elif handler == "mcp_tool":
                total_tokens += _handle_mcp_tool(event, root, child_spans, cfg)
            elif handler == "model_call":
                total_tokens += _handle_model_call(event, root, child_spans, cfg)
            elif handler == "hitl":
                total_tokens += _handle_hitl(event, root, cfg)
            elif handler == "consensus":
                total_tokens += _handle_consensus(event, root, cfg)
            elif handler == "policy":
                total_tokens += _handle_policy(event, root, cfg)
            else:
                # Opaque span event — preserve unknown types
                span_event, tokens = _event_to_span_event(event, cfg)
                if span_event:
                    root.events.append(span_event)
                total_tokens += tokens
        except Exception as exc:
            warnings.append(
                ExportWarning(
                    code="event_mapping_error",
                    message=f"Failed to map event type={etype!r}: {exc}",
                    span_id=root_sid,
                )
            )

    return [root] + child_spans, warnings, total_tokens


# ── Semconv conformance check ─────────────────────────────────────────────────

# Required gen_ai.* attributes per span type
GENAI_REQUIRED_ROOT = ("gen_ai.agent.name", "gen_ai.agent.description")
GENAI_REQUIRED_MODEL = (
    "gen_ai.system",
    "gen_ai.request.model",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.cache_read_input_tokens",
    "gen_ai.usage.cache_creation_input_tokens",
    "gen_ai.response.finish_reasons",
)
GENAI_REQUIRED_TOOL = ("gen_ai.tool.name", "gen_ai.tool.description")

# Content attributes that must NEVER be present by default
GENAI_CONTENT_FORBIDDEN = (
    "gen_ai.prompt",
    "gen_ai.completion",
    "gen_ai.request.messages",
    "gen_ai.response.messages",
)


def check_genai_semconv(spans: list[ArcSpan]) -> list[dict[str, Any]]:
    """Check spans for gen_ai.* semconv conformance.

    Returns list of violations: [{"span_id", "span_name", "missing", "forbidden"}]
    """
    violations: list[dict[str, Any]] = []
    for span in spans:
        missing: list[str] = []
        forbidden: list[str] = []

        if span.name == "arc.run":
            for attr in GENAI_REQUIRED_ROOT:
                if attr not in span.attributes:
                    missing.append(attr)
        elif span.name == "arc.model.call":
            for attr in GENAI_REQUIRED_MODEL:
                if attr not in span.attributes:
                    missing.append(attr)
        elif span.name == "arc.tool.call":
            for attr in GENAI_REQUIRED_TOOL:
                if attr not in span.attributes:
                    missing.append(attr)

        # Check forbidden content attributes on all spans
        for attr in GENAI_CONTENT_FORBIDDEN:
            if attr in span.attributes:
                forbidden.append(attr)

        if missing or forbidden:
            violations.append(
                {
                    "span_id": span.span_id,
                    "span_name": span.name,
                    "missing": missing,
                    "forbidden": forbidden,
                }
            )
    return violations
