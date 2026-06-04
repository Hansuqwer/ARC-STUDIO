"""OpenInference format mapping.

Wraps the OTel-style spans with OpenInference semantic conventions.
OpenInference is a superset of OTel for LLM tracing.
Ref: https://github.com/Arize-ai/openinference

The primary difference from arc-otel-json is top-level format metadata
and use of OpenInference attribute namespaces where they overlap.
"""

from __future__ import annotations

import re
from typing import Any, Optional

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


# ── MCP Context Propagator (W3C traceparent via JSON-RPC _meta) ───────────────

_TRACEPARENT_RE = re.compile(r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$")


class MCPContextPropagator:
    """Propagate W3C traceparent through MCP JSON-RPC _meta envelope.

    Forward-compatible with MCP 2026-07-28 spec draft.
    Injects traceparent into params._meta; extracts from the same location.
    Falls back gracefully when _meta is absent.
    """

    TRACEPARENT_KEY = "traceparent"

    def inject(
        self,
        trace_id: str,
        span_id: str,
        *,
        trace_flags: str = "01",
        version: str = "00",
        message: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Inject traceparent into a JSON-RPC request message.

        If message is None, returns a new message skeleton with _meta.
        """
        traceparent = f"{version}-{trace_id}-{span_id}-{trace_flags}"
        if message is None:
            message = {}
        params = message.setdefault("params", {})
        if not isinstance(params, dict):
            return message
        meta = params.setdefault("_meta", {})
        if not isinstance(meta, dict):
            params["_meta"] = {self.TRACEPARENT_KEY: traceparent}
        else:
            meta[self.TRACEPARENT_KEY] = traceparent
        return message

    def extract(self, message: dict[str, Any]) -> Optional[tuple[str, str, str, str]]:
        """Extract traceparent from JSON-RPC message _meta.

        Returns (version, trace_id, span_id, trace_flags) or None if absent/invalid.
        """
        params = message.get("params")
        if not isinstance(params, dict):
            return None
        meta = params.get("_meta")
        if not isinstance(meta, dict):
            return None
        tp = meta.get(self.TRACEPARENT_KEY)
        if not isinstance(tp, str):
            return None
        if not _TRACEPARENT_RE.match(tp):
            return None
        parts = tp.split("-")
        return (parts[0], parts[1], parts[2], parts[3])
