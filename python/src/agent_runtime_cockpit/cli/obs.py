"""arc obs — OpenInference / OpenTelemetry local export commands.

arc obs export --trace-file <path> --format <fmt> --out <path> [--json]
arc obs inspect <export-path> [--json]
arc obs validate <export-path> [--json]
arc obs redaction-check <export-path> [--json]
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import obs_app


@obs_app.command("export")
def obs_export_cmd(
    trace_file: str = typer.Option(..., "--trace-file", help="Path to ARC JSONL trace file."),
    fmt: str = typer.Option(
        "openinference-json",
        "--format",
        "-f",
        help="Export format: openinference-json | arc-otel-json",
    ),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output JSON file path."),
    ir_file: Optional[str] = typer.Option(None, "--ir-file", help="Optional IR JSON to attach."),
    policy_file: Optional[str] = typer.Option(None, "--policy-file", help="Optional policy JSON."),
    no_redact: bool = typer.Option(False, "--no-redact"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export an ARC trace to OpenInference or OTel JSON (local file only)."""
    _setup_logging(debug)

    from ..observability import ObservabilityExportConfig, export_trace
    from ..observability.validation import validate_export

    if fmt not in ("openinference-json", "arc-otel-json"):
        _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown format: {fmt!r}"), json_output)
        raise typer.Exit(1)

    if not Path(trace_file).is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Trace file not found: {trace_file}"), json_output)
        raise typer.Exit(1)

    cfg = ObservabilityExportConfig(
        format=fmt,
        redact_secrets=not no_redact,
    )

    try:
        export = export_trace(
            trace_file,
            cfg=cfg,
            ir_file=ir_file,
            policy_file=policy_file,
            out=out,
        )
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Export failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    val = validate_export(export)
    payload = {
        "export_id": export.export_id,
        "format": export.format,
        "export_hash": export.export_hash,
        "span_count": len(export.spans),
        "warning_count": len(export.warnings),
        "tokens_redacted": export.redaction_summary.tokens_redacted,
        "valid": val.ok,
        "out": out,
        "warnings": [w.message for w in export.warnings],
    }
    _out(ok(payload), json_output)
    if not val.ok:
        raise typer.Exit(2)


@obs_app.command("inspect")
def obs_inspect_cmd(
    export_path: str = typer.Argument(..., help="Path to an observability export JSON file."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a local observability export file."""
    _setup_logging(debug)

    from ..observability.models import ArcTraceExport

    p = Path(export_path)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {export_path}"), json_output)
        raise typer.Exit(1)

    try:
        export = ArcTraceExport.model_validate_json(p.read_text())
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid export file: {exc}"), json_output)
        raise typer.Exit(1) from exc

    kinds: dict[str, int] = {}
    for span in export.spans:
        kinds[span.name] = kinds.get(span.name, 0) + 1

    payload = {
        "export_id": export.export_id,
        "format": export.format,
        "schema_version": export.schema_version,
        "export_hash": export.export_hash,
        "run_id": export.source.run_id,
        "span_count": len(export.spans),
        "span_kinds": kinds,
        "metric_count": len(export.metrics),
        "warning_count": len(export.warnings),
        "redaction_summary": export.redaction_summary.model_dump(),
        "resource": export.resource,
    }
    _out(ok(payload), json_output)


@obs_app.command("validate")
def obs_validate_cmd(
    export_path: str = typer.Argument(...),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate an observability export file."""
    _setup_logging(debug)

    from ..observability.validation import validate_export_file

    p = Path(export_path)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {export_path}"), json_output)
        raise typer.Exit(1)

    report = validate_export_file(str(p))
    payload = report.model_dump()
    _out(
        ok(payload)
        if report.ok
        else err(ArcErrorCode.INVALID_INPUT, "Validation failed", details=payload),
        json_output,
    )
    if not report.ok:
        raise typer.Exit(2)


@obs_app.command("redaction-check")
def obs_redaction_check_cmd(
    export_path: str = typer.Argument(...),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Check that an export file contains no obvious secrets."""
    _setup_logging(debug)

    from ..security.redaction import Redactor

    p = Path(export_path)
    if not p.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {export_path}"), json_output)
        raise typer.Exit(1)

    try:
        content = p.read_text()
        redactor = Redactor()
        safe = redactor.is_safe(content)
        payload = {
            "file": export_path,
            "is_safe": safe,
            "message": "No secrets detected." if safe else "Possible secret detected in export.",
        }
        _out(
            ok(payload)
            if safe
            else err(ArcErrorCode.INVALID_INPUT, "Secret detected", details=payload),
            json_output,
        )
        if not safe:
            raise typer.Exit(2)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Check failed: {exc}"), json_output)
        raise typer.Exit(1) from exc
