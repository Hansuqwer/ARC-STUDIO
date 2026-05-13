const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

test('ARC: Start Run command opens ARC Chat', () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/browser/arc-command-contribution.ts'), 'utf8');
  assert.match(source, /START_RUN[\s\S]*executeCommand\('arc:open-chat'\)/);
  assert.doesNotMatch(source, /Run launcher coming in next iteration/);
});
