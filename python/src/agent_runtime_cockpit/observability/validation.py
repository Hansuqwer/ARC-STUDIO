"""Validate ArcTraceExport for correctness and safety.

Fail-closed: unknown format → error.
Secrets in export → error when redact_check=True.
"""

from __future__ import annotations

import json

from .models import ArcTraceExport, ExportValidationReport

_VALID_FORMATS = {"arc-otel-json", "openinference-json"}
_MAX_PAYLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_SECRET_INDICATORS = ("Bearer ", "sk-", "Authorization:", "-----BEGIN")


def validate_export(export: ArcTraceExport, *, redact_check: bool = True) -> ExportValidationReport:
    """Validate a loaded ArcTraceExport. Returns ExportValidationReport."""
    errors: list[str] = []
    warnings: list[str] = []

    # Format check
    if export.format not in _VALID_FORMATS:
        errors.append(f"Unknown format: {export.format!r}. Must be one of {_VALID_FORMATS}")

    # Required IDs
    if not export.export_id:
        errors.append("export_id is required")

    # Parent span references
    span_ids = {s.span_id for s in export.spans}
    for span in export.spans:
        if span.parent_span_id and span.parent_span_id not in span_ids:
            errors.append(
                f"Span {span.span_id!r} references unknown parent {span.parent_span_id!r}"
            )

    # JSON serializable
    try:
        serialized = export.model_dump_json()
    except Exception as exc:
        errors.append(f"Export is not JSON serializable: {exc}")
        serialized = ""

    # Size check
    if len(serialized) > _MAX_PAYLOAD_BYTES:
        warnings.append(f"Export is large ({len(serialized) // 1024}KB); consider splitting")

    # No network destination
    dest = export.source.trace_file or ""
    if any(dest.startswith(p) for p in ("http://", "https://", "grpc://")):
        errors.append(f"Network destination not allowed: {dest!r}")

    # Secret check on serialized output
    if redact_check and serialized:
        for indicator in _SECRET_INDICATORS:
            if indicator in serialized:
                errors.append(f"Possible secret indicator found in export: {indicator!r}")

    return ExportValidationReport(
        ok=not errors,
        format=export.format,
        span_count=len(export.spans),
        errors=errors,
        warnings=warnings,
    )


def validate_export_file(path: str) -> ExportValidationReport:
    """Load and validate a JSON export file from disk."""
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
        export = ArcTraceExport.model_validate(data)
        return validate_export(export)
    except Exception as exc:
        return ExportValidationReport(
            ok=False,
            errors=[f"Failed to load export file: {exc}"],
        )
