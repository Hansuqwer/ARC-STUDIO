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

export interface WorkflowNode {
  id: string;
  label: string;
  type: 'agent' | 'tool' | 'router' | 'start' | 'end' | 'unknown';
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

export interface RunRecord {
  id: string;
  workflow_id: string;
  runtime: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  ended_at?: string;
  events: RunEvent[];
  metadata: Record<string, unknown>;
}

export interface RunEvent {
  type: string;
  timestamp: string;
  run_id: string;
  sequence: number;
  data: Record<string, unknown>;
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
