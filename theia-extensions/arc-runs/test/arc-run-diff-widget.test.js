/** ARC Run Diff Widget Tests */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '../src/browser/arc-run-diff-widget.tsx'), 'utf8');

test('ARC Run Diff widget exists', () => {
  assert.match(source, /class ArcRunDiffWidget/);
});

test('ARC Run Diff fetches diff from backend API', () => {
  assert.match(source, /\/api\/runs\/diff\?run_a=/);
});

test('ARC Run Diff shows selectors for run A and B', () => {
  assert.match(source, /Select Run A/);
  assert.match(source, /Select Run B/);
});
