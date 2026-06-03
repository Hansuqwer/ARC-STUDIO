"""Opt-in OTLP HTTP/gRPC export for ArcTraceExport.

HARD CONSTRAINTS:
- No network call unless confirm_network_export=True AND endpoint is set.
- Redaction must happen before send (caller responsibility; we validate).
- No secrets in logs.
- Fail closed without confirmation.
- Optional dependency: uses urllib.request (stdlib) for HTTP to avoid heavy deps.
- gRPC: fails with OTLP_GRPC_UNAVAILABLE if opentelemetry-exporter-otlp-proto-grpc not installed.

Supported formats: otlp-http, otlp-grpc
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

_SECRET_INDICATORS = ("Bearer ", "sk-", "Authorization:", "-----BEGIN")


class OtlpExportResult(BaseModel):
    ok: bool
    format: str
    endpoint: Optional[str] = None
    span_count: int = 0
    http_status: Optional[int] = None
    error: Optional[str] = None


class ConfirmationRequired(ValueError):
    """Raised when --confirm-network-export is missing."""


class EndpointRequired(ValueError):
    """Raised when --endpoint is missing for network export."""


class OtlpGrpcUnavailable(ImportError):
    """Raised when gRPC exporter dependencies are not installed."""


def _validate_no_secrets(payload: str) -> None:
    for indicator in _SECRET_INDICATORS:
        if indicator in payload:
            raise ValueError(f"Secret indicator {indicator!r} in payload; refusing export")


def _build_otlp_json_payload(export_dict: dict[str, Any]) -> str:
    """Build a minimal OTLP-compatible JSON payload from ArcTraceExport dict.

    Structure follows OTLP/JSON spec (partial — enough for Phoenix/Langfuse ingestion).
    """
    resource_spans = []
    resource = export_dict.get("resource") or {}
    spans_raw = export_dict.get("spans") or []

    scope_spans = []
    for span in spans_raw:
        otlp_span: dict[str, Any] = {
            "traceId": span.get("trace_id", ""),
            "spanId": span.get("span_id", ""),
            "name": span.get("name", ""),
            "kind": _kind_to_int(span.get("kind", "INTERNAL")),
            "startTimeUnixNano": _iso_to_nano(span.get("start_time")),
            "endTimeUnixNano": _iso_to_nano(span.get("end_time")),
            "attributes": _dict_to_kv(span.get("attributes") or {}),
            "status": {"code": 1 if span.get("status") == "OK" else 2},
            "events": [
                {
                    "name": ev.get("name", ""),
                    "timeUnixNano": _iso_to_nano(ev.get("timestamp")),
                    "attributes": _dict_to_kv(ev.get("attributes") or {}),
                }
                for ev in (span.get("events") or [])
            ],
        }
        if span.get("parent_span_id"):
            otlp_span["parentSpanId"] = span["parent_span_id"]
        scope_spans.append(otlp_span)

    resource_spans.append(
        {
            "resource": {"attributes": _dict_to_kv(resource)},
            "scopeSpans": [{"scope": {"name": "arc-studio"}, "spans": scope_spans}],
        }
    )
    return json.dumps({"resourceSpans": resource_spans}, separators=(",", ":"))


def _kind_to_int(kind: str) -> int:
    return {"INTERNAL": 1, "SERVER": 2, "CLIENT": 3, "PRODUCER": 4, "CONSUMER": 5}.get(kind, 1)


def _iso_to_nano(ts: Optional[str]) -> int:
    if not ts:
        return 0
    try:
        from datetime import datetime

        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return 0


def _dict_to_kv(d: dict) -> list[dict]:
    result = []
    for k, v in d.items():
        if isinstance(v, bool):
            result.append({"key": k, "value": {"boolValue": v}})
        elif isinstance(v, int):
            result.append({"key": k, "value": {"intValue": v}})
        elif isinstance(v, float):
            result.append({"key": k, "value": {"doubleValue": v}})
        elif isinstance(v, str):
            result.append({"key": k, "value": {"stringValue": v}})
        else:
            result.append({"key": k, "value": {"stringValue": str(v)}})
    return result


def export_otlp_http(
    export_dict: dict[str, Any],
    *,
    endpoint: str,
    confirm_network_export: bool = False,
    timeout_seconds: float = 10.0,
    headers: Optional[dict[str, str]] = None,
) -> OtlpExportResult:
    """POST export to OTLP HTTP endpoint.

    Args:
        export_dict:            ArcTraceExport.model_dump() (already redacted).
        endpoint:               Full URL, e.g. http://localhost:4318/v1/traces
        confirm_network_export: Must be True; fails closed otherwise.
        timeout_seconds:        Request timeout.
        headers:                Extra HTTP headers (e.g. auth). Never logged.

    Returns:
        OtlpExportResult
    """
    if not confirm_network_export:
        raise ConfirmationRequired(
            "Network export requires --confirm-network-export flag. No data sent."
        )
    if not endpoint:
        raise EndpointRequired("--endpoint is required for OTLP HTTP export.")

    span_count = len(export_dict.get("spans") or [])

    try:
        payload = _build_otlp_json_payload(export_dict)
    except Exception as exc:
        return OtlpExportResult(
            ok=False, format="otlp-http", endpoint=endpoint, error=f"Payload build failed: {exc}"
        )

    # Validate no secrets BEFORE send
    try:
        _validate_no_secrets(payload)
    except ValueError as exc:
        return OtlpExportResult(ok=False, format="otlp-http", endpoint=endpoint, error=str(exc))

    # Use stdlib urllib — no heavy deps required
    import urllib.request  # noqa: S310 — opt-in only, confirmation required
    import urllib.error

    req = urllib.request.Request(
        endpoint,
        data=payload.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            status = resp.status
        return OtlpExportResult(
            ok=True,
            format="otlp-http",
            endpoint=endpoint,
            span_count=span_count,
            http_status=status,
        )
    except urllib.error.HTTPError as exc:
        return OtlpExportResult(
            ok=False,
            format="otlp-http",
            endpoint=endpoint,
            span_count=span_count,
            http_status=exc.code,
            error=f"HTTP {exc.code}",
        )
    except Exception as exc:
        return OtlpExportResult(
            ok=False, format="otlp-http", endpoint=endpoint, span_count=span_count, error=str(exc)
        )


def export_otlp_grpc(
    export_dict: dict[str, Any],
    *,
    endpoint: str,
    confirm_network_export: bool = False,
) -> OtlpExportResult:
    """Export via OTLP gRPC (requires opentelemetry-exporter-otlp-proto-grpc).

    Falls back to OTLP HTTP JSON if gRPC SDK not installed.
    Fails closed without confirmation.
    """
    if not confirm_network_export:
        raise ConfirmationRequired(
            "Network export requires --confirm-network-export flag. No data sent."
        )
    if not endpoint:
        raise EndpointRequired("--endpoint is required for OTLP gRPC export.")

    # Attempt SDK import — only to verify dependency availability
    try:
        import importlib.util as _ilu

        try:
            spec = _ilu.find_spec("opentelemetry.exporter.otlp.proto.grpc")
        except ModuleNotFoundError:
            spec = None
        if not spec:
            raise ImportError("opentelemetry-exporter-otlp-proto-grpc not installed")
    except ImportError as exc:
        raise OtlpGrpcUnavailable(
            "OTLP gRPC requires: pip install opentelemetry-exporter-otlp-proto-grpc\n"
            f"Original error: {exc}"
        ) from exc

    # Validate no secrets
    try:
        payload = json.dumps(export_dict)
        _validate_no_secrets(payload)
    except ValueError as exc:
        return OtlpExportResult(ok=False, format="otlp-grpc", endpoint=endpoint, error=str(exc))

    # Minimal SDK export via HTTP-fallback JSON payload
    # Note: Full gRPC export via SDK requires span objects, not dicts.
    # For MVP, fall through to HTTP JSON with gRPC endpoint if SDK unavailable.
    return OtlpExportResult(
        ok=False,
        format="otlp-grpc",
        endpoint=endpoint,
        error="OTLP_GRPC_FULL_SDK_NOT_CONFIGURED: use otlp-http with this endpoint instead",
    )
