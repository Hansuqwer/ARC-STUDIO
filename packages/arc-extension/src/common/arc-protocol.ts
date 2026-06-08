/**
 * ARC Studio Protocol
 * 
 * Defines the RPC protocol between frontend and backend.
 */

// Import battle protocol types (Phase 34.2)
import type { BattleRun, BattleCandidate, BattleVote, BattleOutcome, EloRating, BattleDetails } from './battle-protocol';
// Replay & Run Diff types live in ./protocol/replay-diff (CR-027); imported here for local
// use in the StreamEnvelope and ArcService declarations below. Re-exported via `export *` below.
import type { ReplayResult, RunDiffResult, CapabilityDiffResponse } from './protocol/replay-diff';
// Run execution types (streaming/preflight/start) live in ./protocol/run-execution (CR-027);
// imported here for local use in ArcService. Re-exported via `export *` below.
import type {
    ActiveTraceStreamRequest,
    ActiveTraceEventChunk,
    RunPreflightRequest,
    RunPreflightResponse,
    GatedProviderActionRequest,
    GatedProviderActionResult,
    StartRunRequest,
    StartRunResponse,
} from './protocol/run-execution';
// Config Tab types live in ./protocol/config-types (CR-027); imported here for local use in
// ArcService. Re-exported via `export *` below.
import type {
    ArcProfileInfo,
    ConfigStatus,
    IsolationProviderInfo,
    IsolationStatus,
    ProviderAccountInfo,
    ProviderAccountUpdate,
    ProviderCatalogEntry,
    ProviderDiagnosticsInfo,
    ProviderKeyRefRequest,
    ProviderModel,
    ProviderQuotaInfo,
    ProviderQuotaResetResult,
    ProviderTestResult,
    SafeConfigUpdate,
} from './protocol/config-types';
// Cockpit schema contracts + graph-linkage types live in ./protocol/contracts-graph (CR-027);
// imported here for local use (ArcService methods, EvidenceSelectionEvent, GraphNodeSelectionEvent).
// Re-exported via `export *` below.
import type {
    EvidenceRef,
    FailureAutopsy,
    GraphNodeData,
    RunContract,
    RunReceipt,
} from './protocol/contracts-graph';
// Runtime status, run-links, and HITL/audit types live in their own ./protocol modules (CR-027);
// imported here for local use in ArcService. Re-exported via `export *` below.
import type { ProviderStatus, RuntimeCapabilitiesResponse } from './protocol/runtime-status';
import type { RunLinksResponse } from './protocol/run-links';
import type { AuditChainInfo, HitlPromptInfo, HitlRespondRequest } from './protocol/hitl-audit';

export const ArcServicePath = '/services/arc';

/**
 * Symbol for ArcService dependency injection token
 */
export const ArcService = Symbol('ArcService');

// Re-export battle protocol types (Phase 34.2)
export type { BattleRun, BattleCandidate, BattleVote, BattleOutcome, EloRating, BattleDetails };

// ========== Enums ==========

/**
 * Error codes for ARC protocol operations.
 *
 * Canonical list defined by ADR-023 and mirrored in Python's
 * `agent_runtime_cockpit.protocol.errors.ArcErrorCode`.
 */
export enum ArcErrorCode {
    WORKSPACE_NOT_FOUND     = 'WORKSPACE_NOT_FOUND',
    NO_RUNTIME_DETECTED     = 'NO_RUNTIME_DETECTED',
    ADAPTER_ERROR           = 'ADAPTER_ERROR',
    ADAPTER_NOT_SUPPORTED   = 'ADAPTER_NOT_SUPPORTED',
    SCHEMA_EXPORT_FAILED    = 'SCHEMA_EXPORT_FAILED',
    WORKFLOW_EXPORT_FAILED  = 'WORKFLOW_EXPORT_FAILED',
    RUN_FAILED              = 'RUN_FAILED',
    RUN_NOT_FOUND           = 'RUN_NOT_FOUND',
    CONTEXT_PROVIDER_ERROR  = 'CONTEXT_PROVIDER_ERROR',
    CONFORMANCE_FAILED      = 'CONFORMANCE_FAILED',
    INVALID_INPUT           = 'INVALID_INPUT',
    INTERNAL_ERROR          = 'INTERNAL_ERROR',
    TIMEOUT                 = 'TIMEOUT',
    NOT_IMPLEMENTED         = 'NOT_IMPLEMENTED',
    PERMISSION_DENIED       = 'PERMISSION_DENIED',
    /**
     * Returned when a concurrent session write is attempted while another write
     * is in progress. The TypeScript-side write mutex serializes IDE writes;
     * this code surfaces when the queue is rejected (e.g. already 1 pending).
     * The Python-side advisory lock (fcntl.flock) is the authoritative
     * data-safety lock and also propagates this code on timeout.
     */
    LOCK_CONTENTION         = 'LOCK_CONTENTION',
    UNKNOWN                 = 'UNKNOWN',

    /** @deprecated ADR-023: use RUN_NOT_FOUND. Removed in v0.3.0. */
    TRACE_NOT_FOUND         = 'TRACE_NOT_FOUND',
    /** @deprecated ADR-023: use RUN_FAILED. Removed in v0.3.0. */
    EXECUTION_FAILED        = 'EXECUTION_FAILED',
    /** @deprecated ADR-023: use INVALID_INPUT. Removed in v0.3.0. */
    PARSE_ERROR             = 'PARSE_ERROR',
    /** @deprecated ADR-023: use WORKSPACE_NOT_FOUND. Removed in v0.3.0. */
    WORKFLOW_NOT_FOUND      = 'WORKFLOW_NOT_FOUND'
}

export function canonicalErrorCode(code: string): ArcErrorCode {
    const legacy: Record<string, ArcErrorCode> = {
        TRACE_NOT_FOUND: ArcErrorCode.RUN_NOT_FOUND,
        EXECUTION_FAILED: ArcErrorCode.RUN_FAILED,
        PARSE_ERROR: ArcErrorCode.INVALID_INPUT,
        WORKFLOW_NOT_FOUND: ArcErrorCode.WORKSPACE_NOT_FOUND
    };
    if (code in legacy) {
        return legacy[code];
    }
    if ((Object.values(ArcErrorCode) as string[]).includes(code)) {
        return code as ArcErrorCode;
    }
    return ArcErrorCode.UNKNOWN;
}

// ========== Error Class ==========

/**
 * Structured error for ARC operations.
 */
export class ArcError extends Error {
    constructor(
        public readonly code: ArcErrorCode,
        message: string,
        public readonly details?: Record<string, any>
    ) {
        super(message);
        this.name = 'ArcError';
        // Restore prototype chain for instanceof checks
        Object.setPrototypeOf(this, new.target.prototype);
    }
}

// ========== Python Daemon ==========

/**
 * Minimal unauthenticated Python daemon health response from `/health`.
 * This endpoint is intentionally not an ArcEnvelope and must not expose run
 * inventory such as active run counts.
 */
export interface PythonDaemonHealth {
    status: 'healthy';
    version: string;
    uptime_seconds: number;
    arc: true;
}

// ========== Execution ==========

/**
 * Options for workflow execution.
 */
export interface ExecutionOptions {
    /**
     * Backend to use for execution.
     * - 'gateway': Use SwarmGraph gateway with real LLM providers
     * - 'stub': Use stub backend for testing without API calls
     * @default 'gateway'
     */
    backend?: 'gateway' | 'stub';

    /**
     * Whether to allow operations that incur API costs.
     * When false, execution will fail if it would make paid API calls.
     * @default true
     */
    costAllowed?: boolean;

    /**
     * Timeout for execution in milliseconds.
     * @default 300000 (5 minutes)
     */
    timeout?: number;

    /**
     * Workspace root directory for execution.
     * If not provided, uses current working directory.
     */
    workspaceRoot?: string;
}

/**
 * Result of a workflow execution.
 */
export interface ExecutionResult {
    /**
     * Unique identifier for this execution run.
     * Format: 'run-sg-{hash}' for SwarmGraph runs.
     */
    runId: string;

    /**
     * Final execution status.
     */
    status: 'completed' | 'failed' | 'running';

    /**
     * Standard output from the execution (if successful).
     */
    output?: string;

    /**
     * Error message (if failed).
     */
    error?: string;

    /**
     * Path to the trace file relative to workspace root.
     * Format: '.arc/traces/{runId}.jsonl'
     */
    tracePath: string;

    /**
     * Execution duration in milliseconds.
     */
    duration?: number;
}

/**
 * Result of workflow cancellation.
 */
export interface CancelResult {
    success: boolean;
    runId: string;
    message: string;
}

// ========== Traces ==========

/**
 * Metadata for a trace file.
 */
export interface TraceFile {
    /**
     * Unique trace identifier (without .jsonl extension).
     */
    id: string;

    /**
     * Absolute path to the trace file.
     */
    path: string;

    /**
     * ISO 8601 timestamp of when the trace was created.
     */
    timestamp: string;

    /**
     * Execution status from the trace file.
     */
    status: 'completed' | 'failed' | 'unknown';

    /**
     * File size in bytes.
     */
    size?: number;

    /**
     * Number of events in the trace.
     */
    eventCount?: number;
}

/**
 * A single event in a trace file.
 *
 * Events follow the AG-UI event format defined in Phase 2 architectural decisions.
 * Each event represents a discrete action during workflow execution.
 * Trace files are JSONL: one TraceEvent JSON object per line.
 */
/**
 * Canonical IDE trace-event types. Mirrors the cross-language event registry
 * (`protocol/fixtures/run-event-registry.json`) so IDE consumers get autocomplete +
 * exhaustiveness over the full event set, not just a handful. `NODE_COMPLETED` and `ERROR`
 * are retained as legacy IDE-only aliases. `TraceEvent.type` keeps a `(string & {})` escape
 * hatch for adapter-specific events. A parity test guards this against registry drift (B2P-02).
 */
export const KNOWN_TRACE_EVENT_TYPES = [
    'AGENT_END', 'AGENT_START', 'BATTLE_CANDIDATE_READY', 'BATTLE_COMPLETED',
    'BATTLE_CONSENSUS_REACHED', 'BATTLE_HITL_REQUIRED', 'BATTLE_STARTED', 'BATTLE_VOTE_COMMITTED',
    'BATTLE_VOTE_REVEALED', 'BUDGET_BROKER_SYNC', 'CAPABILITY_CARD_DECISION',
    'CONSENSUS_DIFFERENTIATOR', 'CONSENSUS_EVAL', 'CONSENSUS_EVAL_RUN', 'CONTEXT_COMPACTED',
    'CONTRACT_ACCEPTED', 'CONTRACT_FULFILLED', 'CONTRACT_PROPOSED', 'CONTRACT_VIOLATED', 'CUSTOM',
    'EVAL_POLICY_APPLIED', 'EVAL_POLICY_RECOMMENDED', 'EVIDENCE_REF_CREATED',
    'FAILURE_AUTOPSY_GENERATED', 'HANDOFF', 'HITL_PROMPT', 'HITL_RESPONSE', 'HITL_TIMEOUT',
    'MCP_CALL_DECISION', 'MESSAGE', 'MESSAGE_CHUNK', 'MODEL_CHANGED', 'NETWORK_DENIED',
    'NODE_FAILED', 'NODE_STARTED', 'NODE_UPDATE', 'OBSERVABILITY_EXPORT_STARTED', 'PAID_CALL_DENIED',
    'PERMISSION_DENIED', 'POLICY_BYPASS_WARNING', 'PRICING_FEED_REFRESHED', 'QUOTA_WARNING', 'RAW',
    'RECEIPT_GENERATED', 'RUN_CANCELLED', 'RUN_COMPLETED', 'RUN_FAILED', 'RUN_STARTED',
    'SHELL_DENIED', 'STATE_SNAPSHOT', 'STEP_COMPLETED', 'STEP_FAILED', 'STEP_STARTED',
    'SWARMGRAPH_CONSENSUS', 'SWARMGRAPH_COST', 'SWARMGRAPH_TOPOLOGY', 'TEXT_MESSAGE_CHUNK',
    'TEXT_MESSAGE_CONTENT', 'TEXT_MESSAGE_END', 'TEXT_MESSAGE_START', 'TOOL_CALL', 'TOOL_CALL_ARGS',
    'TOOL_CALL_END', 'TOOL_CALL_ERROR', 'TOOL_CALL_RESULT', 'TOOL_CALL_START', 'TOOL_END',
    'TOOL_OUTPUT_VIRTUALIZED', 'TRUST_DENIED',
    // Legacy IDE-only aliases (not in the canonical registry, retained for back-compat):
    'NODE_COMPLETED', 'ERROR',
] as const;

export type KnownTraceEventType = (typeof KNOWN_TRACE_EVENT_TYPES)[number];

/**
 * Terminal stream markers. The literal list is typed against the canonical event union so a typo
 * is a compile error (B2P-02b); the exported Set is `ReadonlySet<string>` so `.has(event.type)`
 * still accepts adapter-specific event strings. `STREAM_END` is a stream-control sentinel.
 */
const TERMINAL_TRACE_EVENT_LIST: readonly (KnownTraceEventType | 'STREAM_END')[] = [
    'RUN_COMPLETED',
    'RUN_FAILED',
    'RUN_CANCELLED',
    'STREAM_END',
];
export const TERMINAL_TRACE_EVENT_TYPES: ReadonlySet<string> = new Set(TERMINAL_TRACE_EVENT_LIST);

export interface TraceEvent {
    /**
     * Type of event.
     * - RUN_STARTED:    Workflow execution began
     * - NODE_COMPLETED: A graph node finished execution
     * - MESSAGE:        A message was sent/received
     * - RUN_COMPLETED:  Workflow execution succeeded
     * - RUN_FAILED:     Workflow execution failed
     * - ERROR:          An error occurred during execution
     * Runtime-specific trace event strings are allowed for real adapter events.
     */
    type: KnownTraceEventType | (string & {});

    /**
     * ISO 8601 timestamp when the event occurred.
     */
    timestamp: string;

    /**
     * Run ID this event belongs to.
     */
    runId: string;

    /**
     * Sequence number for ordering events (0-indexed).
     */
    sequence: number;

    /**
     * Event-specific data. Structure varies by event type.
     */
    data: Record<string, any>;
}

/**
 * Complete trace data including all events and metadata.
 *
 * Trace files use JSONL format where each line is a TraceEvent.
 * This interface represents the parsed and aggregated trace data.
 */
export interface TraceData {
    /**
     * Unique trace identifier.
     */
    id: string;

    /**
     * Identifier of the workflow that was executed.
     */
    workflowId: string;

    /**
     * Runtime that executed the workflow ('swarmgraph' or 'langgraph').
     */
    runtime: string;

    /**
     * Final execution status.
     */
    status: string;

    /**
     * ISO 8601 timestamp when execution started.
     */
    startedAt: string;

    /**
     * ISO 8601 timestamp when execution ended.
     */
    endedAt?: string;

    /**
     * Array of all events that occurred during execution.
     * Events are ordered by sequence number.
     */
    events: TraceEvent[];

    /**
     * Additional metadata about the execution.
     * May include: model names, token counts, costs, etc.
     */
    metadata: Record<string, any>;
}

/**
 * Result of validating a trace file.
 */
export interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
    /** Detected file format. */
    format: 'json' | 'jsonl' | 'unknown';
}

// ========== Workflows ==========

/**
 * Information about a detected workflow in the workspace.
 */
export interface WorkflowInfo {
    /**
     * Type of workflow runtime.
     */
    type: 'langgraph' | 'swarmgraph';

    /**
     * Absolute path to the workflow file or executable.
     */
    path: string;

    /**
     * Human-readable name of the workflow.
     */
    name: string;

    /**
     * Optional description of the workflow.
     */
    description?: string;
}

// ========== Runtime Adapter Status (extracted to ./protocol/runtime-status) ==========
export * from './protocol/runtime-status';

// ========== Config Tab Types (extracted to ./protocol/config-types) ==========
export * from './protocol/config-types';

// ========== Run Links Types (extracted to ./protocol/run-links) ==========
export * from './protocol/run-links';

// ========== Cockpit Schema Contracts + Stable IDs/Graph (extracted to ./protocol/contracts-graph) ==========
export * from './protocol/contracts-graph';

// ========== HITL + Audit (extracted to ./protocol/hitl-audit) ==========
export * from './protocol/hitl-audit';

// ========== Replay & Run Diff (extracted to ./protocol/replay-diff) ==========
export * from './protocol/replay-diff';

/**
 * Degradation manifest when stable IDs are missing.
 */
export interface DegradationManifest {
    totalEvents: number;
    missingNodeIds: number;
    missingMessageIds: number;
    missingToolCallIds: number;
    missingEvidenceRefs: number;
    isDegraded: boolean;
    crossLinkingAvailable: boolean;
}

/**
 * Graph node selection event for cross-surface linking.
 */
export interface GraphNodeSelectionEvent {
    nodeId: string;
    nodeData: GraphNodeData;
    linkedMessageIds: string[];
    linkedEvidenceIds: string[];
    linkedToolCallIds: string[];
}

// ========== Streaming, Run Preflight & Start (extracted to ./protocol/run-execution) ==========
export * from './protocol/run-execution';

// ========== Service Interface ==========

// ========== Session Bridge Types (Phase 43) ==========

/**
 * Summary view of a local chat session (read-only, redacted).
 * Returned by listChatSessions().
 */
export interface ChatSessionSummary {
    id: string;
    mode: string;
    runtime_mode: string;
    updated_at: string;
    message_count: number;
}

/**
 * Detailed view of a local chat session (read-only, redacted).
 * Returned by getChatSession().
 */
export interface ChatSessionDetail {
    id: string;
    mode: string;
    runtime_mode: string;
    profile_id: string;
    isolation_id: string;
    created_at: string;
    updated_at: string;
    history: Array<Record<string, string>>;
}

export interface DaemonWriteResult {
    ok: boolean;
    session_id?: string;
    operation?: 'write' | 'delete' | 'update';
    message?: string;
}

export interface EditFilePlanInfo {
    path: string;
    command: string[];
    original_exists: boolean;
    original_hash: string;
    replacement_hash?: string | null;
    patch_hash?: string | null;
    allowed: boolean;
    reason: string;
    classification: string;
}

export interface EditPlanInfo {
    version: number;
    plan_id: string;
    workspace_root: string;
    policy: string;
    path: string;
    command: string[];
    original_exists: boolean;
    original_hash: string;
    replacement_hash: string;
    allowed: boolean;
    reason: string;
    classification: string;
    plan_path?: string | null;
    created_at: string;
    status?: string;
    files: EditFilePlanInfo[];
}

export interface EditPlanListResult {
    plans: EditPlanInfo[];
    count: number;
}

export interface EditPlanApprovalResult {
    version: number;
    approval_id: string;
    plan_id: string;
    token_hash: string;
    plan_hash: string;
    approved_at: string;
}

export interface EditPlanDiffResult {
    plan_id: string;
    status: string;
    diff: string;
    diff_truncated: boolean;
    binary: boolean;
    max_bytes: number;
    files: EditFilePlanInfo[];
}

export interface EditPlanApplyResult {
    applied: boolean;
    reason: string;
    transaction_id?: string | null;
    plan?: EditPlanInfo;
    audit_events?: Array<Record<string, unknown>>;
}

/**
 * Main service interface for ARC Studio backend operations.
 *
 * Implementations handle:
 * - Executing SwarmGraph and LangGraph workflows
 * - Managing trace files in .arc/traces/
 * - Detecting workflow definitions in the workspace
 * - Streaming execution events to the frontend
 */
export interface ArcService {
    /**
     * Execute a SwarmGraph workflow with the given prompt.
     *
     * Spawns a subprocess to run the SwarmGraph CLI and captures
     * the execution trace in JSONL format. The trace file is written to
     * .arc/traces/ and can be retrieved later for visualization.
     *
     * @param prompt   - The user prompt to execute
     * @param options  - Optional execution configuration
     * @returns Promise resolving to execution result with run ID and trace path
     * @throws {ArcError} INVALID_INPUT if prompt is empty or too long
     * @throws {ArcError} RUN_FAILED if the CLI is unavailable
     * @throws {ArcError} TIMEOUT if execution exceeds the configured timeout
     *
     * @example
     * ```typescript
     * const result = await arcService.executeWorkflow(
     *   "What is the weather?",
     *   { backend: 'gateway', costAllowed: true }
     * );
     * console.log(`Run ID: ${result.runId}`);
     * console.log(`Trace: ${result.tracePath}`);
     * ```
     */
    executeWorkflow(prompt: string, options?: ExecutionOptions): Promise<ExecutionResult>;

    /**
     * Cancel a running workflow execution.
     *
     * Sends SIGTERM to the subprocess identified by runId.
     *
     * @param runId - The run ID returned by executeWorkflow
     * @returns Promise resolving to cancellation result
     */
    cancelWorkflow(runId: string): Promise<CancelResult>;

    /**
     * Get list of all trace files from .arc/traces/ directory.
     *
     * Returns metadata for each trace file including ID, timestamp, and status.
     * Files are sorted by timestamp (most recent first).
     *
     * @returns Promise resolving to array of trace file metadata
     * @throws {ArcError} UNKNOWN if the traces directory cannot be read
     *
     * @example
     * ```typescript
     * const traces = await arcService.getTraces();
     * traces.forEach(trace => {
     *   console.log(`${trace.id}: ${trace.status} at ${trace.timestamp}`);
     * });
     * ```
     */
    getTraces(): Promise<TraceFile[]>;

    /**
     * Read and parse a specific trace file by ID.
     *
     * Loads the complete trace data including all events, metadata, and
     * execution results. The trace file must exist in .arc/traces/.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Promise resolving to complete trace data
     * @throws {ArcError} INVALID_INPUT if traceId is malformed
     * @throws {ArcError} RUN_NOT_FOUND if the file does not exist
     * @throws {ArcError} INVALID_INPUT if the file cannot be parsed
     *
     * @example
     * ```typescript
     * const trace = await arcService.readTrace('run-sg-abc123');
     * console.log(`Workflow: ${trace.workflowId}`);
     * console.log(`Events: ${trace.events.length}`);
     * ```
     */
    readTrace(traceId: string): Promise<TraceData>;

    /**
     * Stream trace events from a trace file one event at a time.
     *
     * Reads the JSONL file line-by-line and yields each parsed TraceEvent.
     * Useful for large traces where loading all events at once is expensive.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Async iterable of TraceEvent objects
     * @throws {ArcError} INVALID_INPUT if traceId is malformed
     * @throws {ArcError} RUN_NOT_FOUND if the file does not exist
     * @throws {ArcError} INVALID_INPUT if a line cannot be parsed
     */
    streamTrace(traceId: string): Promise<AsyncIterable<TraceEvent>>;

    /** Stream active run events with explicit live vs replay and terminal semantics. */
    streamActiveTrace(request: ActiveTraceStreamRequest): Promise<AsyncIterable<ActiveTraceEventChunk>>;

    /** JSON-RPC-safe active run stream snapshot for browser clients. */
    readActiveTraceStream(request: ActiveTraceStreamRequest): Promise<ActiveTraceEventChunk[]>;

    /** Cancel a backend active stream proxy for a run. Does not cancel the run itself. */
    cancelActiveTraceStream(runId: string): Promise<{ success: boolean; message: string }>;

    /**
     * Validate the format and content of a trace file.
     *
     * Checks required fields, event structure, and JSONL format compliance.
     *
     * @param traceId - The trace ID (without .jsonl extension)
     * @returns Promise resolving to validation result with errors and warnings
     */
    validateTrace(traceId: string): Promise<ValidationResult>;

    /**
     * Detect workflow definitions in the current workspace.
     *
     * Scans the workspace for:
     * - SwarmGraph CLI installations
     * - LangGraph StateGraph definitions (via AST analysis)
     * - Other supported workflow types
     *
     * @returns Promise resolving to array of detected workflows
     * @throws {ArcError} UNKNOWN if the workspace cannot be scanned
     *
     * @example
     * ```typescript
     * const workflows = await arcService.detectWorkflows();
     * workflows.forEach(wf => {
     *   console.log(`Found ${wf.type} workflow: ${wf.name} at ${wf.path}`);
     * });
     * ```
     */
    detectWorkflows(): Promise<WorkflowInfo[]>;

    /**
     * List runtime capability reports for the current workspace.
     * Returns detected runtimes with their readiness status.
     */
    listRuntimeCapabilities(): Promise<RuntimeCapabilitiesResponse>;

    /** Dry-run a runtime launch through the Python CLI. No provider calls are made. */
    preflightRun(request: RunPreflightRequest): Promise<RunPreflightResponse>;

    /** Narrow provider action bridge. Dry-run by default; provider calls require explicit gates. */
    runGatedProviderAction(request: GatedProviderActionRequest): Promise<GatedProviderActionResult>;

    /** Start a runtime launch through the Python CLI after explicit user action. */
    startRun(request: StartRunRequest): Promise<StartRunResponse>;

    /**
     * Get provider configuration status.
     * @param provider - Provider ID (e.g. 'openai', 'anthropic')
     * @param baseUrl - Optional base URL override
     */
    getProviderStatus(provider: string, baseUrl?: string): Promise<ProviderStatus>;

    /**
     * Get current workspace status (frontend/backend paths).
     */
    getWorkspaceStatus(): Promise<{ frontendPath: string; backendPath: string; source: string }>;

    // ========== Config Tab Methods (Session B) ==========

    /**
     * Get current config status with all secret values stripped.
     * Returns runtime config, provider key statuses (source only, no raw keys),
     * workspace trust state, and current mode.
     * Gracefully handles unavailable backend.
     */
    getConfigStatus(): Promise<ConfigStatus>;

    /**
     * Save safe config fields only.
     * Rejects any attempt to save secret values.
     * Only non-secret fields from SafeConfigUpdate are accepted.
     */
    saveConfig(update: SafeConfigUpdate): Promise<{ success: boolean; message: string }>;

    /** List non-secret run profiles from Python CLI. */
    listProfiles(): Promise<ArcProfileInfo[]>;

    /** Get active isolation status. Falls back safely if CLI unavailable. */
    getIsolationStatus(): Promise<IsolationStatus>;

    /** List isolation providers. No secrets or host env values are returned. */
    listIsolationProviders(): Promise<IsolationProviderInfo[]>;

    /** List provider catalog entries. No raw credentials are returned. */
    getProviderCatalog(): Promise<ProviderCatalogEntry[]>;

    /** Get provider diagnostics metadata. No credential values are returned. */
    getProviderDiagnostics(): Promise<ProviderDiagnosticsInfo>;

    /** Get provider quota/counter metadata. No credential values are returned. */
    getProviderQuota(provider?: string): Promise<ProviderQuotaInfo>;

    /** Reset local provider quota counters only. No provider network calls are made. */
    resetProviderQuota(): Promise<ProviderQuotaResetResult>;

    /** Save an env-var provider key reference. Rejects raw key material. */
    setProviderKeyRef(request: ProviderKeyRefRequest): Promise<{ success: boolean; message: string }>;

    /** Remove an env-var provider key reference by provider id or account id. */
    unsetProviderKeyRef(providerOrAccountId: string): Promise<{ success: boolean; message: string }>;

    /** Test provider connection and configuration. Calls `arc providers test <id> --json`. */
    testProvider(providerId: string): Promise<ProviderTestResult>;

    /** List available models for a provider. Calls `arc providers models [--provider <id>] --json`. */
    listProviderModels(providerId?: string): Promise<ProviderModel[]>;

    /** Get a single provider account by ID. Delegates to daemon HTTP when available. */
    getProviderAccount(accountId: string): Promise<ProviderAccountInfo>;

    /** Update provider account fields (label, default_model, base_url, enabled). Trust-checked. */
    updateProviderAccount(accountId: string, update: ProviderAccountUpdate): Promise<ProviderAccountInfo>;

    // ========== Run Links Methods (Session B7) ==========

    /**
     * Get cross-linked event chains for a run.
     * Calls the Python /api/runs/{id}/links endpoint via CLI.
     * Returns node, message, tool call, and evidence chains.
     */
    getRunLinks(runId: string, filter?: string, stableId?: string): Promise<RunLinksResponse>;

    // ========== Run Details (Cockpit Cards) ==========

    /**
     * Get the run receipt for a completed/failed/cancelled run.
     */
    getRunReceipt(runId: string): Promise<RunReceipt>;

    /**
     * Get the failure autopsy for a failed run. Returns null if no autopsy exists.
     */
    getRunAutopsy(runId: string): Promise<FailureAutopsy | null>;

    /**
     * Get the run contract for a run. Returns null if no contract exists.
     */
    getRunContract(runId: string): Promise<RunContract | null>;

    // ========== HITL Methods (Slice 7) ==========

    /**
     * List pending HITL prompts that need user response.
     * Calls `arc hitl pending --json` via the Python CLI.
     */
    listPendingHitlPrompts(): Promise<HitlPromptInfo[]>;

    /**
     * Respond to a HITL prompt with approve/reject/modify.
     * Calls `arc hitl respond <promptId> --decision <decision> --json` via the Python CLI.
     */
    respondHitlPrompt(request: HitlRespondRequest): Promise<{ success: boolean; message: string }>;

    // ========== Audit Methods (Slice 7) ==========

    /**
     * Get audit chain info for a run.
     * Calls `arc audit verify <auditPath> --json` via the Python CLI.
     */
    getAuditChainInfo(runId: string): Promise<AuditChainInfo | null>;

    // ========== Replay Methods (Slice 7) ==========

    /**
     * Replay stored trace events for a run.
     * Calls `arc runs replay <runId> --json` via the Python CLI.
     */
    replayRun(runId: string): Promise<ReplayResult>;

    /** Diff two stored runs using the Python CLI. */
    diffRuns(runAId: string, runBId: string): Promise<RunDiffResult>;

    /** Get configured Python daemon URL from ARC_PYTHON_DAEMON_URL env var. */
    getPythonDaemonUrl(): Promise<string | undefined>;

    /**
     * Discover a running Python daemon by probing the default loopback URL
     * (http://127.0.0.1:7777/health) with a short timeout.
     * Returns the base URL if the daemon responds, undefined otherwise.
     * Only probes loopback addresses; no outbound connections.
     */
    discoverPythonDaemonUrl(): Promise<string | undefined>;

    // ========== Capability Diff (Session B) ==========

    /**
     * Get capability diff between two runtimes.
     * Compares capabilities of fromRuntime vs toRuntime and returns
     * added/removed capabilities with trust boundary analysis.
     */
    getCapabilityDiff(fromRuntime: string, toRuntime: string): Promise<CapabilityDiffResponse>;

    // ========== Battle Methods (Phase 34.2) ==========

    /**
     * List battle runs with optional filtering.
     * Calls `arc battle list --json` via the Python CLI.
     * 
     * @param options - Optional filters for status and limit
     * @returns Promise resolving to array of battle runs
     * @throws {ArcError} UNKNOWN if the battle store cannot be read
     */
    listBattles(options?: { status?: string; limit?: number }): Promise<BattleRun[]>;

    /**
     * Get detailed information about a specific battle.
     * Calls `arc battle show <battleId> --json` via the Python CLI.
     * 
     * @param battleId - The battle ID to retrieve
     * @returns Promise resolving to battle details with candidates, votes, and outcome
     * @throws {ArcError} RUN_NOT_FOUND if the battle does not exist
     */
    getBattleDetails(battleId: string): Promise<BattleDetails>;

    /**
     * Get ELO leaderboard rankings for battle models.
     * Calls `arc battle leaderboard --json` via the Python CLI.
     * 
     * @param limit - Optional limit on number of rankings to return
     * @returns Promise resolving to array of ELO ratings
     * @throws {ArcError} UNKNOWN if the ELO store cannot be read
     */
    getLeaderboard(limit?: number): Promise<EloRating[]>;

    // ========== Session Bridge Methods (Phase 43 — read-only) ==========

    /**
     * List local chat sessions (read-only, redacted).
     * Delegates to SessionBridgeService which calls `arc studio sessions --json`.
     * Returns empty array if no sessions exist or CLI is unavailable.
     * IDE write/import is deferred until advisory locking is verified.
     */
    listChatSessions(): Promise<ChatSessionSummary[]>;

    /**
     * Get a single chat session by ID (read-only, redacted).
     * Delegates to SessionBridgeService which calls
     * `arc studio sessions show <id> --json`.
     * @throws {ArcError} RUN_NOT_FOUND if session does not exist.
     * @throws {ArcError} INVALID_INPUT if sessionId contains unsafe characters.
     */
    getChatSession(sessionId: string): Promise<ChatSessionDetail>;

    // ========== Session Write Bridge Methods (Phase 46) ==========

    /**
     * Import (create or overwrite) a session from the IDE.
     * Pipes the validated payload to `arc studio sessions write --json` via stdin.
     * History is truncated to the last 200 entries before sending.
     * Payload size is capped at 512 KB on the Python side.
     * Writes are serialized through a per-workspace TS mutex (LOCK_CONTENTION
     * on concurrent attempt) and the Python-side advisory lock (fcntl.flock).
     *
     * @throws {ArcError} INVALID_INPUT if sessionId is unsafe or payload is invalid.
     * @throws {ArcError} PERMISSION_DENIED if workspace is untrusted.
     * @throws {ArcError} LOCK_CONTENTION if a write is already in progress.
     */
    importSession(payload: ChatSessionDetail): Promise<{ ok: boolean; id: string; message: string }>;

    /**
     * Delete a session by ID from the IDE.
     * Calls `arc studio sessions delete <id> --json`.
     * Requires workspace trust.
     *
     * @throws {ArcError} INVALID_INPUT if sessionId is unsafe.
     * @throws {ArcError} RUN_NOT_FOUND if session does not exist.
     * @throws {ArcError} PERMISSION_DENIED if workspace is untrusted.
     * @throws {ArcError} LOCK_CONTENTION if advisory lock cannot be acquired.
     */
    deleteSession(sessionId: string): Promise<{ ok: boolean; message: string }>;

    /**
     * Update a single safe field on a session from the IDE.
     * Allowed fields: mode, runtime_mode, profile_id, isolation_id.
     * Calls `arc studio sessions update <id> --field <field> --value <value> --json`.
     * Requires workspace trust.
     *
     * @throws {ArcError} INVALID_INPUT if sessionId, field, or value is unsafe.
     * @throws {ArcError} RUN_NOT_FOUND if session does not exist.
     * @throws {ArcError} PERMISSION_DENIED if workspace is untrusted.
     * @throws {ArcError} LOCK_CONTENTION if advisory lock cannot be acquired.
     */
    updateSessionField(sessionId: string, field: string, value: string): Promise<{ ok: boolean; message: string }>;

    /** Read-only MCP workbench status via CLI bridge */
    getMcpWorkbenchStatus(): Promise<McpWorkbenchStatus>;
    /** Read-only workspace inventory via CLI bridge */
    getWorkspaceInventory(options?: { suffix?: string; maxEntries?: number }): Promise<WorkspaceInventory>;
    /** Read-only testbench detection via CLI bridge */
    detectTestbench(commandOverride?: string): Promise<TestbenchDetection>;
    /** Run a detected test command through the local-safe sandbox policy (network/destructive denied). */
    runTestbench(command: string): Promise<TestbenchRunResult>;
    /** Discover AGENTS.md files in the workspace (R-AUDIT16) — real producer for ArcContextDrawer. */
    discoverAgentsMd(): Promise<AgentsMdEntry[]>;
    /** Path-confined workspace text search (R-AUDIT18) — real producer for the IDE search panel. */
    searchWorkspace(query: string): Promise<WorkspaceSearchHit[]>;
    /** Read-only CI check status via CLI bridge */
    getCiCheckStatus(): Promise<CiCheckStatus>;

    /** Metadata-only saved edit-plan list via CLI bridge. No replacement content is returned. */
    listEditPlans(limit?: number): Promise<EditPlanListResult>;
    /** Metadata-only saved edit-plan detail via CLI bridge. No replacement content is returned. */
    showEditPlan(planId: string): Promise<EditPlanInfo>;
    /** Scoped local approval for an exact saved edit-plan metadata hash. */
    approveEditPlan(planId: string, token: string): Promise<EditPlanApprovalResult>;
    /** Real saved edit-plan diff content with caps; no replacement body is returned. */
    diffEditPlan(planId: string, maxBytes?: number): Promise<EditPlanDiffResult>;
    /** Apply a saved edit plan through Python edit/sandbox/transaction gates. */
    applyEditPlan(planId: string, content: string, token: string): Promise<EditPlanApplyResult>;

    /** Sandbox-gated MCP server inspect via sandbox run */
    sandboxInspect(command: string[], policy?: string): Promise<SandboxInspectResult>;

    /** Capability Card enforcement decisions for a run (CAPABILITY_CARD_DECISION events) */
    getCapabilityCardSummary(runId: string): Promise<CapabilityCardSummary>;
    /** Recent MCP outbound call decisions (MCP_CALL_DECISION events) from .arc/mcp/decisions.jsonl */
    getMcpDecisions(opts?: { limit?: number; since?: string }): Promise<McpDecisionList>;
    /**
     * Invoke a single MCP tool in-process through the per-call risk gate (loopback, no network).
     * Requires workspace trust; returns the tool's structured result + risk metadata.
     */
    invokeMcpTool(tool: string, args?: Record<string, unknown>): Promise<McpToolInvokeResult>;
    /** Mobile Runtime SDK status: capabilities list + doctor health (simulator/mock only). */
    getMobileStatus(): Promise<MobileStatus>;
}

export interface MobileCapabilityEntry {
    id: string;
    name: string;
    category: string;
    platforms: string[];
    approval_mode: string;
    simulator_supported: boolean;
}

export interface MobileStatus {
    available: boolean;
    capabilities: MobileCapabilityEntry[];
    doctor: { ok: boolean; message: string };
    error?: string;
}

export interface CapabilityCardDecision {
    action: string;
    decision: 'allow' | 'deny' | 'warn';
    reason: string;
    cardId?: string;
    cardHash?: string;
    entityType?: string;
    mode: 'off' | 'warn' | 'strict';
    correlationId?: string;
    remediation?: string;
}

export interface CapabilityCardSummary {
    runId: string;
    decisions: CapabilityCardDecision[];
    mode: 'off' | 'warn' | 'strict';
}

export interface McpDecisionEntry {
    serverId: string;
    toolName: string;
    decision: 'allow' | 'deny' | 'warn';
    riskScore: 'low' | 'medium' | 'high' | 'critical';
    policy: string;
    reason: string;
    timestamp: number;
    correlationId?: string;
}

export interface McpDecisionList {
    decisions: McpDecisionEntry[];
    total: number;
}

// Phase 78/79/80 follow-up: read-only telemetry types
export interface McpToolInvokeResult {
    tool: string;
    /** True when the tool ran and returned an ok envelope; false on deny/error. */
    ok: boolean;
    /** The tool's `data` payload when ok. */
    data?: unknown;
    /** Risk level from the per-call risk gate, when present. */
    riskLevel?: string;
    error?: string;
}

export interface McpWorkbenchStatus {
    workspace: string;
    serverCreatable: boolean;
    serverBlocker?: string | null;
    tools: string[];
    resources: string[];
    trust: { level: string; reason?: string | null; markerPath?: string | null; warning?: string | null };
    diagnostic: string;
}

export interface WorkspaceInventoryFile {
    path: string;
    size: number | null;
    suffix: string;
    provenance: string;
    error?: string;
}

export interface WorkspaceInventory {
    workspace: string;
    files: { count: number; totalSize: number; entries: WorkspaceInventoryFile[]; truncated?: boolean };
    git: { provenance: string; present?: boolean; branch?: string | null; commit?: string | null; commitCount?: number | null; dirty?: boolean; gitDir?: string; degraded?: boolean; reason?: string };
    traces: { count: number; entries: Array<{ name: string; size: number; provenance: string }> };
    mcpResources: Array<{ name?: string; provenance: string; present?: boolean; reason?: string }>;
    symbols?: { count: number; entries: Array<{ path: string; language: string; kind: string; name: string; qualname: string; line: number; provenance: string }>; errors: Array<{ path: string; error: string }>; truncated: boolean; provenance: string };
}

export interface TestbenchDetection {
    workspace: string;
    detected: Array<{ command?: string; source: string; cwd?: string; confidence: string; runner?: string; reason?: string; script?: string }>;
    count: number;
}

export interface TestbenchRunResult {
    command: string;
    ok?: boolean;
    /** Whether the sandbox policy allowed the command (false => blocked, not executed). */
    allowed: boolean;
    classification?: string;
    /** Process exit code when executed; null when blocked or unknown. */
    exitCode?: number | null;
    auditPath?: string;
    error?: string;
}

/** A discovered AGENTS.md file + its metadata (R-AUDIT16). */
export interface AgentsMdEntry {
    path: string;
    sha256: string;
    sizeBytes: number;
    overCap: boolean;
    isOverride: boolean;
    likelyLlmGenerated: boolean;
}

/** A single path-confined workspace-search hit (R-AUDIT18). */
export interface WorkspaceSearchHit {
    file: string;
    line: number;
    match: string;
}

export interface CiCheckStatus {
    private: boolean;
    workspace: string;
    checks: Record<string, Record<string, unknown>>;
    overall: string;
    checkedAt?: string;
}

export interface SandboxInspectResult {
    command: string[];
    classification: string;
    decision: string;
    policy: string;
    tools?: Array<{ name: string; description: string }>;
    resources?: Array<{ uriTemplate: string; name: string; description: string }>;
    prompts?: Array<{ name: string; description: string }>;
    stderr?: string | null;
}
