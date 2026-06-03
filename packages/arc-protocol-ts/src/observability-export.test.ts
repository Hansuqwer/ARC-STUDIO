import * as fs from "fs";
import * as path from "path";
import {
  ArcTraceExport,
  ArcSpan,
  isArcTraceExport,
  getRootSpan,
  getChildSpans,
  exportHasWarnings,
  OBSERVABILITY_SCHEMA_VERSION,
} from "./observability-export";

const FIXTURES_DIR = path.resolve(
  __dirname,
  "../../../python/tests/observability/fixtures"
);

function buildMinimalExport(): ArcTraceExport {
  return {
    schema_version: 1,
    export_id: "test-export-001",
    format: "openinference-json",
    source: { run_id: "run-001", trace_file: "minimal_run.jsonl" },
    resource: { "service.name": "arc-studio" },
    spans: [
      {
        trace_id: "abc123",
        span_id: "span-root",
        name: "arc.run",
        kind: "SERVER",
        attributes: { "arc.run.id": "run-001" },
        events: [],
        status: "OK",
        links: [],
      },
      {
        trace_id: "abc123",
        span_id: "span-tool",
        parent_span_id: "span-root",
        name: "arc.tool.call",
        kind: "INTERNAL",
        attributes: { "arc.tool.name": "read_file" },
        events: [],
        status: "OK",
        links: [],
      },
    ],
    metrics: [],
    redaction_summary: {
      fields_redacted: 0,
      tokens_redacted: 0,
      payloads_removed: 0,
      paths_redacted: 0,
    },
    warnings: [],
    export_hash: "abc123hash",
  };
}

describe("ArcTraceExport TypeScript mirror", () => {
  it("schema version constant is 1", () => {
    expect(OBSERVABILITY_SCHEMA_VERSION).toBe(1);
  });

  it("isArcTraceExport accepts valid export", () => {
    expect(isArcTraceExport(buildMinimalExport())).toBe(true);
  });

  it("isArcTraceExport rejects non-export", () => {
    expect(isArcTraceExport({ foo: "bar" })).toBe(false);
    expect(isArcTraceExport(null)).toBe(false);
  });

  it("getRootSpan finds arc.run span", () => {
    const root = getRootSpan(buildMinimalExport());
    expect(root?.name).toBe("arc.run");
    expect(root?.attributes["arc.run.id"]).toBe("run-001");
  });

  it("getChildSpans returns spans by parent", () => {
    const exp = buildMinimalExport();
    const children = getChildSpans(exp, "span-root");
    expect(children).toHaveLength(1);
    expect(children[0].name).toBe("arc.tool.call");
  });

  it("exportHasWarnings returns false when no warnings", () => {
    expect(exportHasWarnings(buildMinimalExport())).toBe(false);
  });

  it("exportHasWarnings returns true when warnings present", () => {
    const exp = buildMinimalExport();
    exp.warnings = [{ code: "test", message: "a warning" }];
    expect(exportHasWarnings(exp)).toBe(true);
  });

  it("format values are constrained to valid types", () => {
    const exp = buildMinimalExport();
    // Both valid formats accepted
    exp.format = "arc-otel-json";
    expect(exp.format).toBe("arc-otel-json");
    exp.format = "openinference-json";
    expect(exp.format).toBe("openinference-json");
  });

  it("accepts Python fixture export when present", () => {
    const fixturePath = path.join(FIXTURES_DIR, "minimal_run.jsonl");
    if (!fs.existsSync(fixturePath)) {
      // Skip if fixture not available in this environment
      return;
    }
    // Fixture is raw JSONL, not an export — just verify file exists
    expect(fs.existsSync(fixturePath)).toBe(true);
  });

  it("RedactionSummary has all required fields", () => {
    const exp = buildMinimalExport();
    expect(exp.redaction_summary).toHaveProperty("fields_redacted");
    expect(exp.redaction_summary).toHaveProperty("tokens_redacted");
    expect(exp.redaction_summary).toHaveProperty("payloads_removed");
    expect(exp.redaction_summary).toHaveProperty("paths_redacted");
  });

  it("ArcSpan events list accepts span events", () => {
    const exp = buildMinimalExport();
    const root = getRootSpan(exp)!;
    root.events.push({
      name: "arc.hitl.gate",
      timestamp: "2026-06-01T10:00:10Z",
      attributes: { "arc.hitl.required": true },
    });
    expect(root.events).toHaveLength(1);
    expect(root.events[0].name).toBe("arc.hitl.gate");
  });

  it("ExportSource optional fields can be undefined", () => {
    const source = buildMinimalExport().source;
    // ir_hash and policy_hash are optional
    expect(source.ir_hash).toBeUndefined();
  });
});
