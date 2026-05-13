const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');

const {
  buildStartRunArgs,
  validateRunId,
  validateOtlpEndpoint,
  resolveWorkspaceRoot,
  safeJoinInsideWorkspace,
} = require('../lib/node/arc-service-impl.js');

describe('buildStartRunArgs', () => {
  test('omits --allow-paid-calls by default', () => {
    const args = buildStartRunArgs({ workflow_id: 'demo' });
    assert.ok(!args.includes('--allow-paid-calls'));
  });

  test('omits --allow-paid-calls when explicitly false', () => {
    const args = buildStartRunArgs({ workflow_id: 'demo', allow_paid_calls: false });
    assert.ok(!args.includes('--allow-paid-calls'));
  });

  test('omits --allow-paid-calls for non-boolean truthy values', () => {
    const args = buildStartRunArgs({ workflow_id: 'demo', allow_paid_calls: 'true' });
    assert.ok(!args.includes('--allow-paid-calls'));
  });

  test('includes --allow-paid-calls only when strictly true', () => {
    const args = buildStartRunArgs({ workflow_id: 'demo', allow_paid_calls: true });
    assert.ok(args.includes('--allow-paid-calls'));
  });

  test('serializes combo runtime selections for the CLI', () => {
    const args = buildStartRunArgs({ workflow_id: 'demo', runtime: ['swarmgraph', 'crewai'] });
    assert.deepEqual(args.slice(0, 4), ['run', 'demo', '--runtime', 'swarmgraph,crewai']);
  });
});

describe('runtime validators', () => {
  let originalEnv;

  beforeEach(() => {
    originalEnv = { ...process.env };
    delete process.env.ARC_OTLP_ALLOW_PRIVATE;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  test('validates run ids', () => {
    assert.equal(validateRunId('run-sg-abcdef'), 'run-sg-abcdef');
    assert.throws(() => validateRunId('../../../etc/passwd'), /invalid run id/);
  });

  test('rejects credentialed and private OTLP endpoints by default', () => {
    assert.throws(() => validateOtlpEndpoint('https://user:pass@example.com/v1/traces'), /credentials/);
    assert.throws(() => validateOtlpEndpoint('http://127.0.0.1:4318/v1/traces'), /private/);
  });

  test('allows private OTLP endpoints only when enabled', () => {
    process.env.ARC_OTLP_ALLOW_PRIVATE = 'true';
    assert.equal(validateOtlpEndpoint('http://127.0.0.1:4318/v1/traces'), 'http://127.0.0.1:4318/v1/traces');
  });

  test('normalizes workspace roots and blocks traversal joins', () => {
    const root = resolveWorkspaceRoot(process.cwd());
    assert.equal(safeJoinInsideWorkspace(root, 'lib').startsWith(root), true);
    assert.throws(() => safeJoinInsideWorkspace(root, '..'), /path escapes workspace/);
  });
});
