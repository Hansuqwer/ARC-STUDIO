/**
 * Replay & Run Diff protocol types.
 *
 * Extracted from `arc-protocol.ts` (CR-027) to keep the protocol surface modular.
 * Re-exported from `arc-protocol.ts` so existing `from '../../common/arc-protocol'`
 * imports continue to work unchanged. These types are self-contained (no cross-section
 * references), so the module has no imports.
 */

// ========== Replay ==========

/**
 * Replay event from stored trace.
 */
export interface ReplayEvent {
    type: string;
    timestamp: string;
    runId: string;
    sequence: number;
    data: Record<string, unknown>;
    category?: 'lifecycle' | 'message' | 'tool' | 'error' | 'hitl' | 'audit' | 'unknown';
    annotations?: string[];
    metadata?: Record<string, unknown>;
}

/**
 * Replay result for a run.
 */
export interface ReplayResult {
    runId: string;
    events: ReplayEvent[];
    totalEvents: number;
    annotations?: string[];
    metadata?: Record<string, unknown>;
}

// ========== Run Diff ==========

export interface RunDiffResult {
    runAId: string;
    runBId: string;
    statusA: string;
    statusB: string;
    runtimeA: string;
    runtimeB: string;
    durationAMs?: number | null;
    durationBMs?: number | null;
    eventCountA: number;
    eventCountB: number;
    typesOnlyInA: string[];
    typesOnlyInB: string[];
    typesCommon: string[];
    finalOutputA?: string | null;
    finalOutputB?: string | null;
    errorEventsA: Record<string, unknown>[];
    errorEventsB: Record<string, unknown>[];
    toolCallsA: number;
    toolCallsB: number;
}

/**
 * Capability diff produced when runtime capabilities change.
 */
export interface CapabilityDiff {
    schemaVersion: number;
    diffId: string;
    runtimeId: string;
    beforeSnapshotId: string;
    afterSnapshotId: string;
    addedCapabilities: string[];
    removedCapabilities: string[];
    changedFlags: Record<string, { before: unknown; after: unknown }>;
    requiresConfirmation: boolean;
    timestamp: string;
}

/**
 * Response envelope for capability diff between two runtimes.
 */
export interface CapabilityDiffResponse {
    diff: CapabilityDiff;
    fromRuntime: string;
    toRuntime: string;
    trustBoundaryWidened: boolean;
    trustSensitiveChanges: string[];
}
