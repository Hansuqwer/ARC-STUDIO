"""OpenInference format mapping.

Wraps the OTel-style spans with OpenInference semantic conventions.
OpenInference is a superset of OTel for LLM tracing.
Ref: https://github.com/Arize-ai/openinference

The primary difference from arc-otel-json is top-level format metadata
and use of OpenInference attribute namespaces where they overlap.
"""

from __future__ import annotations

from .models import ArcSpan, ArcTraceExport

# OpenInference attribute mappings (supplement ARC attrs)
_OI_ATTR_MAP = {
    "arc.model.name": "llm.model_name",
    "arc.model.provider": "llm.provider",
    "arc.tool.name": "tool.name",
    "arc.mcp.tool_name": "tool.name",
    "arc.mcp.server_id": "tool.description",
    "gen_ai.request.model": "llm.model_name",
    "gen_ai.system": "llm.provider",
}


def add_openinference_attrs(span: ArcSpan) -> ArcSpan:
    """Add OpenInference semantic attribute aliases to a span (non-destructive)."""
    extra: dict = {}
    for arc_key, oi_key in _OI_ATTR_MAP.items():
        if arc_key in span.attributes and oi_key not in span.attributes:
            extra[oi_key] = span.attributes[arc_key]
    if extra:
        span = span.model_copy(update={"attributes": {**span.attributes, **extra}})

    # OpenInference span kind annotation
    kind_map = {
        "arc.model.call": "LLM",
        "arc.tool.call": "TOOL",
        "arc.mcp.tool": "TOOL",
        "arc.run": "CHAIN",
        "arc.ir.node": "CHAIN",
    }
    oi_kind = kind_map.get(span.name)
    if oi_kind and "openinference.span.kind" not in span.attributes:
        span = span.model_copy(
            update={"attributes": {**span.attributes, "openinference.span.kind": oi_kind}}
        )
    return span


def apply_openinference_format(export: ArcTraceExport) -> ArcTraceExport:
    """Apply OpenInference attribute conventions to all spans in the export."""
    new_spans = [add_openinference_attrs(s) for s in export.spans]
    return export.model_copy(update={"spans": new_spans, "format": "openinference-json"})
