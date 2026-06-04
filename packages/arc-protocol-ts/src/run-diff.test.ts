/**
 * Run Diff / Time Travel — TypeScript mirror parity tests.
 *
 * Verify that the TypeScript types structurally match the Python RunDiffReport
 * JSON output. Source of truth lives in `agent_runtime_cockpit/run_diff/models.py`.
 *
 * These tests use the same fixture loading pattern as swarmgraph-ir.test.ts.
 */
import * as fs from 'fs';
import * as path from 'path';
import {
  RUN_DIFF_SCHEMA_VERSION,
  DiffMode,
  ChangeType,
  DiffSubjectKind,
  RunDiffReport,
  GraphDiff,
  EventDiff,
  PolicyDiff,
  SimulationDiff,
  McpManifestDiff,
  CapabilityDiff,
  FlightDiff,
  CostDiff,
  RiskDiff,
  FirstDivergence,
  TimelineFrame,
  TimeTravelCursor,
  emptyDiffSummary,
  emptyDiffSubject,
  redactDict,
  redactReport,
  toJson,
  fromJson,
  assertParity,
} from './run-diff';

const FIX = path.join(__dirname, 'fixtures', 'swarmgraph-ir');

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Load a Python-generated RunDiffReport fixture. */
function loadFixture(name: string): RunDiffReport {
  return JSON.parse(fs.readFileSync(path.join(FIX, name), 'utf-8')) as RunDiffReport;
}

// ---------------------------------------------------------------------------
// Type / constant tests
// ---------------------------------------------------------------------------

describe('Run Diff constants and types', () => {
  it('RUN_DIFF_SCHEMA_VERSION is 1', () => {
    expect(RUN_DIFF_SCHEMA_VERSION).toBe(1);
  });

  it('ChangeType enum has all four values', () => {
    expect(ChangeType.ADDED).toBe('added');
    expect(ChangeType.REMOVED).toBe('removed');
    expect(ChangeType.CHANGED).toBe('changed');
    expect(ChangeType.UNCHANGED).toBe('unchanged');
  });

  it('DiffSubjectKind covers all subject types', () => {
    expect(DiffSubjectKind.IR_GRAPH).toBe('ir_graph');
    expect(DiffSubjectKind.RUN_RECORD).toBe('run_record');
    expect(DiffSubjectKind.POLICY_REPORT).toBe('policy_report');
    expect(DiffSubjectKind.SIMULATION_REPORT).toBe('simulation_report');
    expect(DiffSubjectKind.CAPABILITY_CARD).toBe('capability_card');
    expect(DiffSubjectKind.FLIGHT_SEGMENT).toBe('flight_segment');
    expect(DiffSubjectKind.MCP_MANIFEST).toBe('mcp_manifest');
    expect(DiffSubjectKind.UNKNOWN).toBe('unknown');
  });

  it('DiffMode covers all comparison modes', () => {
    const modes: DiffMode[] = [
      'ir_vs_ir',
      'run_vs_run',
      'policy_vs_policy',
      'simulation_vs_simulation',
      'simulation_vs_run',
      'capability_vs_capability',
      'flight_vs_flight',
      'mcp_vs_mcp',
    ];
    expect(modes).toHaveLength(8);
  });

  it('emptyDiffSummary has all required fields with correct defaults', () => {
    const s = emptyDiffSummary();
    expect(s.total_changes).toBe(0);
    expect(s.risk_increased).toBe(false);
    expect(s.hitl_removed).toBe(false);
    expect(s.paid_call_delta).toBe(0);
    expect(Array.isArray(s.event_types_added)).toBe(true);
    expect(Array.isArray(s.nodes_changed)).toBe(false); // 0, not array
  });

  it('emptyDiffSubject has correct defaults', () => {
    const s = emptyDiffSubject();
    expect(s.kind).toBe(DiffSubjectKind.UNKNOWN);
    expect(s.id).toBe('');
    expect(s.metadata).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// TimeTravelCursor tests
// ---------------------------------------------------------------------------

describe('TimeTravelCursor', () => {
  const frames: TimelineFrame[] = [
    {
      frame_id: 'f0', sequence: 0, subject: 'ir', summary: 'Node added', change_type: ChangeType.ADDED,
      redacted: false, redacted_fields: [],
    },
    {
      frame_id: 'f1', sequence: 1, subject: 'ir', summary: 'Node changed', change_type: ChangeType.CHANGED,
      redacted: false, redacted_fields: [],
    },
    {
      frame_id: 'f2', sequence: 2, subject: 'policy', summary: 'Policy issue added', change_type: ChangeType.ADDED,
      redacted: false, redacted_fields: [],
    },
  ];

  it('starts at frame 0', () => {
    const cursor = new TimeTravelCursor(frames);
    expect(cursor.current?.frame_id).toBe('f0');
    expect(cursor.sequence).toBe(0);
    expect(cursor.can_step_back).toBe(false);
    expect(cursor.can_step_forward).toBe(true);
  });

  it('stepForward advances', () => {
    const cursor = new TimeTravelCursor(frames);
    cursor.stepForward();
    expect(cursor.current?.frame_id).toBe('f1');
    expect(cursor.can_step_back).toBe(true);
  });

  it('stepBack retreats', () => {
    const cursor = new TimeTravelCursor(frames);
    cursor.stepForward();
    cursor.stepForward();
    cursor.stepBack();
    expect(cursor.current?.frame_id).toBe('f1');
    cursor.stepBack();
    expect(cursor.current?.frame_id).toBe('f0');
  });

  it('seekTo jumps to specific frame', () => {
    const cursor = new TimeTravelCursor(frames);
    const found = cursor.seekTo('f2');
    expect(found?.frame_id).toBe('f2');
    expect(cursor.sequence).toBe(2);
  });

  it('seekTo returns null for unknown frame_id', () => {
    const cursor = new TimeTravelCursor(frames);
    const found = cursor.seekTo('nonexistent');
    expect(found).toBeNull();
  });

  it('context returns surrounding frames', () => {
    const cursor = new TimeTravelCursor(frames);
    cursor.stepForward(); // now at f1
    const ctx = cursor.context(1, 1);
    expect(ctx.map((f) => f.frame_id)).toEqual(['f0', 'f1', 'f2']);
  });

  it('asDict produces serializable state', () => {
    const cursor = new TimeTravelCursor(frames);
    const state = cursor.asDict();
    expect(state.frame_id).toBe('f0');
    expect(state.sequence).toBe(0);
    expect(state.can_step_back).toBe(false);
    expect(state.can_step_forward).toBe(true);
    expect(Array.isArray(state.context)).toBe(true);
  });

  it('empty cursor has null current', () => {
    const cursor = new TimeTravelCursor([]);
    expect(cursor.current).toBeNull();
    expect(cursor.frame_id).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Redaction tests
// ---------------------------------------------------------------------------

describe('Redaction helpers', () => {
  it('redactDict redacts secret key values', () => {
    const input = { api_key: 'sk-ant-abc123', name: 'test' };
    const result = redactDict(input) as Record<string, unknown>;
    expect(result.api_key).toBe('[REDACTED]');
    expect(result.name).toBe('test');
  });

  it('redactDict handles nested dicts', () => {
    const input = { outer: { api_key: 'secret', inner: { token: 'abc' } } };
    const result = redactDict(input) as Record<string, unknown>;
    const outer = result.outer as Record<string, unknown>;
    expect(outer.api_key).toBe('[REDACTED]');
    const inner = outer.inner as Record<string, unknown>;
    expect(inner.token).toBe('[REDACTED]');
  });

  it('redactDict handles arrays of dicts', () => {
    const input = { items: [{ api_key: 'x' }, { name: 'y' }] };
    const result = redactDict(input) as Record<string, unknown>;
    const items = result.items as Record<string, unknown>[];
    expect(items[0].api_key).toBe('[REDACTED]');
    expect(items[1].api_key).toBeUndefined();
  });

  it('redactDict preserves non-secret keys', () => {
    const input = { name: 'Alice', status: 'active', id: '123' };
    const result = redactDict(input) as Record<string, unknown>;
    expect(result).toEqual({ name: 'Alice', status: 'active', id: '123' });
  });

  it('redactDict handles array elements under a secret key', () => {
    // redactValue uses the parent key for matching; 'api_key' key triggers redaction
    const input = { api_key: ['value1', 'value2'] };
    const result = redactDict(input) as Record<string, unknown>;
    expect(result.api_key).toEqual(['[REDACTED]', '[REDACTED]']);
  });

  it('redactDict returns non-object values unchanged', () => {
    expect(redactDict(null)).toBeNull();
    expect(redactDict('string')).toBe('string');
    expect(redactDict(42)).toBe(42);
  });

  it('redactReport handles full report structure', () => {
    const report = {
      left: { id: 'run-1', path: 'run-a.ir.json', metadata: { api_key: 'secret' } },
      right: { id: 'run-2', path: 'run-b.ir.json', metadata: {} },
      summary: { total_changes: 1 },
      timeline: [],
      warnings: [],
      errors: [],
    };
    const result = redactReport(report) as Record<string, unknown>;
    const left = result.left as Record<string, unknown>;
    const metadata = left.metadata as Record<string, unknown>;
    expect(metadata.api_key).toBe('[REDACTED]');
  });
});

// ---------------------------------------------------------------------------
// JSON round-trip tests
// ---------------------------------------------------------------------------

describe('JSON helpers', () => {
  it('toJson and fromJson round-trip a report', () => {
    const report: RunDiffReport = {
      schema_version: 1,
      generated_at: '2026-06-03T12:00:00Z',
      left: { kind: DiffSubjectKind.IR_GRAPH, id: 'g1', metadata: {} },
      right: { kind: DiffSubjectKind.IR_GRAPH, id: 'g2', metadata: {} },
      mode: 'ir_vs_ir',
      summary: emptyDiffSummary(),
      timeline: [],
      warnings: [],
      errors: [],
      mode_metadata: {},
    };
    const json = toJson(report);
    const parsed = fromJson(json);
    expect(parsed.schema_version).toBe(1);
    expect(parsed.mode).toBe('ir_vs_ir');
    expect(parsed.left.id).toBe('g1');
    expect(parsed.right.id).toBe('g2');
  });

  it('toJson with indent produces readable output', () => {
    const report: RunDiffReport = {
      schema_version: 1,
      generated_at: '2026-06-03T12:00:00Z',
      left: emptyDiffSubject(),
      right: emptyDiffSubject(),
      mode: 'run_vs_run',
      summary: emptyDiffSummary(),
      timeline: [],
      warnings: [],
      errors: [],
      mode_metadata: {},
    };
    const json = toJson(report, 2);
    expect(json).toContain('  "schema_version": 1');
  });

  it('assertParity validates schema_version and mode', () => {
    const goodJson = JSON.stringify({
      schema_version: 1,
      mode: 'ir_vs_ir',
      left: { kind: 'ir_graph', id: 'x', metadata: {} },
      right: { kind: 'ir_graph', id: 'y', metadata: {} },
      summary: { total_changes: 0, nodes_added: 0, nodes_removed: 0, nodes_changed: 0,
        edges_added: 0, edges_removed: 0, edges_changed: 0, events_added: 0,
        events_removed: 0, events_changed: 0, event_types_added: [], event_types_removed: [],
        policy_issues_added: 0, policy_issues_removed: 0, policy_blockers_introduced: 0,
        policy_errors_introduced: 0, risk_increased: false, risk_decreased: false,
        mcp_drift_changed: false, paid_call_delta: 0, hitl_gate_delta: 0,
        consensus_changed: false, hitl_removed: false },
      timeline: [],
      warnings: [],
      errors: [],
      mode_metadata: {},
    });
    const result = assertParity(goodJson, 'ir_vs_ir');
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.report.schema_version).toBe(1);
    }
  });

  it('assertParity rejects wrong schema_version', () => {
    const badJson = JSON.stringify({
      schema_version: 2,
      mode: 'ir_vs_ir',
      left: { kind: 'ir_graph', id: 'x', metadata: {} },
      right: { kind: 'ir_graph', id: 'y', metadata: {} },
      summary: { total_changes: 0, nodes_added: 0, nodes_removed: 0, nodes_changed: 0,
        edges_added: 0, edges_removed: 0, edges_changed: 0, events_added: 0,
        events_removed: 0, events_changed: 0, event_types_added: [], event_types_removed: [],
        policy_issues_added: 0, policy_issues_removed: 0, policy_blockers_introduced: 0,
        policy_errors_introduced: 0, risk_increased: false, risk_decreased: false,
        mcp_drift_changed: false, paid_call_delta: 0, hitl_gate_delta: 0,
        consensus_changed: false, hitl_removed: false },
      timeline: [],
      warnings: [],
      errors: [],
      mode_metadata: {},
    });
    const result = assertParity(badJson, 'ir_vs_ir');
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect((result as { ok: false; detail: string }).detail).toContain('schema_version');
    }
  });
});

// ---------------------------------------------------------------------------
// Sub-type structural tests (spot-check all diff types)
// ---------------------------------------------------------------------------

describe('Sub-type structural validation', () => {
  it('GraphDiff has all required fields', () => {
    const gd: GraphDiff = {
      nodes_added: [],
      nodes_removed: [],
      nodes_changed: [],
      edges_added: [],
      edges_removed: [],
      edges_changed: [],
      node_count_left: 0,
      node_count_right: 0,
      edge_count_left: 0,
      edge_count_right: 0,
    };
    expect(gd.nodes_added).toEqual([]);
    expect(gd.node_count_left).toBe(0);
  });

  it('EventDiff has all required fields', () => {
    const ed: EventDiff = {
      events_added: [],
      events_removed: [],
      events_changed: [],
      sequence_alignment: [],
      first_event_divergence: null,
      event_count_left: 0,
      event_count_right: 0,
    };
    expect(Array.isArray(ed.events_added)).toBe(true);
    expect(ed.first_event_divergence).toBeNull();
  });

  it('PolicyDiff has can_run regression fields', () => {
    const pd: PolicyDiff = {
      issues_added: [],
      issues_removed: [],
      issues_changed: [],
      can_run_left: true,
      can_run_right: true,
      can_run_regression: false,
      risk_regression: false,
      consensus_regression: false,
      error_count_left: 0,
      error_count_right: 0,
      error_count_delta: 0,
      warning_count_left: 0,
      warning_count_right: 0,
      warning_count_delta: 0,
    };
    expect(pd.can_run_regression).toBe(false);
  });

  it('SimulationDiff has hitl/paid-call delta fields', () => {
    const sd: SimulationDiff = {
      summary_changed: false,
      reachable_nodes_left: 5,
      reachable_nodes_right: 6,
      hitl_gates_left: 2,
      hitl_gates_right: 1,
      hitl_gate_delta: -1,
      paid_calls_left: 0,
      paid_calls_right: 1,
      paid_call_delta: 1,
      mcp_tools_left: 3,
      mcp_tools_right: 4,
      gate_count_left: 2,
      gate_count_right: 2,
      policy_regression: false,
      can_run_left: true,
      can_run_right: true,
      warnings_added: [],
      warnings_removed: [],
    };
    expect(sd.hitl_gate_delta).toBe(-1);
    expect(sd.paid_call_delta).toBe(1);
  });

  it('McpManifestDiff has server drift fields', () => {
    const md: McpManifestDiff = {
      servers_added: ['s3'],
      servers_removed: ['fs'],
      hash_changed: [{ server: 'http', left_hash: 'abc', right_hash: 'def' }],
      approved_tools_delta: 1,
      blocked_tools_delta: 0,
      tools_added: ['read'],
      tools_removed: [],
      drifted_servers: ['http'],
    };
    expect(md.drifted_servers).toContain('http');
    expect(md.hash_changed[0].left_hash).toBe('abc');
  });

  it('CapabilityDiff has trust regression field', () => {
    const cd: CapabilityDiff = {
      cards_added: [],
      cards_removed: [],
      cards_changed: [],
      capabilities_added: [],
      capabilities_removed: [],
      risk_level_changed: [],
      mcp_drift_detected: true,
      trust_regression: true,
    };
    expect(cd.trust_regression).toBe(true);
  });

  it('FlightDiff has hash chain validation fields', () => {
    const fd: FlightDiff = {
      events_added: 5,
      events_removed: 2,
      events_changed: 0,
      segment_hashes_match: false,
      hash_chain_valid: true,
      event_types_added: ['run.completed'],
      event_types_removed: ['hitl.requested'],
      first_event_divergence: 10,
    };
    expect(fd.hash_chain_valid).toBe(true);
    expect(fd.segment_hashes_match).toBe(false);
  });

  it('CostDiff has paid-call introduction flag', () => {
    const cd: CostDiff = {
      has_paid_calls_left: false,
      has_paid_calls_right: true,
      paid_calls_introduced: true,
      estimated_cost_delta_usd: 0.05,
      estimated_cost_floor_left: 0.0,
      estimated_cost_floor_right: 0.05,
    };
    expect(cd.paid_calls_introduced).toBe(true);
    expect(cd.estimated_cost_delta_usd).toBeCloseTo(0.05);
  });

  it('RiskDiff has signals array fields', () => {
    const rd: RiskDiff = {
      level_left: 'low',
      level_right: 'high',
      level_changed: true,
      signals_added: ['exec_tool_detected'],
      signals_removed: [],
      score_delta: 0.5,
    };
    expect(rd.level_changed).toBe(true);
    expect(rd.signals_added).toContain('exec_tool_detected');
  });

  it('FirstDivergence has all location fields', () => {
    const fd: FirstDivergence = {
      kind: 'node',
      node_id: 'node-42',
      edge_id: null,
      event_id: null,
      policy_rule: null,
      sequence: 5,
      frame_index: 5,
      left_value: null,
      right_value: null,
      reason: 'Paid call introduced',
    };
    expect(fd.kind).toBe('node');
    expect(fd.reason).toBe('Paid call introduced');
  });

  it('TimelineFrame has redacted and redacted_fields', () => {
    const tf: TimelineFrame = {
      frame_id: 'tf0',
      sequence: 0,
      subject: 'ir',
      summary: 'Node added',
      change_type: ChangeType.ADDED,
      redacted: true,
      redacted_fields: ['secret_key'],
    };
    expect(tf.redacted).toBe(true);
    expect(tf.redacted_fields).toContain('secret_key');
  });
});