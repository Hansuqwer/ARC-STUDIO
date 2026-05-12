/**
 * ARC Protocol — TypeScript schema definitions
 *
 * These mirror the Python Pydantic models in python/src/agent_runtime_cockpit/protocol/
 * Source: docs/DECISIONS/ADR-0002-python-daemon-json-boundary.md
 */

/** ARC Protocol version */
export const ARC_PROTOCOL_VERSION = '1.0';

/** Standard envelope for all ARC responses */
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

/** Workspace inspection result */
export interface WorkspaceInfo {
  path: string;
  runtimes: RuntimeInfo[];
  files_scanned: number;
  detection_warnings: string[];
}

/** A detected runtime adapter */
export interface RuntimeInfo {
  id: string;
  name: string;
  adapter: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: string[];
  capabilities: RuntimeCapabilities;
}

export interface RuntimeCapabilities {
  can_inspect: boolean;
  can_run: boolean;
  can_trace: boolean;
  can_replay: boolean;
  can_export_schema: boolean;
  can_export_workflow: boolean;
}

/** Workflow topology */
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

/** Schema info */
export interface SchemaInfo {
  id: string;
  name: string;
  runtime: string;
  schema: Record<string, unknown>;  // JSON Schema
  source_file?: string;
}

/** Run record */
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

/** AG-UI compatible run event */
export interface RunEvent {
  type: string;
  timestamp: string;
  run_id: string;
  sequence: number;
  data: Record<string, unknown>;
}

/** Context pack entry */
export interface ContextPackEntry {
  id: string;
  task: string;
  source: string;
  source_type: 'local_repo' | 'context7' | 'vercel_grep' | 'github_search' | 'web_search';
  content: string;
  url?: string;
  freshness?: string;
  relevance_score: number;
}

export interface ProviderStatus {
  provider: string;
  baseUrlConfigured: boolean;
  apiKeyConfigured: boolean;
  apiKeySource?: string;
  runtimeAvailable: boolean;
  message: string;
}

/** Source location for jump-to-definition */
export interface SourceLocation {
  file: string;
  line: number;
  column?: number;
}

/** ARC Service path identifier for Theia IPC */
export const ARC_SERVICE_PATH = '/services/arc-core';

/** ARC Service interface (frontend ↔ backend IPC) */
export const ArcServiceSymbol = Symbol('ArcService');

export interface ArcService {
  inspectWorkspace(workspacePath: string): Promise<ArcEnvelope<WorkspaceInfo>>;
  listRuntimes(workspacePath: string): Promise<ArcEnvelope<RuntimeInfo[]>>;
  listWorkflows(workspacePath: string, runtimeId?: string): Promise<ArcEnvelope<WorkflowInfo[]>>;
  listSchemas(workspacePath: string, runtimeId?: string): Promise<ArcEnvelope<SchemaInfo[]>>;
  startRun(workflowId: string, inputs?: Record<string, unknown>): Promise<ArcEnvelope<RunRecord>>;
  getRun(runId: string): Promise<ArcEnvelope<RunRecord>>;
  listRuns(workspacePath: string): Promise<ArcEnvelope<RunRecord[]>>;
  generateContextPack(task: string, workspacePath?: string): Promise<ArcEnvelope<ContextPackEntry[]>>;
  getDaemonStatus(): Promise<ArcEnvelope<{ running: boolean; version: string; pid?: number }>>;
  getProviderStatus(provider: string, baseUrl?: string): Promise<ArcEnvelope<ProviderStatus>>;
  getWorkspaceStatus(workspacePath: string): Promise<ArcEnvelope<{ frontendPath: string; backendPath: string; source: string }>>;
}
