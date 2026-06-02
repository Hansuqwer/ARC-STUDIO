/**
 * SwarmGraph IR — TypeScript mirror of the Python IR models.
 *
 * Read-only structural mirror of
 * `agent_runtime_cockpit/swarmgraph_ir/models.py`. Used by the Theia workflow
 * graph widget and `arc ir` JSON output. Keep field names in sync with the
 * Python models (parity is asserted in swarmgraph-ir.test.ts).
 *
 * This describes a normalization & analysis IR. It is NOT an execution plan.
 */

export const IR_SCHEMA_VERSION = 1;

export type IRRiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type IRNodeKind =
  | 'agent'
  | 'tool'
  | 'mcp_tool'
  | 'model_call'
  | 'human_gate'
  | 'consensus'
  | 'router'
  | 'fan_out'
  | 'fan_in'
  | 'start'
  | 'end'
  | 'unknown';

export type IRSideEffectKind =
  | 'none'
  | 'read'
  | 'write'
  | 'network'
  | 'paid_call'
  | 'exec'
  | 'secret_read';

export interface IRRisk {
  level: IRRiskLevel;
  score: number;
  signals: string[];
  rationale?: string | null;
  source: 'sdk' | 'heuristic' | 'manual';
}

export interface IRCapabilityRequirement {
  capability: string;
  reason?: string | null;
  optional: boolean;
}

export interface IRSideEffect {
  kind: IRSideEffectKind;
  target?: string | null;
  paid: boolean;
  confidence: number;
}

export interface IRBudget {
  tokens?: number | null;
  cost_usd?: number | null;
  latency_ms?: number | null;
  requires_paid_call: boolean;
  paid_call_gate: boolean;
}

export interface IRToolRef {
  name: string;
  namespace?: string | null;
  pinned: boolean;
  capabilities: IRCapabilityRequirement[];
}

export interface IRMcpToolRef {
  server_id: string;
  tool_name: string;
  manifest_hash?: string | null;
  can_write: boolean;
  can_network: boolean;
  can_read_secrets: boolean;
  accesses_outside_workspace: boolean;
  risk_level: 'low' | 'medium' | 'high';
  approved: boolean;
  blocked: boolean;
}

export interface IRModelCall {
  provider?: string | null;
  model?: string | null;
  paid: boolean;
  budget?: IRBudget | null;
}

export interface IRHumanGate {
  gate_id: string;
  blocking: boolean;
  prompt?: string | null;
  trust_required?: number | null;
}

export interface IRConsensusHint {
  protocol?: string | null;
  suggested_protocol?: string | null;
  min_workers?: number | null;
  source: 'sdk' | 'metadata' | 'default';
}

export interface IRAuditBoundary {
  boundary_id: string;
  reason: string;
  audit_level: 'none' | 'arc_sha256' | 'swarmgraph_hmac';
}

export interface IRReplayMarker {
  marker_id: string;
  node_id: string;
  correlation_key: string;
}

export interface IRAdapterProvenance {
  adapter_id: string;
  runtime: string;
  adapter_version?: string | null;
  source_file?: string | null;
  exported_via: string;
  imported_at?: string | null;
}

export interface IRNode {
  id: string;
  label: string;
  kind: IRNodeKind;
  tool?: IRToolRef | null;
  mcp_tool?: IRMcpToolRef | null;
  model_call?: IRModelCall | null;
  human_gate?: IRHumanGate | null;
  consensus?: IRConsensusHint | null;
  risk: IRRisk;
  capabilities: IRCapabilityRequirement[];
  side_effects: IRSideEffect[];
  budget?: IRBudget | null;
  audit_boundary?: IRAuditBoundary | null;
  replay_marker?: IRReplayMarker | null;
  trust_annotation?: string | null;
  privileged: boolean;
  write_path?: string | null;
  eval_metadata: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface IREdge {
  id: string;
  from_node: string;
  to_node: string;
  conditional: boolean;
  condition?: string | null;
  label?: string | null;
  metadata: Record<string, unknown>;
}

export interface IRValidationReport {
  ok: boolean;
  errors: string[];
  warnings: string[];
  node_count: number;
  edge_count: number;
}

export interface IRGraph {
  ir_version: number;
  id: string;
  name: string;
  runtime: string;
  provenance: IRAdapterProvenance;
  nodes: IRNode[];
  edges: IREdge[];
  entry_points: string[];
  risk: IRRisk;
  consensus: IRConsensusHint;
  graph_hash?: string | null;
  compiled_at?: string | null;
  metadata: Record<string, unknown>;
}
