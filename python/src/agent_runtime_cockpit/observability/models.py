"""Observability export models for OpenInference / OpenTelemetry output.

Local-first, no network transmission. Schema version 1.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


OBSERVABILITY_SCHEMA_VERSION = 1


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── Config ────────────────────────────────────────────────────────────────────


class ObservabilityExportConfig(_Base):
    schema_version: int = OBSERVABILITY_SCHEMA_VERSION
    mode: Literal["local"] = "local"  # only local supported in MVP
    format: Literal["arc-otel-json", "openinference-json"] = "openinference-json"
    destination: str = "local"  # file path; "local" = caller provides path
    redact_secrets: bool = True
    include_payloads: bool = True
    include_policy: bool = True
    include_mcp: bool = True
    include_ir: bool = True
    include_evals: bool = True
    resource_attributes: dict[str, str] = Field(default_factory=dict)
    fail_closed: bool = True


# ── Core span models ──────────────────────────────────────────────────────────


class ArcSpanEvent(_Base):
    name: str
    timestamp: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ArcSpanLink(_Base):
    trace_id: str
    span_id: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class ArcSpan(_Base):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: str = "INTERNAL"  # INTERNAL | SERVER | CLIENT | PRODUCER | CONSUMER
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    events: list[ArcSpanEvent] = Field(default_factory=list)
    status: str = "OK"  # OK | ERROR | UNSET
    links: list[ArcSpanLink] = Field(default_factory=list)


class ArcMetric(_Base):
    name: str
    kind: str = "gauge"  # gauge | counter | histogram
    value: float = 0.0
    unit: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)


# ── Redaction ─────────────────────────────────────────────────────────────────


class RedactionSummary(_Base):
    fields_redacted: int = 0
    tokens_redacted: int = 0
    payloads_removed: int = 0
    paths_redacted: int = 0


# ── Source reference ──────────────────────────────────────────────────────────


class ExportSource(_Base):
    run_id: Optional[str] = None
    trace_file: Optional[str] = None
    ir_hash: Optional[str] = None
    policy_hash: Optional[str] = None
    source_hash: Optional[str] = None  # SHA-256 of source content


# ── Warnings ─────────────────────────────────────────────────────────────────


class ExportWarning(_Base):
    code: str
    message: str
    span_id: Optional[str] = None


# ── Top-level export ──────────────────────────────────────────────────────────


class ArcTraceExport(_Base):
    schema_version: int = OBSERVABILITY_SCHEMA_VERSION
    export_id: str
    created_at: Optional[str] = None  # excluded from export_hash
    format: str = "openinference-json"
    source: ExportSource = Field(default_factory=ExportSource)
    resource: dict[str, Any] = Field(default_factory=dict)
    spans: list[ArcSpan] = Field(default_factory=list)
    metrics: list[ArcMetric] = Field(default_factory=list)
    redaction_summary: RedactionSummary = Field(default_factory=RedactionSummary)
    warnings: list[ExportWarning] = Field(default_factory=list)
    export_hash: Optional[str] = None  # excluded from its own computation


# ── Validation ────────────────────────────────────────────────────────────────


class ExportValidationReport(_Base):
    ok: bool = True
    format: str = ""
    span_count: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LiveExportStatus(_Base):
    attempted: bool = False
    format: str = ""  # otlp-http | otlp-grpc
    endpoint: Optional[str] = None
    ok: bool = False
    span_count: int = 0
    http_status: Optional[int] = None
    error: Optional[str] = None
