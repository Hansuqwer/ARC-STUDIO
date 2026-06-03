"""ARC Observability — OpenInference / OpenTelemetry export.

Local-first, opt-in. No network transmission in MVP.

Usage:
    from agent_runtime_cockpit.observability import export_trace, ObservabilityExportConfig
    report = export_trace("run.jsonl", out="out.json")
"""

from .exporters import export_trace
from .loaders import LoadedTrace, load_trace_file
from .models import (
    ArcMetric,
    ArcSpan,
    ArcSpanEvent,
    ArcTraceExport,
    ExportSource,
    ExportValidationReport,
    ExportWarning,
    ObservabilityExportConfig,
    RedactionSummary,
    OBSERVABILITY_SCHEMA_VERSION,
)
from .validation import validate_export, validate_export_file

__all__ = [
    "export_trace",
    "load_trace_file",
    "LoadedTrace",
    "ObservabilityExportConfig",
    "ArcTraceExport",
    "ArcSpan",
    "ArcSpanEvent",
    "ArcMetric",
    "ExportSource",
    "ExportWarning",
    "ExportValidationReport",
    "RedactionSummary",
    "validate_export",
    "validate_export_file",
    "OBSERVABILITY_SCHEMA_VERSION",
]
