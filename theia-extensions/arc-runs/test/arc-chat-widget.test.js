const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../src/browser/arc-chat-widget.tsx'), 'utf8');

test('ARC Chat submits prompts via ArcFrontendService.startRun', () => {
  assert.match(source, /class ArcChatWidget/);
  assert.match(source, /this\.arcService\.startRun\('wf-swarmgraph-001', \{ prompt \}/);
});

test('ARC Chat exposes combo runtime selection and readiness messaging', () => {
  assert.match(source, /selectedRuntimes = new Set<RuntimeId>/);
  assert.match(source, /return combo\.length > 1 \? combo : this\.selectedRuntime/);
  assert.match(source, /Set \$\{runtime\.required_env\.join\(', '\)\}\./);
  assert.match(source, /Allow paid\/provider calls/);
});
