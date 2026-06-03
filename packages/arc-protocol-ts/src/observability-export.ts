/**
 * ARC Observability Export — TypeScript mirror of Python observability/models.py
 *
 * Local-first OpenInference / OpenTelemetry export types.
 * Schema version 1. No network transmission in MVP.
 */

export const OBSERVABILITY_SCHEMA_VERSION = 1;

export type ObsExportFormat = "arc-otel-json" | "openinference-json";

export interface ObservabilityExportConfig {
  schema_version: number;
  mode: "local";
  format: ObsExportFormat;
  destination: string;
  redact_secrets: boolean;
  include_payloads: boolean;
  include_policy: boolean;
  include_mcp: boolean;
  include_ir: boolean;
  include_evals: boolean;
  resource_attributes: Record<string, string>;
  fail_closed: boolean;
}

export interface ArcSpanEvent {
  name: string;
  timestamp?: string;
  attributes: Record<string, unknown>;
}

export interface ArcSpanLink {
  trace_id: string;
  span_id: string;
  attributes: Record<string, unknown>;
}

export interface ArcSpan {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  name: string;
  kind: string;
  start_time?: string;
  end_time?: string;
  attributes: Record<string, unknown>;
  events: ArcSpanEvent[];
  status: string;
  links: ArcSpanLink[];
}

export interface ArcMetric {
  name: string;
  kind: string;
  value: number;
  unit: string;
  attributes: Record<string, unknown>;
}

export interface RedactionSummary {
  fields_redacted: number;
  tokens_redacted: number;
  payloads_removed: number;
  paths_redacted: number;
}

export interface ExportSource {
  run_id?: string;
  trace_file?: string;
  ir_hash?: string;
  policy_hash?: string;
  source_hash?: string;
}

export interface ExportWarning {
  code: string;
  message: string;
  span_id?: string;
}

export interface ArcTraceExport {
  schema_version: number;
  export_id: string;
  created_at?: string;
  format: ObsExportFormat;
  source: ExportSource;
  resource: Record<string, unknown>;
  spans: ArcSpan[];
  metrics: ArcMetric[];
  redaction_summary: RedactionSummary;
  warnings: ExportWarning[];
  export_hash?: string;
}

export interface ExportValidationReport {
  ok: boolean;
  format: string;
  span_count: number;
  errors: string[];
  warnings: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Type guard for ArcTraceExport */
export function isArcTraceExport(obj: unknown): obj is ArcTraceExport {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "export_id" in obj &&
    "spans" in obj &&
    Array.isArray((obj as ArcTraceExport).spans)
  );
}

/** Get the root span (arc.run) from an export */
export function getRootSpan(export_: ArcTraceExport): ArcSpan | undefined {
  return export_.spans.find((s) => s.name === "arc.run");
}

/** Get child spans by parent span ID */
export function getChildSpans(export_: ArcTraceExport, parentId: string): ArcSpan[] {
  return export_.spans.filter((s) => s.parent_span_id === parentId);
}

/** Check if an export has any errors */
export function exportHasWarnings(export_: ArcTraceExport): boolean {
  return export_.warnings.length > 0;
}
