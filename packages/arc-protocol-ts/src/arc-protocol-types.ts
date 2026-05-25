/**
 * ARC Protocol types — standalone package (no Theia dependency).
 * Mirrors arc-core/src/common/arc-protocol.ts for use in tests, scripts, tools.
 */
export const ARC_PROTOCOL_VERSION = '1.0';

export interface ArcEnvelope<T = unknown> {
  version: string;
  ok: boolean;
  data: T | null;
  error: ArcError | null;
  meta: ArcMeta;
}

export interface ArcError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ArcMeta {
  duration_ms?: number;
  adapter?: string;
  workspace?: string;
  timestamp?: string;
}

export interface WorkspaceInfo {
  path: string;
  runtimes: RuntimeInfo[];
  files_scanned: number;
  detection_warnings: string[];
}

export interface RuntimeInfo {
  id: string;
  name: string;
  adapter: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: string[];
  capabilities: RuntimeCapabilities;
}

export const CAPABILITY_SCHEMA_VERSION = 1;

export type SupportLevel = 'stable' | 'beta' | 'alpha' | 'experimental' | 'deprecated';

export type ExecutionMode = 'standalone' | 'sequence' | 'adoption';

export type AuditLevel = 'none' | 'arc_sha256' | 'swarmgraph_hmac';

export type HitlLevel = 'none' | 'advisory' | 'enforced';

export interface RuntimeCapabilities {
  schema_version: number;
  support_level: SupportLevel;
  execution_modes: ExecutionMode[];
  adoption_modes: string[];
  audit_level: AuditLevel;
  hitl_level: HitlLevel;
  can_inspect: boolean;
  can_run: boolean;
  can_trace: boolean;
  can_replay: boolean;
  can_export_schema: boolean;
  can_export_workflow: boolean;
}

export interface WorkflowInfo {
  id: string;
  name: string;
  runtime: string;
  source_file?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  entry_points: string[];
  metadata: Record<string, unknown>;
}

export interface SourceLocation {
  file: string;
  line: number;
  column?: number;
}

export interface WorkflowNode {
  id: string;
  label: string;
  type: 'agent' | 'tool' | 'resource' | 'prompt' | 'router' | 'start' | 'end' | 'unknown';
  source_location?: SourceLocation;
  metadata: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  from_node: string;
  to_node: string;
  label?: string;
  conditional: boolean;
  metadata: Record<string, unknown>;
}

export interface SchemaInfo {
  id: string;
  name: string;
  runtime: string;
  schema: Record<string, unknown>;
  source_file?: string;
}

export interface BudgetVector {
  tokens?: number;
  cost_usd?: number;
  latency_ms?: number;
}

export interface RunRecord {
  id: string;
  workflow_id: string;
  runtime: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  ended_at?: string;
  events: RunEvent[];
  metadata: Record<string, unknown>;
  audit_path?: string;
  budget?: BudgetVector;
}

/** Event schema version constant — mirrors Python CURRENT_SCHEMA_VERSION */
export const EVENT_SCHEMA_VERSION = 2;

export interface RunEvent {
  schema_version: number;
  type: string;
  timestamp: string;
  run_id: string;
  sequence: number;
  data: Record<string, unknown>;
}

/**
 * Parse a raw JSON event string, defaulting schema_version to 1 for old traces.
 * Returns the parsed event. If the version exceeds EVENT_SCHEMA_VERSION, wraps
 * the event as a RAW type for forward compatibility.
 */
export function parseEvent(raw: string): RunEvent {
  const event: RunEvent = JSON.parse(raw);
  if (!event.schema_version) {
    event.schema_version = 1;
  }
  if (event.schema_version === 1) {
    const data = { ...(event.data ?? {}) } as Record<string, unknown>;
    data.runtime_mode = runtimeModeFromLegacy(data.runtime_mode);
    data.profile_id ??= 'default';
    data.isolation_id ??= 'none';
    data.source_trust ??= 'workspace';
    event.schema_version = 2;
    event.data = data;
  }
  if (event.schema_version > EVENT_SCHEMA_VERSION) {
    return {
      ...event,
      type: 'RAW',
      data: { raw: { ...event } },
    };
  }
  return event;
}

function runtimeModeFromLegacy(value: unknown): 'fake' | 'gated_local' | 'provider_backed' {
  const normalized = typeof value === 'string' ? value.trim().toLowerCase() : 'fake';
  if (normalized === 'offline') return 'fake';
  if (normalized === 'local' || normalized === 'gated') return 'gated_local';
  if (normalized === 'live') return 'provider_backed';
  if (normalized === 'fake' || normalized === 'gated_local' || normalized === 'provider_backed') return normalized;
  return 'fake';
}

export interface ContextPackEntry {
  id: string;
  task: string;
  source: string;
  source_type: string;
  content: string;
  url?: string;
  freshness?: string;
  relevance_score: number;
}

/** Validate an ARC envelope minimally */
export function validateEnvelope(obj: unknown): obj is ArcEnvelope {
  if (typeof obj !== 'object' || obj === null) return false;
  const e = obj as Record<string, unknown>;
  return typeof e['version'] === 'string' && typeof e['ok'] === 'boolean';
}
