"""ARC Observability — OpenInference / OpenTelemetry export.

Local-first, opt-in. No network transmission in MVP.

Usage:
    from agent_runtime_cockpit.observability import export_trace, ObservabilityExportConfig
    report = export_trace("run.jsonl", out="out.json")
"""

from .exporters import export_trace
from .loaders import (
    LoadedTrace,
    RunNotFoundError,
    RunRecordInvalidError,
    load_run_by_id,
    load_trace_file,
)
from .mcp_drift import McpDriftSummary, McpToolStatus, infer_mcp_drift
from .models import (
    ArcMetric,
    ArcSpan,
    ArcSpanEvent,
    ArcTraceExport,
    ExportSource,
    ExportValidationReport,
    ExportWarning,
    LiveExportStatus,
    ObservabilityExportConfig,
    RedactionSummary,
    OBSERVABILITY_SCHEMA_VERSION,
)
from .validation import validate_export, validate_export_file

__all__ = [
    "export_trace",
    "load_trace_file",
    "load_run_by_id",
    "LoadedTrace",
    "RunNotFoundError",
    "RunRecordInvalidError",
    "infer_mcp_drift",
    "McpDriftSummary",
    "McpToolStatus",
    "ObservabilityExportConfig",
    "ArcTraceExport",
    "ArcSpan",
    "ArcSpanEvent",
    "ArcMetric",
    "ExportSource",
    "ExportWarning",
    "ExportValidationReport",
    "LiveExportStatus",
    "RedactionSummary",
    "validate_export",
    "validate_export_file",
    "OBSERVABILITY_SCHEMA_VERSION",
]
