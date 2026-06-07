/**
 * Cockpit schema contracts (RunContract/RunReceipt/FailureAutopsy/TrustDiff/EvidenceRef)
 * and Stable ID + graph-linkage types (GraphNodeData/GraphEdgeData/CrossLinkState/
 * CapabilitySnapshot/StableIdKind).
 *
 * Extracted from `arc-protocol.ts` (CR-027) and re-exported from it via the barrel,
 * so existing `from '../../common/arc-protocol'` imports continue to work unchanged.
 * Self-contained: these types reference only each other and primitives.
 */


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
    /** Runtime that owns this node.
     * 'lmarena' is daemon-only-deferred: the Python backend supports arena runs,
     * but no active UI renders arena graph nodes. Reserved for future LM Arena UI.
     */
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
