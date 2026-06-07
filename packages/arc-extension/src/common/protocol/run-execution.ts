/**
 * Run execution protocol types: live/replay trace streaming, run preflight, and
 * gated run/provider start requests.
 *
 * Extracted from `arc-protocol.ts` (CR-027) and re-exported from it via the barrel,
 * so existing `from '../../common/arc-protocol'` imports continue to work unchanged.
 * `TraceEvent` is back-imported from the barrel (type-only, erased at compile time);
 * `ReplayEvent` comes from the sibling replay-diff module.
 */

import type { TraceEvent } from '../arc-protocol';
import type { ReplayEvent } from './replay-diff';

// ========== Streaming ==========

/**
 * A streaming trace event chunk delivered during live execution.
 * Used by the frontend to update the graph view in real time.
 */
export interface TraceEventChunk {
    /** The event payload. */
    event: TraceEvent;
    /** True when this is the last event in the stream. */
    done: boolean;
}

export type ActiveTraceStreamMode = 'live' | 'replay';

export type ActiveTraceTerminalType =
    | 'RUN_COMPLETED'
    | 'RUN_FAILED'
    | 'RUN_CANCELLED'
    | 'STREAM_END';

export type ActiveTraceStreamState =
    | 'connecting'
    | 'connected'
    | 'reconnecting'
    | 'replaying'
    | 'disconnected'
    | 'error'
    | 'ended'
    | 'cancelled';

export interface ActiveTraceStreamRequest {
    runId: string;
    mode: ActiveTraceStreamMode;
    /** Python web/SSE base URL. Live mode streams /api/runs/{runId}/events; backend may use configured daemon URL when omitted. */
    baseUrl?: string;
    /** Max stream lifetime in milliseconds. Defaults to backend-safe timeout. */
    timeoutMs?: number;
    /** Last received SSE event id for reconnect resume. */
    lastEventId?: number;
}

export interface ActiveTraceStreamStatus {
    runId: string;
    mode: ActiveTraceStreamMode;
    state: ActiveTraceStreamState;
    message?: string;
    baseUrlConfigured?: boolean;
    timestamp: string;
}

/** Live/replay stream chunk compatible with Python SSE JSON event payloads. */
export interface ActiveTraceEventChunk {
    runId: string;
    mode: ActiveTraceStreamMode;
    sequence: number;
    event?: TraceEvent | ReplayEvent | Record<string, unknown>;
    status?: ActiveTraceStreamStatus;
    terminal?: ActiveTraceTerminalType;
    done: boolean;
}

// ========== Run Preflight ==========

export interface RunBlocker {
    code: string;
    message: string;
}

export interface RunCostMetadata {
    paidCallRequired: boolean;
    paidCallAllowed: boolean;
    providerCall: false;
    dryRun?: boolean;
    quota?: Record<string, unknown>;
    provider?: string;
    estimatedCost?: Record<string, unknown> | null;
}

export interface RunPreflightRequest {
    workflow: string;
    prompt?: string;
    runtimeId: string;
    profileId?: string;
    allowPaidCalls?: boolean;
    dryRun: true;
}

export interface RunPreflightResponse {
    workflow: string;
    runtime: string;
    profile?: Record<string, unknown> | null;
    runnable: boolean;
    blockers: RunBlocker[];
    warnings: string[];
    doctorActions: Array<Record<string, unknown>>;
    paidCallRequired: boolean;
    keyRefStatus: Record<string, unknown>;
    exportTargetStatus: Record<string, unknown>;
    dependencyStatus: Record<string, unknown>;
    dryRun: true;
    providerCall: false;
    costMetadata: RunCostMetadata;
}

export interface GatedProviderActionRequest {
    provider: string;
    model?: string;
    prompt: string;
    dryRun?: boolean;
    allowPaidCalls?: boolean;
    confirmProviderCall?: boolean;
}

export interface GatedProviderActionResult {
    success: boolean;
    blocked: boolean;
    dryRun: boolean;
    providerCall: boolean;
    provider?: string;
    model?: string;
    message: string;
    quota?: Record<string, unknown>;
    estimatedCost?: Record<string, unknown> | null;
    data?: Record<string, unknown>;
    error?: Record<string, unknown> | string;
}

export interface StartRunRequest {
    workflow: string;
    prompt?: string;
    runtimeId: string;
    profileId?: string;
    allowPaidCalls?: boolean;
}

export interface StartRunResponse {
    runId: string;
    status: string;
    runtime: string;
    tracePath?: string;
    metadata: Record<string, unknown>;
    costMetadata: RunCostMetadata;
}
