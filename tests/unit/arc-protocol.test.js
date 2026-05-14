/**
 * Unit tests: ARC Protocol TypeScript types (via compiled JS)
 * Run with: node tests/unit/arc-protocol.test.js
 *
 * These are plain Node.js tests (no test framework required for CI bootstrap).
 */
'use strict';

const assert = require('assert');
const { makeEnvelope, FIXTURE_WORKSPACE_INFO, FIXTURE_WORKFLOW, FIXTURE_RUN } =
  require('../../packages/arc-test-fixtures/src/index');
const fs = require('fs');
const path = require('path');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}: ${e.message}`);
    failed++;
  }
}

console.log('\nARC Protocol Unit Tests\n');

test('makeEnvelope produces valid structure', () => {
  const env = makeEnvelope({ foo: 'bar' });
  assert.strictEqual(env.version, '1.0');
  assert.strictEqual(env.ok, true);
  assert.deepStrictEqual(env.data, { foo: 'bar' });
  assert.strictEqual(env.error, null);
});

test('FIXTURE_WORKSPACE_INFO has required fields', () => {
  assert.ok(FIXTURE_WORKSPACE_INFO.path);
  assert.ok(Array.isArray(FIXTURE_WORKSPACE_INFO.runtimes));
  assert.ok(typeof FIXTURE_WORKSPACE_INFO.files_scanned === 'number');
});

test('FIXTURE_WORKFLOW has nodes and edges', () => {
  assert.ok(FIXTURE_WORKFLOW.nodes.length >= 2);
  assert.ok(FIXTURE_WORKFLOW.edges.length >= 1);
  assert.ok(FIXTURE_WORKFLOW.entry_points.length >= 1);
});

test('FIXTURE_WORKFLOW edge references exist in nodes', () => {
  const nodeIds = new Set(FIXTURE_WORKFLOW.nodes.map(n => n.id));
  for (const edge of FIXTURE_WORKFLOW.edges) {
    assert.ok(nodeIds.has(edge.from_node), `Edge from unknown node: ${edge.from_node}`);
    assert.ok(nodeIds.has(edge.to_node), `Edge to unknown node: ${edge.to_node}`);
  }
});

test('FIXTURE_RUN has events in order', () => {
  const seqs = FIXTURE_RUN.events.map(e => e.sequence);
  const sorted = [...seqs].sort((a, b) => a - b);
  assert.deepStrictEqual(seqs, sorted);
});

test('FIXTURE_RUN starts with RUN_STARTED event', () => {
  assert.strictEqual(FIXTURE_RUN.events[0].type, 'RUN_STARTED');
});

test('Runtime capabilities not all true (honest caps)', () => {
  const caps = FIXTURE_WORKSPACE_INFO.runtimes[0].capabilities;
  // can_replay should be false in fixture
  assert.strictEqual(caps.can_replay, false);
});

test('Fixture is clearly marked as mock', () => {
  assert.ok(FIXTURE_WORKSPACE_INFO.detection_warnings.some(w => w.includes('[MOCK]')));
  assert.ok(FIXTURE_WORKFLOW.metadata._mock === true);
  assert.ok(FIXTURE_RUN.metadata._mock === true);
});

test('Theia startRun uses positional workflow CLI argument', () => {
  const servicePath = path.join(__dirname, '../../theia-extensions/arc-core/src/node/arc-service-impl.ts');
  const source = fs.readFileSync(servicePath, 'utf8');
  assert.ok(source.includes("const args = ['run', request.workflow_id,"));
  assert.ok(!source.includes("['run', '--workflow',"));
});

test('Theia backend error envelope preserves sanitized details', () => {
  const servicePath = path.join(__dirname, '../../theia-extensions/arc-core/src/node/arc-service-impl.ts');
  const source = fs.readFileSync(servicePath, 'utf8');
  assert.ok(source.includes('details: {'));
  assert.ok(source.includes('command,'));
  assert.ok(source.includes('stderr'));
  assert.ok(source.includes('stdout'));
  assert.ok(source.includes('sanitize'));
  assert.ok(source.includes('REDACTED'));
});

test('Theia backend does not expose normal mock fallback', () => {
  const servicePath = path.join(__dirname, '../../theia-extensions/arc-core/src/node/arc-service-impl.ts');
  const source = fs.readFileSync(servicePath, 'utf8');
  assert.ok(source.includes('errorEnvelope'));
  assert.ok(!source.includes('mockFallback'));
  assert.ok(!source.includes('MOCK_DATA'));
});

console.log(`\n  ${passed} passed, ${failed} failed\n`);
if (failed > 0) process.exit(1);
