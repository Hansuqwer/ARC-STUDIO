"""arc obs — OpenInference / OpenTelemetry local and live export commands.

arc obs export --trace-file <path> --format openinference-json --out <path>
arc obs export --run-id <id> --format openinference-json --out <path>
arc obs export --run-id <id> --format otlp-http --endpoint <url> --confirm-network-export
arc obs export --run-id <id> --format otlp-grpc --endpoint <url> --confirm-network-export
arc obs inspect <export-path>
arc obs validate <export-path>
arc obs redaction-check <export-path>
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import obs_app

_LOCAL_FORMATS = {"openinference-json", "arc-otel-json"}
_LIVE_FORMATS = {"otlp-http", "otlp-grpc"}
_ALL_FORMATS = _LOCAL_FORMATS | _LIVE_FORMATS


@obs_app.command("export")
def obs_export_cmd(
    trace_file: Optional[str] = typer.Option(
        None, "--trace-file", help="Path to ARC JSONL trace file."
    ),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="ARC run ID (load from storage)."),
    fmt: str = typer.Option(
        "openinference-json",
        "--format",
        "-f",
        help="Export format: openinference-json | arc-otel-json | otlp-http | otlp-grpc",
    ),
    out: Optional[str] = typer.Option(
        None, "--out", "-o", help="Output JSON file path (local formats)."
    ),
    ir_file: Optional[str] = typer.Option(None, "--ir-file", help="Optional IR JSON to attach."),
    policy_file: Optional[str] = typer.Option(None, "--policy-file", help="Optional policy JSON."),
    endpoint: Optional[str] = typer.Option(
        None, "--endpoint", help="OTLP endpoint URL (live export only)."
    ),
    confirm_network_export: bool = typer.Option(
        False,
        "--confirm-network-export",
        help="Required for live OTLP export. Confirms data will leave this machine.",
    ),
    storage_root: Optional[str] = typer.Option(
        None, "--storage-root", help="Override ARC storage root."
    ),
    no_redact: bool = typer.Option(False, "--no-redact"),
    no_mcp_drift: bool = typer.Option(False, "--no-mcp-drift", help="Skip MCP drift inference."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export an ARC trace to OpenInference, OTel JSON, or live OTLP (opt-in)."""
    _setup_logging(debug)

    from ..observability import (
        ObservabilityExportConfig,
        RunNotFoundError,
        RunRecordInvalidError,
        export_trace,
        load_run_by_id,
    )
    from ..observability.validation import validate_export

    if fmt not in _ALL_FORMATS:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown format: {fmt!r}. Valid: {sorted(_ALL_FORMATS)}",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Live export safety gate
    if fmt in _LIVE_FORMATS:
        if not confirm_network_export:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Live OTLP export requires --confirm-network-export. No data sent.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        if not endpoint:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Live OTLP export requires --endpoint. No data sent.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    # Exactly one of --trace-file or --run-id required
    if not trace_file and not run_id:
        _out(err(ArcErrorCode.INVALID_INPUT, "Provide --trace-file or --run-id."), json_output)
        raise typer.Exit(1)
    if trace_file and run_id:
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Provide --trace-file OR --run-id, not both."),
            json_output,
        )
        raise typer.Exit(1)

    if trace_file and not Path(trace_file).is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Trace file not found: {trace_file}"), json_output)
        raise typer.Exit(1)

    # For run-id, validate early
    if run_id:
        try:
            trace = load_run_by_id(run_id, storage_root=storage_root)
            trace_source = trace.source_file
        except RunNotFoundError as exc:
            _out(err(ArcErrorCode.NOT_FOUND, str(exc)), json_output)
            raise typer.Exit(1) from exc
        except RunRecordInvalidError as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Run record invalid: {exc}"), json_output)
            raise typer.Exit(1) from exc
        except Exception as exc:  # noqa: BLE001
            _out(err(ArcErrorCode.INTERNAL_ERROR, f"Storage error: {exc}"), json_output)
            raise typer.Exit(1) from exc
    else:
        trace_source = trace_file

    cfg = ObservabilityExportConfig(
        format=fmt if fmt in _LOCAL_FORMATS else "openinference-json",
        redact_secrets=not no_redact,
    )

    try:
        export = export_trace(
            trace_source,
            cfg=cfg,
            ir_file=ir_file,
            policy_file=policy_file,
            out=out if fmt in _LOCAL_FORMATS else None,
        )
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Export failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    # MCP drift inference
    mcp_drift_payload: Optional[dict] = None
    if not no_mcp_drift and run_id:
        try:
            from ..observability.mcp_drift import infer_mcp_drift as _infer

            drift = _infer(
                export.source.run_id and [e for s in export.spans for e in s.events] or [],
                workspace=storage_root,
            )
            # Re-run on raw events (more complete)
            if run_id:
                raw_trace = load_run_by_id(run_id, storage_root=storage_root)
                drift = _infer(raw_trace.events, workspace=storage_root)
            mcp_drift_payload = drift.model_dump()
        except Exception as exc:
            log_warn = f"MCP drift inference failed (non-fatal): {exc}"
            export.warnings.append(
                __import__(
                    "agent_runtime_cockpit.observability.models", fromlist=["ExportWarning"]
                ).ExportWarning(code="mcp_drift_error", message=log_warn)
            )

    val = validate_export(export)

    # Live OTLP export
    live_status: Optional[dict] = None
    if fmt in _LIVE_FORMATS:
        from ..observability.otlp_exporter import (
            ConfirmationRequired,
            EndpointRequired,
            OtlpGrpcUnavailable,
            export_otlp_http,
            export_otlp_grpc,
        )

        if not val.ok:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Validation failed; refusing live export.",
                    details=val.model_dump(),
                ),
                json_output,
            )
            raise typer.Exit(2)

        export_dict = json.loads(export.model_dump_json())
        try:
            if fmt == "otlp-http":
                result = export_otlp_http(
                    export_dict,
                    endpoint=endpoint,
                    confirm_network_export=confirm_network_export,
                )
            else:
                result = export_otlp_grpc(
                    export_dict,
                    endpoint=endpoint,
                    confirm_network_export=confirm_network_export,
                )
            live_status = result.model_dump()
        except OtlpGrpcUnavailable as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
            raise typer.Exit(1) from exc
        except (ConfirmationRequired, EndpointRequired) as exc:
            _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
            raise typer.Exit(1) from exc

    payload = {
        "export_id": export.export_id,
        "format": export.format,
        "export_hash": export.export_hash,
        "span_count": len(export.spans),
        "warning_count": len(export.warnings),
        "tokens_redacted": export.redaction_summary.tokens_redacted,
        "valid": val.ok,
        "out": out,
    }
    if mcp_drift_payload:
        payload["mcp_drift"] = mcp_drift_payload
    if live_status:
        payload["live_export"] = live_status

    _out(ok(payload), json_output)
    if not val.ok:
        raise typer.Exit(2)


@obs_app.command("inspect")
def obs_inspect_cmd(
    export_path: str = typer.Argument(...),
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
