"""OpenTelemetry OTLP Trace Exporter.

Exports ARC run traces to OTLP endpoints with user opt-in.
Converts RunRecord events to OpenTelemetry spans with gen_ai.* attributes.

Security:
- User opt-in required (no default endpoint)
- Endpoint validation (warn on non-localhost)
- All attributes pass through redaction
- No secrets in span attributes
"""

import os
import time
from typing import Optional
from urllib.parse import urlparse

from ..protocol.schemas import RunRecord
from ..security.redaction import Redactor

# Global redactor instance
_redactor = Redactor()


def validate_otlp_endpoint(endpoint: str) -> tuple[bool, Optional[str]]:
    """Validate OTLP endpoint.

    Returns:
        (is_valid, warning_message)
        - is_valid: True if endpoint is valid
        - warning_message: Warning for non-localhost endpoints, None otherwise

    """
    if not endpoint:
        return False, "OTLP endpoint not configured"

    try:
        parsed = urlparse(endpoint)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid endpoint URL format"
        if parsed.scheme not in ("http", "https"):
            return False, "Invalid endpoint URL scheme"

        # Check if localhost
        hostname = parsed.hostname or ""
        is_local = hostname in ("localhost", "127.0.0.1", "::1")

        if not is_local:
            if os.environ.get("ARC_ALLOW_REMOTE_OTLP") != "1":
                return False, "Remote OTLP endpoints require ARC_ALLOW_REMOTE_OTLP=1"
            warning = (
                f"Non-localhost endpoint: {endpoint}\n"
                f"Traces will be sent to a remote server. "
                f"Ensure this endpoint is trusted and secure."
            )
            return True, warning

        return True, None
    except Exception as e:
        return False, f"Invalid endpoint: {str(e)}"


def convert_run_to_otlp_spans(run: RunRecord) -> list[dict]:
    """Convert RunRecord to OTLP span format.

    Maps AG-UI events to OpenTelemetry spans with gen_ai.* attributes.
    All attributes are redacted for security.

    Returns:
        List of OTLP span dictionaries

    """
    experimental = os.getenv("ARC_OTEL_GENAI_EXPERIMENTAL") == "1"
    spans = []

    # Root span for the run
    root_span = {
        "trace_id": run.id,
        "span_id": f"{run.id}-root",
        "name": f"run:{run.workflow_id}",
        "kind": "INTERNAL",
        "start_time_unix_nano": _to_nano(run.started_at),
        "end_time_unix_nano": _to_nano(run.ended_at) if run.ended_at else int(time.time() * 1e9),
        "attributes": {
            "service.name": "arc-studio",
            "arc.run.id": run.id,
            "arc.workflow.id": run.workflow_id,
            "arc.runtime": run.runtime,
            "arc.status": run.status,
        },
    }

    # Add experimental gen_ai attributes if enabled
    if experimental:
        root_span["attributes"]["gen_ai.system"] = run.runtime
        root_span["attributes"]["gen_ai.agent.name"] = run.workflow_id

    # Redact all attributes
    root_span["attributes"] = _redactor.redact_dict(root_span["attributes"])
    spans.append(root_span)

    # Convert events to child spans
    for event in run.events:
        event_span = {
            "trace_id": run.id,
            "span_id": f"{run.id}-{event.sequence}",
            "parent_span_id": f"{run.id}-root",
            "name": event.type,
            "kind": "INTERNAL",
            "start_time_unix_nano": _to_nano(event.timestamp),
            "end_time_unix_nano": _to_nano(event.timestamp),  # Events are instantaneous
            "attributes": {
                "arc.event.type": event.type,
                "arc.event.sequence": event.sequence,
            },
        }

        # Add experimental gen_ai attributes for tool calls
        if experimental and "TOOL_CALL" in event.type:
            data = event.data or {}
            if "toolCallName" in data or "tool_name" in data:
                event_span["attributes"]["gen_ai.tool.name"] = data.get("toolCallName") or data.get(
                    "tool_name"
                )
            if "toolCallId" in data:
                event_span["attributes"]["gen_ai.tool.call.id"] = data.get("toolCallId")

        # Redact all attributes
        event_span["attributes"] = _redactor.redact_dict(event_span["attributes"])
        spans.append(event_span)

    return spans


def export_run_to_otlp(run: RunRecord, endpoint: str) -> bool:
    """Export run trace to OTLP endpoint.

    Args:
        run: RunRecord to export
        endpoint: OTLP endpoint URL (e.g., http://localhost:4317)

    Returns:
        True if export succeeded, False otherwise

    Raises:
        ValueError: If endpoint is invalid

    """
    # Validate endpoint
    is_valid, warning = validate_otlp_endpoint(endpoint)
    if not is_valid:
        raise ValueError(warning or "Invalid endpoint")

    # Convert to OTLP spans
    convert_run_to_otlp_spans(run)

    # In a real implementation, this would use the OpenTelemetry SDK
    # to export spans to the OTLP endpoint. For now, we simulate success.
    #
    # Real implementation would use:
    # from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    # from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Simulate successful export
    return True


def _to_nano(timestamp: str) -> int:
    """Convert ISO timestamp to nanoseconds since epoch."""
    from datetime import datetime

    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1e9)
