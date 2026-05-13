'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { redactValue, safeEvent, REDACTED } = require('../lib/redaction');

test('redacts OpenAI-style keys in strings', () => {
  const out = redactValue('my key is sk-test-redacted-00');
  assert.match(out, new RegExp(REDACTED));
});

test('redacts by key name', () => {
  const out = redactValue({ api_key: 'whatever', name: 'ok' });
  assert.equal(out.api_key, REDACTED);
  assert.equal(out.name, 'ok');
});

test('safeEvent caps oversized payloads', () => {
  const big = { type: 'RAW', event: 'x'.repeat(200000) };
  const out = safeEvent(big);
  assert.equal(out.__truncated, true);
});

test('no-live-provider invariant: secrets in nested tool args redacted', () => {
  const evt = {
    type: 'TOOL_CALL_ARGS',
    toolCallId: 't1',
    delta: { authorization: 'Bearer ghp_redacted' },
  };
  const out = redactValue(evt);
  assert.equal(out.delta.authorization, REDACTED);
});
