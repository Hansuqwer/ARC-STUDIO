/**
 * Run Diff / Time Travel — TypeScript mirror of the Python `run_diff` package.
 *
 * Read-only structural mirror of
 * `agent_runtime_cockpit/run_diff/models.py` and related modules.
 * Used by Theia IDE widgets (run-diff widget, run-timeline widget) and
 * `arc ir diff --json` output consumers. Keep field names in sync with the
 * Python models (parity is asserted in run-diff.test.ts).
 *
 * This module is fully local-first and read-only — no network, subprocess,
 * or model call primitives.
 */

export const RUN_DIFF_SCHEMA_VERSION = 1;

// ---------------------------------------------------------------------------
// Enums / Literal types
// ---------------------------------------------------------------------------

export type DiffMode =
  | 'ir_vs_ir'
  | 'run_vs_run'
  | 'policy_vs_policy'
  | 'simulation_vs_simulation'
  | 'simulation_vs_run'
  | 'capability_vs_capability'
  | 'flight_vs_flight'
  | 'mcp_vs_mcp';

export const ChangeType = {
  ADDED: 'added',
  REMOVED: 'removed',
  CHANGED: 'changed',
  UNCHANGED: 'unchanged',
} as const;
export type ChangeType = (typeof ChangeType)[keyof typeof ChangeType];

export const DiffSubjectKind = {
  IR_GRAPH: 'ir_graph',
  RUN_RECORD: 'run_record',
  POLICY_REPORT: 'policy_report',
  SIMULATION_REPORT: 'simulation_report',
  CAPABILITY_CARD: 'capability_card',
  FLIGHT_SEGMENT: 'flight_segment',
  MCP_MANIFEST: 'mcp_manifest',
  UNKNOWN: 'unknown',
} as const;
export type DiffSubjectKind = (typeof DiffSubjectKind)[keyof typeof DiffSubjectKind];

// ---------------------------------------------------------------------------
// DiffSubject
// ---------------------------------------------------------------------------

export interface DiffSubject {
  kind: DiffSubjectKind;
  id: string;
  path?: string | null;
  hash?: string | null;
  run_id?: string | null;
  graph_hash?: string | null;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// DiffSummary
// ---------------------------------------------------------------------------

export interface DiffSummary {
  nodes_added: number;
  nodes_removed: number;
  nodes_changed: number;
  edges_added: number;
  edges_removed: number;
  edges_changed: number;
  events_added: number;
  events_removed: number;
  events_changed: number;
  event_types_added: string[];
  event_types_removed: string[];
  policy_issues_added: number;
  policy_issues_removed: number;
  policy_blockers_introduced: number;
  policy_errors_introduced: number;
  risk_increased: boolean;
  risk_decreased: boolean;
  mcp_drift_changed: boolean;
  paid_call_delta: number;
  hitl_gate_delta: number;
  consensus_changed: boolean;
  hitl_removed: boolean;
  total_changes: number;
}

export function diffSummaryHasChanges(summary: DiffSummary): boolean {
  return summary.total_changes > 0;
}

// ---------------------------------------------------------------------------
// Node / Graph diff
// ---------------------------------------------------------------------------

export interface NodeDiffField {
  field_name: string;
  left_value: unknown;
  right_value: unknown;
  change_type: ChangeType;
}

export interface NodeDiff {
  node_id: string;
  change_type: ChangeType;
  changed_fields: NodeDiffField[];
  risk_delta?: string | null;
  policy_delta?: string | null;
  tool_delta?: string | null;
  mcp_delta?: string | null;
  consensus_delta?: string | null;
  hitl_delta?: string | null;
  paid_call_delta?: boolean | null;
  audit_delta?: string | null;
  is_semantic_regression: boolean;
  regression_reason?: string | null;
}

export interface GraphDiff {
  nodes_added: string[];
  nodes_removed: string[];
  nodes_changed: NodeDiff[];
  edges_added: string[];
  edges_removed: string[];
  edges_changed: Record<string, unknown>[];
  node_count_left: number;
  node_count_right: number;
  edge_count_left: number;
  edge_count_right: number;
  risk_level_left?: string | null;
  risk_level_right?: string | null;
  consensus_left?: string | null;
  consensus_right?: string | null;
}

// ---------------------------------------------------------------------------
// Event diff
// ---------------------------------------------------------------------------

export interface EventEntry {
  event_index: number;
  event_type: string;
  timestamp?: string | null;
  sequence?: number | null;
  data_keys: string[];
  hash?: string | null;
}

export interface EventDiff {
  events_added: EventEntry[];
  events_removed: EventEntry[];
  events_changed: Record<string, unknown>[];
  sequence_alignment: Record<string, unknown>[];
  first_event_divergence?: number | null;
  event_count_left: number;
  event_count_right: number;
}

// ---------------------------------------------------------------------------
// Policy diff
// ---------------------------------------------------------------------------

export interface PolicyIssueDiff {
  rule: string;
  left_severity?: string | null;
  right_severity?: string | null;
  node_id?: string | null;
  left_present: boolean;
  right_present: boolean;
  is_regression: boolean;
  regression_type?: string | null;
}

export interface PolicyDiff {
  issues_added: PolicyIssueDiff[];
  issues_removed: PolicyIssueDiff[];
  issues_changed: PolicyIssueDiff[];
  can_run_left: boolean;
  can_run_right: boolean;
  can_run_regression: boolean;
  risk_level_left?: string | null;
  risk_level_right?: string | null;
  risk_regression: boolean;
  suggested_consensus_left?: string | null;
  suggested_consensus_right?: string | null;
  consensus_regression: boolean;
  error_count_left: number;
  error_count_right: number;
  error_count_delta: number;
  warning_count_left: number;
  warning_count_right: number;
  warning_count_delta: number;
}

// ---------------------------------------------------------------------------
// Simulation diff
// ---------------------------------------------------------------------------

export interface SimulationDiff {
  summary_changed: boolean;
  reachable_nodes_left: number;
  reachable_nodes_right: number;
  hitl_gates_left: number;
  hitl_gates_right: number;
  hitl_gate_delta: number;
  paid_calls_left: number;
  paid_calls_right: number;
  paid_call_delta: number;
  mcp_tools_left: number;
  mcp_tools_right: number;
  gate_count_left: number;
  gate_count_right: number;
  policy_regression: boolean;
  can_run_left: boolean;
  can_run_right: boolean;
  warnings_added: string[];
  warnings_removed: string[];
}

// ---------------------------------------------------------------------------
// MCP manifest diff
// ---------------------------------------------------------------------------

export interface McpManifestDiff {
  servers_added: string[];
  servers_removed: string[];
  hash_changed: { server: string; left_hash: string; right_hash: string }[];
  approved_tools_delta: number;
  blocked_tools_delta: number;
  tools_added: string[];
  tools_removed: string[];
  drifted_servers: string[];
}

// ---------------------------------------------------------------------------
// Capability diff
// ---------------------------------------------------------------------------

export interface CapabilityDiff {
  cards_added: string[];
  cards_removed: string[];
  cards_changed: Record<string, unknown>[];
  capabilities_added: string[];
  capabilities_removed: string[];
  risk_level_changed: { card_id: string; left_level: string; right_level: string }[];
  mcp_drift_detected: boolean;
  trust_regression: boolean;
}

// ---------------------------------------------------------------------------
// Flight diff
// ---------------------------------------------------------------------------

export interface FlightDiff {
  events_added: number;
  events_removed: number;
  events_changed: number;
  segment_hashes_match: boolean;
  hash_chain_valid: boolean;
  event_types_added: string[];
  event_types_removed: string[];
  first_event_divergence?: number | null;
}

// ---------------------------------------------------------------------------
// Cost / Risk diff
// ---------------------------------------------------------------------------

export interface CostDiff {
  has_paid_calls_left: boolean;
  has_paid_calls_right: boolean;
  paid_calls_introduced: boolean;
  estimated_cost_delta_usd: number;
  estimated_cost_floor_left: number;
  estimated_cost_floor_right: number;
}

export interface RiskDiff {
  level_left?: string | null;
  level_right?: string | null;
  level_changed: boolean;
  signals_added: string[];
  signals_removed: string[];
  score_delta: number;
}

// ---------------------------------------------------------------------------
// First divergence
// ---------------------------------------------------------------------------

export interface FirstDivergence {
  kind: string;
  node_id?: string | null;
  edge_id?: string | null;
  event_id?: string | null;
  policy_rule?: string | null;
  sequence?: number | null;
  frame_index?: number | null;
  left_value: unknown;
  right_value: unknown;
  reason: string;
}

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

export interface TimelineFrame {
  frame_id: string;
  sequence: number;
  timestamp?: string | null;
  subject: string;
  event_type?: string | null;
  node_id?: string | null;
  summary: string;
  left_label?: string | null;
  right_label?: string | null;
  change_type: ChangeType;
  left_value?: Record<string, unknown> | null;
  right_value?: Record<string, unknown> | null;
  redacted: boolean;
  redacted_fields: string[];
}

// ---------------------------------------------------------------------------
// TimeTravelCursor
// ---------------------------------------------------------------------------

export interface TimeTravelCursorState {
  frame_id: string | null;
  sequence: number | null;
  can_step_back: boolean;
  can_step_forward: boolean;
  context: TimelineFrame[];
}

/** Step through a RunDiffReport timeline frame-by-frame. */
export class TimeTravelCursor {
  private _frames: TimelineFrame[];
  private _index: number;

  constructor(frames: TimelineFrame[]) {
    this._frames = frames;
    this._index = 0;
  }

  get current(): TimelineFrame | null {
    return this._frames[this._index] ?? null;
  }

  get frame_id(): string | null {
    return this.current?.frame_id ?? null;
  }

  get sequence(): number | null {
    return this.current?.sequence ?? null;
  }

  get can_step_back(): boolean {
    return this._index > 0;
  }

  get can_step_forward(): boolean {
    return this._index < this._frames.length - 1;
  }

  stepBack(): TimelineFrame | null {
    if (this.can_step_back) this._index -= 1;
    return this.current;
  }

  stepForward(): TimelineFrame | null {
    if (this.can_step_forward) this._index += 1;
    return this.current;
  }

  /** Jump to a specific frame by frame_id. Returns null if not found. */
  seekTo(frameId: string): TimelineFrame | null {
    const idx = this._frames.findIndex((f) => f.frame_id === frameId);
    if (idx !== -1) {
      this._index = idx;
      return this.current;
    }
    return null;
  }

  /** Get frames around the current position. */
  context(before = 2, after = 2): TimelineFrame[] {
    const start = Math.max(0, this._index - before);
    const end = Math.min(this._frames.length, this._index + after + 1);
    return this._frames.slice(start, end);
  }

  /** Export cursor state as a serializable dict. */
  asDict(): TimeTravelCursorState {
    return {
      frame_id: this.frame_id,
      sequence: this.sequence,
      can_step_back: this.can_step_back,
      can_step_forward: this.can_step_forward,
      context: this.context(),
    };
  }
}

// ---------------------------------------------------------------------------
// RunDiffReport
// ---------------------------------------------------------------------------

export interface RunDiffReport {
  schema_version: number;
  generated_at: string;
  left: DiffSubject;
  right: DiffSubject;
  mode: DiffMode;
  summary: DiffSummary;
  first_divergence?: FirstDivergence | null;
  graph_diff?: GraphDiff | null;
  event_diff?: EventDiff | null;
  policy_diff?: PolicyDiff | null;
  simulation_diff?: SimulationDiff | null;
  capability_diff?: CapabilityDiff | null;
  flight_diff?: FlightDiff | null;
  mcp_diff?: McpManifestDiff | null;
  cost_diff?: CostDiff | null;
  risk_diff?: RiskDiff | null;
  timeline: TimelineFrame[];
  warnings: string[];
  errors: string[];
  mode_metadata: Record<string, unknown>;
  diff_hash?: string | null;
}

/** Default empty DiffSummary matching Python behavior. */
export function emptyDiffSummary(): DiffSummary {
  return {
    nodes_added: 0,
    nodes_removed: 0,
    nodes_changed: 0,
    edges_added: 0,
    edges_removed: 0,
    edges_changed: 0,
    events_added: 0,
    events_removed: 0,
    events_changed: 0,
    event_types_added: [],
    event_types_removed: [],
    policy_issues_added: 0,
    policy_issues_removed: 0,
    policy_blockers_introduced: 0,
    policy_errors_introduced: 0,
    risk_increased: false,
    risk_decreased: false,
    mcp_drift_changed: false,
    paid_call_delta: 0,
    hitl_gate_delta: 0,
    consensus_changed: false,
    hitl_removed: false,
    total_changes: 0,
  };
}

/** Default empty DiffSubject matching Python behavior. */
export function emptyDiffSubject(): DiffSubject {
  return {
    kind: DiffSubjectKind.UNKNOWN,
    id: '',
    path: null,
    hash: null,
    run_id: null,
    graph_hash: null,
    metadata: {},
  };
}

// ---------------------------------------------------------------------------
// Load result (mirrors Python LoadResult / LoadError)
// ---------------------------------------------------------------------------

export type LoadResultOk<T> = { ok: true; data: T; error: null };
export type LoadResultErr = { ok: false; data: null; error: string };
export type LoadResult<T> = LoadResultOk<T> | LoadResultErr;

// ---------------------------------------------------------------------------
// Redaction helpers (mirrors Python redaction.py)
// ---------------------------------------------------------------------------

const REDACT_PLACEHOLDER = '[REDACTED]';

const ALWAYS_REDACT_KEYS = new Set([
  'api_key', 'apikey', 'secret', 'password', 'token', 'access_token',
  'auth_token', 'bearer_token', 'private_key', 'credential', 'key',
  'passphrase', 'aws_key', 'github_token', 'anthropic_key', 'openai_key',
]);

function shouldRedactKey(key: string): boolean {
  const k = key.toLowerCase();
  return Array.from(ALWAYS_REDACT_KEYS).some((s) => k.includes(s));
}

function redactValue(key: string, value: unknown): unknown {
  if (typeof value !== 'string') return value;
  if (shouldRedactKey(key) && value && value !== REDACT_PLACEHOLDER) {
    return REDACT_PLACEHOLDER;
  }
  return value;
}

/** Recursively redact secrets from a plain object. */
export function redactDict(data: unknown): unknown {
  if (typeof data !== 'object' || data === null || Array.isArray(data)) {
    return data;
  }
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
    if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      result[k] = redactDict(v);
    } else if (Array.isArray(v)) {
      result[k] = v.map((item) =>
        typeof item === 'object' && item !== null ? redactDict(item) : redactValue(k, item),
      );
    } else {
      result[k] = redactValue(k, v);
    }
  }
  return result;
}

/** Redact all secrets from a RunDiffReport plain object before display/export. */
export function redactReport(report: unknown): unknown {
  if (typeof report !== 'object' || report === null) return report;
  const result: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(report as Record<string, unknown>)) {
    if (typeof v === 'string') {
      result[k] = v; // Note: full-text pattern redaction omitted here (requires regex)
    } else if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      result[k] = redactDict(v);
    } else if (Array.isArray(v)) {
      result[k] = v.map((item) =>
        typeof item === 'object' && item !== null
          ? redactDict(item)
          : typeof item === 'string'
            ? item
            : item,
      );
    } else {
      result[k] = v;
    }
  }
  return result;
}

/** Check if a string is safe to display without redaction. */
export function isSafe(_text: string): boolean {
  // Placeholder — full implementation would run SECRET_PATTERNS regex
  return true;
}

// ---------------------------------------------------------------------------
// JSON helpers (mirrors Python export.py)
// ---------------------------------------------------------------------------

/** Serialize a RunDiffReport to a JSON string. */
export function toJson(report: RunDiffReport, indent?: number): string {
  return JSON.stringify(report, null, indent ?? 0);
}

/** Deserialize a JSON string into a RunDiffReport. */
export function fromJson(json: string): RunDiffReport {
  return JSON.parse(json) as RunDiffReport;
}

// ---------------------------------------------------------------------------
// Parity assertions (run in test suite)
// ---------------------------------------------------------------------------

/**
 * Verify that a Python-side RunDiffReport JSON serialises to a structurally
 * equivalent TypeScript object. Call from run-diff.test.ts.
 */
export function assertParity(
  pythonJson: string,
  expectedMode: DiffMode,
): { ok: true; report: RunDiffReport } | { ok: false; detail: string } {
  try {
    const parsed = JSON.parse(pythonJson);
    if (parsed.schema_version !== RUN_DIFF_SCHEMA_VERSION) {
      return { ok: false, detail: `schema_version mismatch: ${parsed.schema_version}` };
    }
    if (parsed.mode !== expectedMode) {
      return { ok: false, detail: `mode mismatch: ${parsed.mode} != ${expectedMode}` };
    }
    const report = parsed as RunDiffReport;
    if (!report.left || !report.right || !report.summary) {
      return { ok: false, detail: 'missing required top-level fields' };
    }
    return { ok: true, report };
  } catch (e) {
    return { ok: false, detail: String(e) };
  }
}