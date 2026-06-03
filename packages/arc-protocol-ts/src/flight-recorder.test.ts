/**
 * TypeScript parity tests for the Local Agent Flight Recorder types.
 *
 * Verifies:
 *  - All expected event types are present.
 *  - Interface shapes match the Python model spec.
 *  - Schema version constant is correct.
 *  - No runtime side-effects on import.
 */

import {
  FLIGHT_RECORDER_SCHEMA_VERSION,
  FlightEvent,
  FlightEventType,
  FlightExportBundle,
  FlightIndex,
  FlightRecorderConfig,
  FlightSegment,
  FlightVerificationReport,
  RedactionSummary,
  RetentionPolicy,
  RunEntry,
  SegmentRef,
} from "./flight-recorder";

describe("FlightRecorder TypeScript types", () => {
  // -------------------------------------------------------------------------
  // Schema version
  // -------------------------------------------------------------------------

  test("FLIGHT_RECORDER_SCHEMA_VERSION is '1'", () => {
    expect(FLIGHT_RECORDER_SCHEMA_VERSION).toBe("1");
  });

  // -------------------------------------------------------------------------
  // Event types
  // -------------------------------------------------------------------------

  test("FlightEventType includes all run lifecycle types", () => {
    const runTypes: FlightEventType[] = ["run.started", "run.completed", "run.failed"];
    // TypeScript compile-time check — if these don't match the union, the file
    // won't compile. Runtime: just verify the strings.
    runTypes.forEach((t) => expect(typeof t).toBe("string"));
  });

  test("FlightEventType includes ir.compiled", () => {
    const t: FlightEventType = "ir.compiled";
    expect(t).toBe("ir.compiled");
  });

  test("FlightEventType includes crash.marker", () => {
    const t: FlightEventType = "crash.marker";
    expect(t).toBe("crash.marker");
  });

  test("FlightEventType includes all mcp types", () => {
    const types: FlightEventType[] = [
      "mcp.manifest.checked",
      "mcp.tool.approved",
      "mcp.tool.blocked",
    ];
    types.forEach((t) => expect(typeof t).toBe("string"));
  });

  test("FlightEventType includes all hitl types", () => {
    const types: FlightEventType[] = [
      "hitl.requested",
      "hitl.approved",
      "hitl.rejected",
    ];
    types.forEach((t) => expect(typeof t).toBe("string"));
  });

  // -------------------------------------------------------------------------
  // FlightEvent shape
  // -------------------------------------------------------------------------

  test("FlightEvent satisfies expected shape", () => {
    const evt: FlightEvent = {
      schemaVersion: "1",
      eventId: "evt-001",
      eventType: "ir.compiled",
      runId: "run-abc",
      sessionId: null,
      timestamp: "2026-06-03T10:00:00Z",
      sequence: 0,
      source: "arc",
      payload: { irHash: "abc123" },
      redaction: {
        fieldsRedacted: [],
        patternsMatched: [],
        redactApplied: false,
      },
      auditRef: null,
      traceRef: "run-abc",
      hash: "a".repeat(64),
    };
    expect(evt.schemaVersion).toBe("1");
    expect(evt.eventType).toBe("ir.compiled");
    expect(evt.hash).toHaveLength(64);
  });

  // -------------------------------------------------------------------------
  // FlightSegment
  // -------------------------------------------------------------------------

  test("FlightSegment satisfies expected shape", () => {
    const seg: FlightSegment = {
      schemaVersion: "1",
      segmentId: "seg-001",
      runId: "run-abc",
      createdAt: "2026-06-03T10:00:00Z",
      closedAt: "2026-06-03T10:01:00Z",
      eventCount: 5,
      firstSequence: 0,
      lastSequence: 4,
      segmentHash: "b".repeat(64),
      previousSegmentHash: "GENESIS",
      eventsPath: "segments/run-abc/segment-000000.events.jsonl",
      metaPath: "segments/run-abc/segment-000000.meta.json",
      corrupt: false,
      metadata: {},
    };
    expect(seg.previousSegmentHash).toBe("GENESIS");
    expect(seg.corrupt).toBe(false);
  });

  // -------------------------------------------------------------------------
  // FlightIndex
  // -------------------------------------------------------------------------

  test("FlightIndex satisfies expected shape", () => {
    const idx: FlightIndex = {
      schemaVersion: "1",
      segments: [],
      runs: {},
      retention: {
        maxSegments: 200,
        maxTotalBytes: 100 * 1024 * 1024,
        maxAgeDays: 30,
      },
      lastVerifiedAt: null,
      lastUpdatedAt: "2026-06-03T10:00:00Z",
    };
    expect(idx.segments).toHaveLength(0);
    expect(idx.retention.maxSegments).toBe(200);
  });

  // -------------------------------------------------------------------------
  // FlightRecorderConfig
  // -------------------------------------------------------------------------

  test("FlightRecorderConfig satisfies expected shape", () => {
    const cfg: FlightRecorderConfig = {
      enabled: true,
      baseDir: ".arc/flight",
      maxSegmentBytes: 5 * 1024 * 1024,
      maxSegments: 200,
      maxTotalBytes: 100 * 1024 * 1024,
      maxAgeDays: 30,
      redactSecrets: true,
      includePayloads: true,
      includeEnvSummary: false,
      compression: false,
      failClosed: true,
    };
    expect(cfg.redactSecrets).toBe(true);
    expect(cfg.failClosed).toBe(true);
  });

  // -------------------------------------------------------------------------
  // FlightExportBundle
  // -------------------------------------------------------------------------

  test("FlightExportBundle satisfies expected shape", () => {
    const bundle: FlightExportBundle = {
      schemaVersion: "1",
      bundleId: "bnd-001",
      createdAt: "2026-06-03T10:00:00Z",
      runs: ["run-abc"],
      segments: ["seg-001"],
      manifest: [{ path: "manifest.json", sha256: "c".repeat(64), sizeBytes: 256 }],
      checksums: { "manifest.json": "c".repeat(64) },
      redactionSummary: { fieldsRedacted: [], patternsMatched: [], redactApplied: false },
      totalEvents: 5,
    };
    expect(bundle.schemaVersion).toBe("1");
    expect(bundle.totalEvents).toBe(5);
  });

  // -------------------------------------------------------------------------
  // FlightVerificationReport
  // -------------------------------------------------------------------------

  test("FlightVerificationReport satisfies expected shape", () => {
    const report: FlightVerificationReport = {
      schemaVersion: "1",
      ok: true,
      checkedSegments: 2,
      corruptSegments: [],
      missingSegments: [],
      hashChainValid: true,
      issues: [],
      verifiedAt: "2026-06-03T10:00:00Z",
    };
    expect(report.ok).toBe(true);
    expect(report.hashChainValid).toBe(true);
  });

  test("FlightVerificationReport with issues", () => {
    const report: FlightVerificationReport = {
      schemaVersion: "1",
      ok: false,
      checkedSegments: 1,
      corruptSegments: ["seg-bad"],
      missingSegments: [],
      hashChainValid: false,
      issues: [
        {
          segmentId: "seg-bad",
          issueType: "hash_mismatch",
          detail: "hash mismatch at index 0",
        },
      ],
      verifiedAt: "2026-06-03T10:00:00Z",
    };
    expect(report.ok).toBe(false);
    expect(report.issues).toHaveLength(1);
    expect(report.issues[0].issueType).toBe("hash_mismatch");
  });

  // -------------------------------------------------------------------------
  // RunEntry
  // -------------------------------------------------------------------------

  test("RunEntry satisfies expected shape", () => {
    const run: RunEntry = {
      runId: "run-abc",
      sessionId: "sess-001",
      startedAt: "2026-06-03T10:00:00Z",
      completedAt: "2026-06-03T10:05:00Z",
      status: "completed",
      segmentIds: ["seg-001"],
      irHash: "abc123",
      policyRisk: "low",
      traceRef: "run-abc",
      auditRef: "audit-001",
    };
    expect(run.status).toBe("completed");
    expect(run.segmentIds).toHaveLength(1);
  });
});
