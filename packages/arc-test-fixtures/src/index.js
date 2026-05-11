/**
 * ARC Test Fixtures — shared mock data for unit/E2E tests.
 * All fixtures are clearly marked as mock data.
 *
 * MOCK_REASON: Provides stable test data independent of live services.
 * REAL_IMPLEMENTATION_PATH: Replace with live service calls in integration tests.
 */

'use strict';

const FIXTURE_WORKSPACE_INFO = {
  path: '/workspace/sample-swarmgraph-project',
  runtimes: [
    {
      id: 'swarmgraph-test-001',
      name: 'SwarmGraph (test fixture)',
      adapter: 'swarmgraph',
      confidence: 'high',
      evidence: ['swarmgraph.yaml found', '[MOCK fixture]'],
      capabilities: {
        can_inspect: true, can_run: true, can_trace: true,
        can_replay: false, can_export_schema: true, can_export_workflow: true,
      },
    },
  ],
  files_scanned: 5,
  detection_warnings: ['[MOCK] Test fixture workspace'],
};

const FIXTURE_WORKFLOW = {
  id: 'wf-test-001',
  name: 'ResearchSwarm (test)',
  runtime: 'swarmgraph',
  nodes: [
    { id: 'start', label: 'Start', type: 'start', metadata: {} },
    { id: 'researcher', label: 'Researcher', type: 'agent', metadata: {} },
    { id: 'end', label: 'End', type: 'end', metadata: {} },
  ],
  edges: [
    { id: 'e1', from_node: 'start', to_node: 'researcher', conditional: false, metadata: {} },
    { id: 'e2', from_node: 'researcher', to_node: 'end', conditional: false, metadata: {} },
  ],
  entry_points: ['start'],
  metadata: { _mock: true },
};

const FIXTURE_RUN = {
  id: 'run-test-001',
  workflow_id: 'wf-test-001',
  runtime: 'swarmgraph',
  status: 'completed',
  started_at: new Date(Date.now() - 5000).toISOString(),
  ended_at: new Date().toISOString(),
  events: [
    { type: 'RUN_STARTED', timestamp: new Date().toISOString(), run_id: 'run-test-001', sequence: 0, data: {} },
    { type: 'RUN_COMPLETED', timestamp: new Date().toISOString(), run_id: 'run-test-001', sequence: 1, data: {} },
  ],
  metadata: { _mock: true },
};

function makeEnvelope(data) {
  return { version: '1.0', ok: true, data, error: null, meta: { timestamp: new Date().toISOString() } };
}

module.exports = {
  FIXTURE_WORKSPACE_INFO,
  FIXTURE_WORKFLOW,
  FIXTURE_RUN,
  makeEnvelope,
};

// Self-test
if (require.main === module) {
  console.log('ARC test fixtures OK');
  console.log('  workspace:', FIXTURE_WORKSPACE_INFO.path);
  console.log('  workflow nodes:', FIXTURE_WORKFLOW.nodes.length);
  console.log('  run events:', FIXTURE_RUN.events.length);
}
