/**
 * Discriminated RunEvent union types for type-safe event handling (Phase 22).
 *
 * Replaces unsafe `data: Record<string, unknown>` with typed payloads for known
 * event types. Consumers can use type narrowing instead of `as any` casts.
 *
 * Architecture: Discriminated union with typed variants for critical event types
 * plus a generic fallback for events that aren't yet typed. This allows incremental
 * migration while maintaining backward compatibility.
 */

/** Base event fields shared by all event types */
export interface RunEventBase {
  schema_version: number;
  timestamp: string;
  run_id: string;
  sequence: number;
}

// ─── Run Lifecycle Events ────────────────────────────────────────────────────

export interface RunStartedEvent extends RunEventBase {
  type: 'RUN_STARTED';
  data: {
    workflow_id: string;
    runtime: string;
    profile_id?: string;
    isolation?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface RunCompletedEvent extends RunEventBase {
  type: 'RUN_COMPLETED';
  data: {
    duration_ms: number;
    output?: unknown;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface RunFailedEvent extends RunEventBase {
  type: 'RUN_FAILED';
  data: {
    error: string;
    error_detail?: string;
    error_type?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface RunCancelledEvent extends RunEventBase {
  type: 'RUN_CANCELLED';
  data: {
    cancel_reason: string;
    node_id?: string;
    message_id?: string;
  };
}

// ─── Step Lifecycle Events ───────────────────────────────────────────────────

export interface StepStartedEvent extends RunEventBase {
  type: 'STEP_STARTED';
  data: {
    step_id: string;
    step_name: string;
    step_type?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface StepCompletedEvent extends RunEventBase {
  type: 'STEP_COMPLETED';
  data: {
    step_id: string;
    output?: unknown;
    duration_ms?: number;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface StepFailedEvent extends RunEventBase {
  type: 'STEP_FAILED';
  data: {
    step_id: string;
    error: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

// ─── Tool Call Events ────────────────────────────────────────────────────────

export interface ToolCallEvent extends RunEventBase {
  type: 'TOOL_CALL';
  data: {
    tool_call_id: string;
    tool_name: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface ToolCallStartEvent extends RunEventBase {
  type: 'TOOL_CALL_START';
  data: {
    tool_call_id: string;
    tool_name: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface ToolCallResultEvent extends RunEventBase {
  type: 'TOOL_CALL_RESULT';
  data: {
    tool_call_id: string;
    result: unknown;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface ToolCallErrorEvent extends RunEventBase {
  type: 'TOOL_CALL_ERROR';
  data: {
    tool_call_id: string;
    error: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

// ─── HITL Events ─────────────────────────────────────────────────────────────

export interface HitlPromptEvent extends RunEventBase {
  type: 'HITL_PROMPT';
  data: {
    hitl_id: string;
    step_id: string;
    prompt_text: string;
    options: string[];
    timeout_seconds: number;
    context?: unknown;
    created_at?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface HitlResponseEvent extends RunEventBase {
  type: 'HITL_RESPONSE';
  data: {
    hitl_id: string;
    decision: string;
    operator_id: string;
    responded_at: string;
    modified_data?: unknown;
    notes?: string;
    node_id?: string;
    message_id?: string;
  };
}

export interface HitlTimeoutEvent extends RunEventBase {
  type: 'HITL_TIMEOUT';
  data: {
    hitl_id: string;
    timeout_seconds: number;
    node_id?: string;
    message_id?: string;
  };
}

// ─── SwarmGraph Events ───────────────────────────────────────────────────────

export interface SwarmGraphTopologyEvent extends RunEventBase {
  type: 'SWARMGRAPH_TOPOLOGY';
  data: {
    nodes: unknown[];
    edges: unknown[];
    task_id?: string;
    strategy?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface SwarmGraphConsensusEvent extends RunEventBase {
  type: 'SWARMGRAPH_CONSENSUS';
  data: {
    votes: unknown[];
    decision?: string;
    strategy?: string;
    voters?: string[];
    confidence?: number;
    consensus_reached?: boolean;
    task_id?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface SwarmGraphCostEvent extends RunEventBase {
  type: 'SWARMGRAPH_COST';
  data: {
    provider?: string;
    model?: string;
    promptTokens?: number;
    completionTokens?: number;
    totalCost?: number;
    totalTokens?: number;
    currency?: string;
    items?: unknown[];
    source?: string;
    runtime?: string;
    measured?: string;
    node_id?: string;
    message_id?: string;
    evidence_refs?: string[];
    cache_read_input_tokens?: number;
    cache_creation_input_tokens?: number;
  };
}

// ─── Message Events ──────────────────────────────────────────────────────────

export interface MessageEvent extends RunEventBase {
  type: 'MESSAGE';
  data: {
    text: string;
    source?: string;
    coalesced?: boolean;
    node_id?: string;
    message_id?: string;
    tool_call_id?: string;
    evidence_refs?: string[];
  };
}

// ─── Node Events ─────────────────────────────────────────────────────────────

export interface NodeStartedEvent extends RunEventBase {
  type: 'NODE_STARTED';
  data: {
    node_id: string;
    node_name?: string;
    node_type?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

export interface NodeFailedEvent extends RunEventBase {
  type: 'NODE_FAILED';
  data: {
    node_id: string;
    error: string;
    node_name?: string;
    message_id?: string;
    evidence_refs?: string[];
  };
}

// ─── Policy Bypass Warning Events ────────────────────────────────────────────

/**
 * Reason codes for policy bypass warnings.
 * Indicates why enforcement could not be applied to an operation.
 */
export type PolicyBypassReason =
  | 'unknown_provider_plugin'
  | 'custom_http_client'
  | 'custom_subprocess_runner'
  | 'uninstrumented_tool'
  | 'upstream_bypassed_boundary';

export interface PolicyBypassWarning extends RunEventBase {
  type: 'POLICY_BYPASS_WARNING';
  data: {
    policy_id: string;
    bypass_reason: PolicyBypassReason;
    surface: string;
    surface_identifier: string;
    suggested_remediation: string;
    parent_run_id?: string;
  };
}

// ─── Capability Card Decision Event ──────────────────────────────────────────

export interface CapabilityCardDecisionEvent extends RunEventBase {
  type: 'CAPABILITY_CARD_DECISION';
  data: {
    action: string;
    decision: 'allow' | 'deny' | 'warn';
    reason: string;
    card_id?: string;
    card_hash?: string;
    entity_type?: string;
    mode: 'off' | 'warn' | 'strict';
    remediation?: string;
    correlation_id?: string;
    details?: Record<string, string>;
  };
}

// ─── MCP Call Decision Event ─────────────────────────────────────────────────

export interface McpCallDecisionEvent extends RunEventBase {
  type: 'MCP_CALL_DECISION';
  data: {
    server_id: string;
    tool_name: string;
    decision: 'allow' | 'deny' | 'warn';
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    policy: 'strict' | 'permissive';
    reason: string;
    injection_severity?: string;
    manifest_risk?: string;
    roots_violation?: boolean;
    drift?: string;
    correlation_id?: string;
  };
}

// ─── Eval Policy Events ──────────────────────────────────────────────────────

export interface EvalPolicyRecommendedEvent extends RunEventBase {
  type: 'EVAL_POLICY_RECOMMENDED';
  data: {
    profile_id: string;
    recommendations_count: number;
    actions: string[];
    correlation_id: string;
    node_id?: string;
    message_id?: string;
  };
}

export interface EvalPolicyAppliedEvent extends RunEventBase {
  type: 'EVAL_POLICY_APPLIED';
  data: {
    profile_id: string;
    new_path: string;
    diff_summary: string;
    correlation_id: string;
    version: number;
    dry_run: boolean;
    node_id?: string;
    message_id?: string;
  };
}

// ─── Quota Warning Events ────────────────────────────────────────────────────

export interface QuotaWarningEvent extends RunEventBase {
  type: 'QUOTA_WARNING';
  data: {
    dimension: string;
    usage_pct: number;
    limit: number;
    current: number;
  };
}

export interface ContextCompactedEvent extends RunEventBase {
  type: 'CONTEXT_COMPACTED';
  data: {
    tokens_before: number;
    tokens_after: number;
    messages_evicted_count: number;
    evicted_handles?: string[];
    [key: string]: unknown;
  };
}

export interface ToolOutputVirtualizedEvent extends RunEventBase {
  type: 'TOOL_OUTPUT_VIRTUALIZED';
  data: {
    tool_name: string;
    original_size_bytes: number;
    handle_uri: string;
    estimated_tokens_saved: number;
    [key: string]: unknown;
  };
}

export interface ModelChangedEvent extends RunEventBase {
  type: 'MODEL_CHANGED';
  data: {
    previous_model: string;
    current_model: string;
    capabilities_added?: string[];
    capabilities_removed?: string[];
    [key: string]: unknown;
  };
}

export interface PricingFeedRefreshedEvent extends RunEventBase {
  type: 'PRICING_FEED_REFRESHED';
  data: {
    feed_url: string;
    feed_hash: string;
    rows_seen: number;
    source: string;
    [key: string]: unknown;
  };
}

export interface BudgetBrokerSyncEvent extends RunEventBase {
  type: 'BUDGET_BROKER_SYNC';
  data: {
    scope: string;
    amount_usd: number;
    local_approved: boolean;
    remote_approved: boolean;
    fell_back: boolean;
    [key: string]: unknown;
  };
}

export interface ObservabilityExportStartedEvent extends RunEventBase {
  type: 'OBSERVABILITY_EXPORT_STARTED';
  data: {
    destination: string;
    protocol: string;
    span_count: number;
    [key: string]: unknown;
  };
}

// ─── Raw/Unknown Events ──────────────────────────────────────────────────────

export interface RawEvent extends RunEventBase {
  type: 'RAW';
  data: {
    raw: unknown;
    source?: string;
    node_id?: string;
    message_id?: string;
  };
}

/**
 * Generic fallback for event types that aren't yet typed.
 * Allows incremental migration while maintaining backward compatibility.
 */
export interface UnknownEvent extends RunEventBase {
  type: string;
  data: Record<string, unknown>;
}

// ─── Security denial events (Phase 23 enforcement) ──────────────────────────

export interface TrustDeniedEvent extends RunEventBase {
  type: 'TRUST_DENIED';
  data: {
    action: string;
    workspace_path: string;
    reason: string;
    trust_level: string;
    required_trust_level?: string;
    remediation?: string;
    correlation_id?: string | null;
    [key: string]: unknown;
  };
}

export interface PaidCallDeniedEvent extends RunEventBase {
  type: 'PAID_CALL_DENIED';
  data: {
    action: string;
    reason: string;
    profile_id: string;
    provider?: string | null;
    model?: string | null;
    allow_paid_calls?: boolean;
    remediation?: string;
    correlation_id?: string | null;
    [key: string]: unknown;
  };
}

export interface ShellDeniedEvent extends RunEventBase {
  type: 'SHELL_DENIED';
  data: {
    action: string;
    reason: string;
    profile_id: string;
    command?: string | null;
    allow_shell?: boolean;
    remediation?: string;
    correlation_id?: string | null;
    [key: string]: unknown;
  };
}

export interface NetworkDeniedEvent extends RunEventBase {
  type: 'NETWORK_DENIED';
  data: {
    action: string;
    reason: string;
    profile_id: string;
    url?: string | null;
    allow_network?: boolean;
    remediation?: string;
    correlation_id?: string | null;
    [key: string]: unknown;
  };
}

export interface PermissionDeniedEvent extends RunEventBase {
  type: 'PERMISSION_DENIED';
  data: {
    action: string;
    reason: string;
    permission_type: string;
    context?: Record<string, string> | null;
    remediation?: string | null;
    correlation_id?: string | null;
    [key: string]: unknown;
  };
}

// ─── Discriminated Union ─────────────────────────────────────────────────────

/**
 * Discriminated union of all known typed event variants.
 * Use type narrowing with `event.type` to access typed payloads.
 *
 * Example:
 * ```ts
 * if (event.type === 'RUN_STARTED') {
 *   // TypeScript knows event.data.workflow_id exists
 *   console.log(event.data.workflow_id);
 * }
 * ```
 */
export type KnownRunEvent =
  | RunStartedEvent
  | RunCompletedEvent
  | RunFailedEvent
  | RunCancelledEvent
  | StepStartedEvent
  | StepCompletedEvent
  | StepFailedEvent
  | ToolCallEvent
  | ToolCallStartEvent
  | ToolCallResultEvent
  | ToolCallErrorEvent
  | HitlPromptEvent
  | HitlResponseEvent
  | HitlTimeoutEvent
  | SwarmGraphTopologyEvent
  | SwarmGraphConsensusEvent
  | SwarmGraphCostEvent
  | MessageEvent
  | NodeStartedEvent
  | NodeFailedEvent
  | PolicyBypassWarning
  | CapabilityCardDecisionEvent
  | McpCallDecisionEvent
  | EvalPolicyRecommendedEvent
  | EvalPolicyAppliedEvent
  | QuotaWarningEvent
  | ContextCompactedEvent
  | ToolOutputVirtualizedEvent
  | ModelChangedEvent
  | PricingFeedRefreshedEvent
  | BudgetBrokerSyncEvent
  | ObservabilityExportStartedEvent
  | TrustDeniedEvent
  | PaidCallDeniedEvent
  | ShellDeniedEvent
  | NetworkDeniedEvent
  | PermissionDeniedEvent
  | RawEvent;

/**
 * Full TypedRunEvent: known typed events + unknown fallback.
 * This allows handling both typed and untyped events gracefully.
 * 
 * Note: The old `RunEvent` interface (from arc-protocol-types.ts) remains
 * for backward compatibility. New code should use `TypedRunEvent` for
 * type-safe event handling.
 */
export type TypedRunEvent = KnownRunEvent | UnknownEvent;

export const KNOWN_RUN_EVENT_TYPES = [
  'RUN_STARTED',
  'RUN_COMPLETED',
  'RUN_FAILED',
  'RUN_CANCELLED',
  'STEP_STARTED',
  'STEP_COMPLETED',
  'STEP_FAILED',
  'TOOL_CALL',
  'TOOL_CALL_START',
  'TOOL_CALL_RESULT',
  'TOOL_CALL_ERROR',
  'HITL_PROMPT',
  'HITL_RESPONSE',
  'HITL_TIMEOUT',
  'SWARMGRAPH_TOPOLOGY',
  'SWARMGRAPH_CONSENSUS',
  'SWARMGRAPH_COST',
  'MESSAGE',
  'NODE_STARTED',
  'NODE_FAILED',
  'POLICY_BYPASS_WARNING',
  'CAPABILITY_CARD_DECISION',
  'MCP_CALL_DECISION',
  'EVAL_POLICY_RECOMMENDED',
  'EVAL_POLICY_APPLIED',
  'QUOTA_WARNING',
  'CONTEXT_COMPACTED',
  'TOOL_OUTPUT_VIRTUALIZED',
  'MODEL_CHANGED',
  'PRICING_FEED_REFRESHED',
  'BUDGET_BROKER_SYNC',
  'OBSERVABILITY_EXPORT_STARTED',
  'TRUST_DENIED',
  'PAID_CALL_DENIED',
  'SHELL_DENIED',
  'NETWORK_DENIED',
  'PERMISSION_DENIED',
  'RAW',
] as const satisfies readonly KnownRunEvent['type'][];

const knownRunEventTypeSet = new Set<string>(KNOWN_RUN_EVENT_TYPES);

// ─── Type Guards ─────────────────────────────────────────────────────────────

/**
 * Type guard to check if an event is of a specific type.
 * Narrows the event type for type-safe access to data fields.
 *
 * Example:
 * ```ts
 * if (isEventOfType(event, 'RUN_STARTED')) {
 *   console.log(event.data.workflow_id); // Type-safe!
 * }
 * ```
 */
export function isEventOfType<T extends KnownRunEvent['type']>(
  event: TypedRunEvent,
  type: T
): event is Extract<KnownRunEvent, { type: T }> {
  return event.type === type;
}

/**
 * Type guard to check if an event is a known typed event.
 * Useful for filtering out unknown events.
 */
export function isKnownEvent(event: TypedRunEvent): event is KnownRunEvent {
  return knownRunEventTypeSet.has(event.type);
}

/**
 * Exhaustiveness check for switch statements.
 * Ensures all event types are handled.
 *
 * Example:
 * ```ts
 * switch (event.type) {
 *   case 'RUN_STARTED': return handleRunStarted(event);
 *   case 'RUN_COMPLETED': return handleRunCompleted(event);
 *   // ... handle all types
 *   default: return assertNeverEvent(event);
 * }
 * ```
 */
export function assertNeverEvent(event: never): never {
  throw new Error(`Unhandled event type: ${(event as TypedRunEvent).type}`);
}

/**
 * Parse a raw event object into a TypedRunEvent.
 * Wraps unknown event types as UnknownEvent for safe handling.
 *
 * @param raw - Raw event object from JSON parsing
 * @returns TypedRunEvent (known or unknown)
 */
export function parseRunEvent(raw: unknown): TypedRunEvent {
  if (typeof raw !== 'object' || raw === null) {
    throw new Error('Invalid event: not an object');
  }

  const event = raw as Record<string, unknown>;

  // Validate required base fields
  if (typeof event.type !== 'string') {
    throw new Error('Invalid event: missing or invalid type field');
  }
  if (typeof event.run_id !== 'string') {
    throw new Error('Invalid event: missing or invalid run_id field');
  }
  if (typeof event.timestamp !== 'string') {
    throw new Error('Invalid event: missing or invalid timestamp field');
  }
  if (typeof event.sequence !== 'number') {
    throw new Error('Invalid event: missing or invalid sequence field');
  }

  // Default schema_version to 1 for old traces
  const schema_version = typeof event.schema_version === 'number' ? event.schema_version : 1;

  // Ensure data is an object
  const data = typeof event.data === 'object' && event.data !== null
    ? (event.data as Record<string, unknown>)
    : {};

  // Construct typed event
  const typedEvent: TypedRunEvent = {
    schema_version,
    type: event.type,
    timestamp: event.timestamp,
    run_id: event.run_id,
    sequence: event.sequence,
    data,
  } as TypedRunEvent;

  return typedEvent;
}
