/**
 * Local Agent Flight Recorder — TypeScript type mirror.
 *
 * Read-only TypeScript interfaces mirroring the Python Pydantic models in
 * `python/src/agent_runtime_cockpit/flight_recorder/models.py`.
 *
 * Schema version: "1"
 *
 * Design constraints:
 *   - No network I/O.
 *   - No subprocess.
 *   - No model calls.
 *   - Pure type declarations — zero runtime behaviour.
 *   - Readonly interfaces for forward compatibility.
 */

export const FLIGHT_RECORDER_SCHEMA_VERSION = "1" as const;

// ---------------------------------------------------------------------------
// Event types
// ---------------------------------------------------------------------------

export type FlightEventType =
  // Run lifecycle
  | "run.started"
  | "run.completed"
  | "run.failed"
  // SwarmGraph IR
  | "ir.compiled"
  // Policy
  | "policy.evaluated"
  // Simulation
  | "simulation.generated"
  // MCP
  | "mcp.manifest.checked"
  | "mcp.tool.approved"
  | "mcp.tool.blocked"
  // HITL
  | "hitl.requested"
  | "hitl.approved"
  | "hitl.rejected"
  // Consensus
  | "consensus.selected"
  // Audit
  | "audit.receipt.created"
  // Evals
  | "eval.recommendation.generated"
  // Tool calls
  | "tool.call.planned"
  | "tool.call.completed"
  // Errors / crash
  | "error.raised"
  | "crash.marker"
  // Recorder internal
  | "segment.opened"
  | "segment.closed"
  | "recorder.started"
  | "recorder.stopped";

// ---------------------------------------------------------------------------
// RedactionSummary
// ---------------------------------------------------------------------------

export interface RedactionSummary {
  readonly fieldsRedacted: readonly string[];
  readonly patternsMatched: readonly string[];
  readonly redactApplied: boolean;
}

// ---------------------------------------------------------------------------
// FlightEvent
// ---------------------------------------------------------------------------

/**
 * A single immutable flight recorder event.
 *
 * `hash` is SHA-256 over canonical JSON of all other fields (sorted keys).
 * Secrets are redacted before this model is persisted.
 * `sequence` is monotonically increasing within a segment.
 */
export interface FlightEvent {
  readonly schemaVersion: string;
  readonly eventId: string;
  readonly eventType: FlightEventType;
  readonly runId: string;
  readonly sessionId: string | null;
  readonly timestamp: string; // ISO-8601 UTC
  readonly sequence: number;
  readonly source: string;
  readonly payload: Record<string, unknown>;
  readonly redaction: RedactionSummary;
  readonly auditRef: string | null;
  readonly traceRef: string | null;
  readonly hash: string; // SHA-256 hex
}

// ---------------------------------------------------------------------------
// FlightSegment
// ---------------------------------------------------------------------------

/**
 * Metadata for one append-only JSONL segment file.
 *
 * Hash chain: previousSegmentHash → segmentHash (SHA-256 over all event hashes
 * in sequence order), enabling tamper-evident ordering across segments.
 */
export interface FlightSegment {
  readonly schemaVersion: string;
  readonly segmentId: string;
  readonly runId: string;
  readonly createdAt: string; // ISO-8601 UTC
  readonly closedAt: string | null;
  readonly eventCount: number;
  readonly firstSequence: number;
  readonly lastSequence: number;
  readonly segmentHash: string;
  readonly previousSegmentHash: string; // "GENESIS" for first segment
  readonly eventsPath: string; // relative to .arc/flight/
  readonly metaPath: string;
  readonly corrupt: boolean;
  readonly metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// FlightIndex
// ---------------------------------------------------------------------------

export interface SegmentRef {
  readonly segmentId: string;
  readonly runId: string;
  readonly createdAt: string;
  readonly closedAt: string | null;
  readonly eventCount: number;
  readonly segmentHash: string;
  readonly previousSegmentHash: string;
  readonly eventsPath: string;
  readonly metaPath: string;
  readonly corrupt: boolean;
}

export interface RunEntry {
  readonly runId: string;
  readonly sessionId: string | null;
  readonly startedAt: string;
  readonly completedAt: string | null;
  readonly status: "running" | "completed" | "failed" | "crashed";
  readonly segmentIds: readonly string[];
  readonly irHash: string | null;
  readonly policyRisk: string | null;
  readonly traceRef: string | null;
  readonly auditRef: string | null;
}

export interface RetentionPolicy {
  readonly maxSegments: number;
  readonly maxTotalBytes: number;
  readonly maxAgeDays: number;
}

/**
 * Master index across all segments and runs.
 * Written atomically to `.arc/flight/index.json`.
 */
export interface FlightIndex {
  readonly schemaVersion: string;
  readonly segments: readonly SegmentRef[];
  readonly runs: Record<string, RunEntry>;
  readonly retention: RetentionPolicy;
  readonly lastVerifiedAt: string | null;
  readonly lastUpdatedAt: string;
}

// ---------------------------------------------------------------------------
// FlightRecorderConfig
// ---------------------------------------------------------------------------

export interface FlightRecorderConfig {
  readonly enabled: boolean;
  readonly baseDir: string;
  readonly maxSegmentBytes: number;
  readonly maxSegments: number;
  readonly maxTotalBytes: number;
  readonly maxAgeDays: number;
  readonly redactSecrets: boolean;
  readonly includePayloads: boolean;
  readonly includeEnvSummary: boolean;
  readonly compression: boolean;
  readonly failClosed: boolean;
}

// ---------------------------------------------------------------------------
// FlightExportBundle
// ---------------------------------------------------------------------------

export interface BundleManifestEntry {
  readonly path: string;
  readonly sha256: string;
  readonly sizeBytes: number;
}

/**
 * Manifest written into every export tarball as `manifest.json`.
 */
export interface FlightExportBundle {
  readonly schemaVersion: string;
  readonly bundleId: string;
  readonly createdAt: string;
  readonly runs: readonly string[];
  readonly segments: readonly string[];
  readonly manifest: readonly BundleManifestEntry[];
  readonly checksums: Record<string, string>; // path → sha256
  readonly redactionSummary: RedactionSummary;
  readonly totalEvents: number;
}

// ---------------------------------------------------------------------------
// FlightVerificationReport
// ---------------------------------------------------------------------------

export interface VerificationIssue {
  readonly segmentId: string;
  readonly issueType: "hash_mismatch" | "corrupt_json" | "missing_file" | "chain_break";
  readonly detail: string;
}

/**
 * Output of `arc flight verify`.
 */
export interface FlightVerificationReport {
  readonly schemaVersion: string;
  readonly ok: boolean;
  readonly checkedSegments: number;
  readonly corruptSegments: readonly string[];
  readonly missingSegments: readonly string[];
  readonly hashChainValid: boolean;
  readonly issues: readonly VerificationIssue[];
  readonly verifiedAt: string;
}

// ---------------------------------------------------------------------------
// CLI JSON output shapes (for arc flight status / verify / export / prune)
// ---------------------------------------------------------------------------

export interface FlightStatusOutput {
  readonly ok: boolean;
  readonly status: {
    readonly enabled: boolean;
    readonly baseDir: string;
    readonly activeRuns: readonly string[];
    readonly totalSegments: number;
    readonly totalRuns: number;
    readonly totalBytes: number;
    readonly lastVerifiedAt: string | null;
    readonly lastUpdatedAt: string;
    readonly retention: RetentionPolicy;
  };
}

export interface FlightVerifyOutput {
  readonly ok: boolean;
  readonly report: FlightVerificationReport;
}

export interface FlightExportOutput {
  readonly ok: boolean;
  readonly bundleId: string;
  readonly out: string;
  readonly totalEvents: number;
  readonly segments: readonly string[];
}

export interface FlightPruneOutput {
  readonly ok: boolean;
  readonly dryRun: boolean;
  readonly prunableSegments: number;
  readonly deletedSegmentIds: readonly string[];
  readonly deletedPaths: readonly string[];
  readonly errors: readonly string[];
  readonly applied: boolean;
}
