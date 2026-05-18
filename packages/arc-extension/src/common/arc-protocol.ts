/**
 * ARC Studio Protocol
 * 
 * Defines the RPC protocol between frontend and backend.
 */

export const ArcServicePath = '/services/arc';

/**
 * Symbol for ArcService dependency injection token
 */
export const ArcService = Symbol('ArcService');

// ========== Enums ==========

/**
 * Error codes for ARC protocol operations.
 */
export enum ArcErrorCode {
    INVALID_INPUT       = 'INVALID_INPUT',
    TRACE_NOT_FOUND     = 'TRACE_NOT_FOUND',
    EXECUTION_FAILED    = 'EXECUTION_FAILED',
    PARSE_ERROR         = 'PARSE_ERROR',
    WORKFLOW_NOT_FOUND  = 'WORKFLOW_NOT_FOUND',
    PERMISSION_DENIED   = 'PERMISSION_DENIED',
    TIMEOUT             = 'TIMEOUT',
    UNKNOWN             = 'UNKNOWN'
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
export type KnownTraceEventType =
    | 'RUN_STARTED'
    | 'NODE_COMPLETED'
    | 'MESSAGE'
    | 'RUN_COMPLETED'
    | 'RUN_FAILED'
    | 'ERROR';

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

// ========== Runtime Adapter Status (ported from arc-core) ==========

/**
 * A doctor action for a runtime capability report.
 */
export interface DoctorAction {
    id: string;
    label: string;
    description: string;
    command: string;
    safe_to_auto_run: boolean;
}

/**
 * Capability report for a runtime adapter.
 */
export interface RuntimeCapabilityReport {
    runtime_id: string;
    runtimeId?: string;
    detected: boolean;
    can_run: boolean;
    canRun?: boolean;
    availability: string;
    reason?: string | null;
    detected_artifacts: string[];
    detectedArtifacts?: string[];
    required_env: string[];
    requiredEnv?: string[];
    version?: string | null;
    requires_paid_calls: boolean;
    requiresPaidCalls?: boolean;
    doctor_actions: DoctorAction[];
    doctorActions?: DoctorAction[];
    metadata?: Record<string, unknown>;
    traceMetadata?: Record<string, unknown>;
    gates?: Record<string, unknown>;
    realRuntimeGate?: boolean;
    providerBacked?: boolean;
}

/**
 * Response envelope for runtime capability listing.
 */
export interface RuntimeCapabilitiesResponse {
    workspace: string;
    auto_priority: string[];
    runtimes: RuntimeCapabilityReport[];
}

/**
 * Provider configuration status for the adapter status widget.
 * Secrets are never exposed as raw values — only source/status metadata.
 */
export interface ProviderStatus {
    provider: string;
    display_name?: string;
    enabled?: boolean;
    dry_run?: boolean;
    base_url_configured?: boolean;
    baseUrlConfigured: boolean;
    api_key_configured?: boolean;
    apiKeyConfigured: boolean;
    apiKeySource?: string;
    runtimeAvailable: boolean;
    message: string;
}

// ========== Config Tab Types (Session B) ==========

/**
 * Safe provider key status shown in Config tab.
 * Never contains raw key values — only source and configured status.
 */
export interface SafeProviderKeyStatus {
    provider: string;
    displayName: string;
    configured: boolean;
    source: 'keyring' | 'env' | 'file' | 'unset';
    defaultModel?: string;
    envOverride?: string;
}

export type ProviderAuthKind =
    | 'api_key'
    | 'bearer_token'
    | 'oauth_device'
    | 'oauth_web'
    | 'web_session'
    | 'local'
    | 'research_only';

export type ProviderCatalogStatus =
    | 'supported'
    | 'env_ref_only'
    | 'oauth_planned'
    | 'research_only'
    | 'not_recommended';

/**
 * Provider auth catalog entry. Contains only metadata, never raw credentials.
 */
export interface ProviderCatalogEntry {
    id: string;
    display_name: string;
    displayName?: string;
    category: string;
    auth_kind: ProviderAuthKind;
    authKind?: ProviderAuthKind;
    credential_label: string;
    credentialLabel?: string;
    env_key_names: string[];
    envKeyNames?: string[];
    default_base_url: string;
    defaultBaseUrl?: string;
    docs_url: string;
    docsUrl?: string;
    supports_chat: boolean;
    supports_tools: boolean;
    supports_embeddings: boolean;
    supports_images: boolean;
    supports_web_auth: boolean;
    status: ProviderCatalogStatus;
    warnings: string[];
}

export interface ProviderDiagnosticsInfo {
    providers?: Record<string, unknown>[];
    routing?: Record<string, unknown>;
    accounts?: Record<string, unknown>[];
    status?: Record<string, unknown>;
    warnings?: string[];
    metadata?: Record<string, unknown>;
}

export interface ProviderQuotaInfo {
    provider?: string;
    accounts?: Record<string, unknown>[];
    quota?: Record<string, unknown>;
    counters?: Record<string, unknown>;
    warnings?: string[];
    metadata?: Record<string, unknown>;
}

export interface ProviderQuotaResetResult {
    success: boolean;
    message: string;
}

/**
 * Request to save a provider key reference. envVar is a variable name only.
 */
export interface ProviderKeyRefRequest {
    provider: string;
    envVar: string;
    label?: string;
    model?: string;
}

/**
 * Workspace trust status for Config tab.
 */
export interface TrustStatus {
    trusted: boolean;
    workspacePath: string;
    trustLevel: 'trusted' | 'untrusted' | 'auto' | 'unknown';
    reason?: string;
}

/**
 * Safe runtime config snapshot for Config tab display.
 * Contains only non-secret fields.
 */
export interface SafeRuntimeConfig {
    defaultRuntime: string;
    autoDetect: boolean;
    fallback: string;
    isolation: string;
    timeoutSeconds: number;
    allowPaidCalls: boolean;
    dryRun: boolean;
    routingMode: string;
}

/**
 * Full config status response for Config tab.
 * All secret values are stripped; only source/status metadata included.
 */
export interface ConfigStatus {
    workspace: TrustStatus;
    runtime: SafeRuntimeConfig;
    providers: SafeProviderKeyStatus[];
    mode: 'plan' | 'build' | 'auto';
    selectedProfile?: string;
    backendAvailable: boolean;
    backendMessage?: string;
}

/**
 * Safe config fields that can be saved from the Config tab.
 * Excludes all secret values.
 */
export interface SafeConfigUpdate {
    defaultRuntime?: string;
    mode?: 'plan' | 'build' | 'auto';
    isolation?: string;
    allowPaidCalls?: boolean;
    dryRun?: boolean;
    routingMode?: string;
    selectedProfile?: string;
}

export interface ArcProfileInfo {
    id: string;
    name: string;
    mode?: 'plan' | 'build' | 'auto' | string;
    description?: string;
    allowPaidCalls?: boolean;
    dryRun?: boolean;
    provider?: string;
    runtime?: string;
}

export interface IsolationProviderInfo {
    id: string;
    name: string;
    available: boolean;
    active?: boolean;
    reason?: string;
}

export interface IsolationStatus {
    current: string;
    available: boolean;
    providers: IsolationProviderInfo[];
    message?: string;
}

// ========== Run Links Types (Session B7) ==========

/**
 * Linked event chain for a single stable ID.
 */
export interface LinkedEventChain {
    stableId: string;
    events: TraceEvent[];
}

/**
 * Run links response from /api/runs/{id}/links.
 * Contains cross-referenced event chains keyed by stable ID type.
 */
export interface RunLinksResponse {
    nodeChains: Record<string, TraceEvent[]>;
    messageChains: Record<string, TraceEvent[]>;
    toolCallChains: Record<string, TraceEvent[]>;
    evidenceChains: Record<string, TraceEvent[]>;
    hasStableIds: boolean;
    stableIdCount: number;
}

/**
 * Evidence selection event emitted when EvidenceChip is opened.
 */
export interface EvidenceSelectionEvent {
    evidenceRef: EvidenceRef;
    source: 'chip-click' | 'keyboard' | 'context-menu';
    timestamp: string;
}

// ========== Cockpit Schema Contracts ==========

export type ContractStatus = 'proposed' | 'accepted' | 'fulfilled' | 'violated';

export type EvidenceKind = 'file' | 'tool_output' | 'run' | 'node' | 'ledger' | 'receipt';

export interface EvidenceRef {
    schema_version: number;
    evidence_id: string;
    kind: EvidenceKind;
    target: string;
    label?: string;
    range?: [number, number];
    redacted: boolean;
    metadata: Record<string, unknown>;
}

export interface RunContract {
    schema_version: number;
    contract_id: string;
    run_id?: string;
    session_id: string;
    objective: string;
    runtime: string;
    mode: 'plan' | 'build' | 'auto';
    allowed_tools: string[];
    write_scope: string[];
    cost_ceiling_usd: number | 'unknown';
    approval_policy: string;
    rollback_plan: string;
    evidence_expected: string[];
    status: ContractStatus;
    terms_digest?: string;
    created_at: string;
    accepted_at?: string;
    fulfilled_at?: string;
    metadata: Record<string, unknown>;
}

export interface FileChange {
    path: string;
    added: number;
    removed: number;
}

export interface BudgetVector {
    tokens: number | null | undefined;
    cost_usd: number | null | undefined;
    latency_ms: number | null | undefined;
}

export interface RunReceipt {
    schema_version: number;
    receipt_id: string;
    run_id: string;
    session_id?: string;
    contract_id?: string;
    status: 'completed' | 'failed' | 'cancelled';
    summary: string;
    cost_usd: number | 'unknown';
    usage?: BudgetVector;
    limit?: BudgetVector;
    duration_ms: number;
    files_changed: FileChange[];
    approvals: string[];
    evidence_refs: EvidenceRef[];
    rollback_command?: string;
    trust_boundaries_crossed: string[];
    unresolved_risks: string[];
    audit_chain_ref?: string;
    signature?: string;
    created_at: string;
}

export interface RetryOption {
    label: string;
    command?: string;
    risk: 'low' | 'medium' | 'high';
}

export interface FailureAutopsy {
    schema_version: number;
    run_id: string;
    probable_cause: string;
    confidence: 'high' | 'medium' | 'low' | 'unknown';
    failed_node?: string;
    last_safe_state?: string;
    retry_options: RetryOption[];
    related_issues: string[];
    knows: string[];
    guesses: string[];
    evidence_refs: EvidenceRef[];
    error_category?: 'tool_timeout' | 'provider_error' | 'validation' | 'internal' | 'unknown';
    stack_summary?: string;
    created_at: string;
    metadata: Record<string, unknown>;
}

export interface TrustDiff {
    schema_version: number;
    diff_id: string;
    workspace_path: string;
    before: string[];
    after: string[];
    added_capabilities: string[];
    removed_restrictions: string[];
    affected_runtimes: string[];
    reason: 'workspace_first_trust' | 'profile_switch' | 'runtime_added' | 'unknown';
    requires_confirmation: boolean;
    confirmed_at?: string;
    created_at: string;
    metadata: Record<string, unknown>;
}

// ========== Stable IDs and Graph Linkage (Wave 5) ==========

/**
 * Stable ID kinds supported by the cockpit.
 * Format: {prefix}_{ulid}
 */
export type StableIdKind =
    | 'message'     // msg_<ulid>
    | 'decision'    // dec_<ulid>
    | 'approval'    // apr_<ulid>
    | 'policy_decision' // pd_<ulid>
    | 'node'        // <workflow>.<node_name>
    | 'tool_call'   // tc_<ulid>
    | 'edge'        // <from>→<to>
    | 'run'         // run_<ulid>
    | 'contract'    // ctr_<ulid>
    | 'receipt'     // rcpt_<ulid>
    | 'evidence'    // ev_<ulid>
    | 'session'     // sess_<ulid>
    | 'hitl';       // hitl_<ulid>

/**
 * Graph node data carrying stable IDs and evidence/link references.
 * Used by the graph visualizer and cross-surface linking.
 */
export interface GraphNodeData {
    /** Stable node ID: <workflow>.<node_name> or node_<ulid> */
    id: string;
    /** Human-readable label */
    label: string;
    /** Node type for visual styling */
    type: 'queen' | 'worker' | 'agent' | 'tool' | 'decision' | 'hitl' | 'terminal' | 'router' | 'start' | 'end';
    /** Runtime that owns this node */
    runtime: 'swarmgraph' | 'langgraph' | 'crewai' | 'openai-agents' | 'ag2' | 'llamaindex' | 'lmarena';
    /** Current execution state */
    state: 'idle' | 'running' | 'waiting' | 'done' | 'failed';
    /** Optional badges (e.g., 'coalesced', 'burst:3') */
    badges?: string[];
    /** Number of events associated with this node */
    eventCount?: number;
    /** Subgraph/group ID for nested graphs (v0.2 reserved) */
    subgraphId?: string;
    /** Whether this is a group/container node */
    group?: boolean;

    // Stable cross-link IDs
    /** Stable message ID if this node produced/consumed a message */
    messageId?: string;
    /** Stable tool call ID if this node represents a tool call */
    toolCallId?: string;
    /** Stable decision ID if this node is a router/decision */
    decisionId?: string;
    /** Stable approval ID if this node requires HITL approval */
    approvalId?: string;

    // Evidence references
    /** Evidence refs attached to this node */
    evidenceRefs?: EvidenceRef[];

    // Runtime metadata
    /** Last event timestamp for this node */
    lastEventAt?: string;
    /** Last event type for this node */
    lastEventType?: string;
    /** Duration in ms this node took (when done/failed) */
    durationMs?: number;
}

/**
 * Graph edge data with stable ID.
 */
export interface GraphEdgeData {
    /** Stable edge ID: <from>→<to> or edge_<ulid> */
    id: string;
    /** Source node ID */
    from: string;
    /** Target node ID */
    to: string;
    /** Optional label for conditional/router edges */
    label?: string;
    /** Whether this is a conditional edge */
    conditional?: boolean;
    /** Message volume bucket for edge width (1, 2, 3) */
    messageVolume?: number;
    /** Whether this edge is currently active */
    active?: boolean;
}

/**
 * Cross-link state managed by the widget.
 * Tracks selections and highlights across graph, chat, runs, and evidence surfaces.
 */
export interface CrossLinkState {
    /** Currently selected graph node ID */
    selectedNodeId: string | null;
    /** Message IDs to highlight in chat */
    highlightedMessageIds: string[];
    /** Evidence IDs to highlight */
    highlightedEvidenceIds: string[];
    /** Tool call IDs to highlight */
    highlightedToolCallIds: string[];
    /** Run IDs to highlight in runs panel */
    highlightedRunIds: string[];
}

/**
 * Capability snapshot for runtime switch comparison.
 */
export interface CapabilitySnapshot {
    schemaVersion: number;
    runtimeId: string;
    snapshotId: string;
    capabilities: {
        canEmitContract: boolean;
        canEmitReceipt: boolean;
        canEmitAutopsy: boolean;
        canEmitEvidence: boolean;
        hasStableIds: boolean;
        canRun: boolean;
        canInspect: boolean;
        canTrace: boolean;
        canStreamEvents: boolean;
        requiresPaidCalls: boolean;
    };
    timestamp: string;
}

// ========== HITL (Human-in-the-Loop) ==========

/**
 * HITL prompt info for IDE display.
 */
export interface HitlPromptInfo {
    promptId: string;
    runId: string;
    prompt: string;
    createdAt: string;
    expiresAt?: string;
    promptType?: string;
    token?: string;
    status?: 'pending' | 'approved' | 'rejected' | 'modified' | 'expired' | 'used' | 'unknown';
    expired?: boolean;
    singleUse?: boolean;
    usedAt?: string;
}

/**
 * Request to respond to a HITL prompt.
 */
export interface HitlRespondRequest {
    promptId: string;
    decision: 'approve' | 'reject' | 'modify';
    response?: string;
    token: string;
}

// ========== Audit ==========

/**
 * Audit chain info for a run.
 */
export interface AuditChainInfo {
    runId: string;
    auditPath?: string;
    chainVerified: boolean;
    recordCount: number;
    state?: 'present' | 'missing' | 'degraded';
    reason?: string;
    signature?: string;
    hmacAlgo?: string;
}

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

// ========== Service Interface ==========

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
     * @throws {ArcError} EXECUTION_FAILED if the CLI is unavailable
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
     * @throws {ArcError} TRACE_NOT_FOUND if the file does not exist
     * @throws {ArcError} PARSE_ERROR if the file cannot be parsed
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
     * @throws {ArcError} TRACE_NOT_FOUND if the file does not exist
     * @throws {ArcError} PARSE_ERROR if a line cannot be parsed
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

    // ========== Capability Diff (Session B) ==========

    /**
     * Get capability diff between two runtimes.
     * Compares capabilities of fromRuntime vs toRuntime and returns
     * added/removed capabilities with trust boundary analysis.
     */
    getCapabilityDiff(fromRuntime: string, toRuntime: string): Promise<CapabilityDiffResponse>;
}
