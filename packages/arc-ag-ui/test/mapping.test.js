'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { mapEvent, AGUIEventType } = require('../lib');
require('../lib/mapping/swarmgraph');
require('../lib/mapping/langgraph');

function loadJsonl(p) {
  return fs.readFileSync(p, 'utf8').trim().split('\n').map(l => JSON.parse(l));
}

function stripVolatile(evts) {
  return evts.map(e => {
    const { timestamp, rawEvent, ...rest } = e;
    return rest;
  });
}

const ctx = { threadId: 'th-1', runId: 'r1', runtime: 'swarmgraph' };

test('swarmgraph mapping matches golden', () => {
  const input = loadJsonl(path.join(__dirname, 'fixtures/swarmgraph.input.jsonl'));
  const expected = loadJsonl(path.join(__dirname, 'fixtures/swarmgraph.expected.jsonl'));
  const got = input.flatMap(e => mapEvent('swarmgraph', e, ctx));
  assert.deepEqual(stripVolatile(got), expected);
});

test('langgraph mapping matches golden', () => {
  const ctx2 = { ...ctx, runtime: 'langgraph' };
  const input = loadJsonl(path.join(__dirname, 'fixtures/langgraph.input.jsonl'));
  const expected = loadJsonl(path.join(__dirname, 'fixtures/langgraph.expected.jsonl'));
  const got = input.flatMap(e => mapEvent('langgraph', e, ctx2));
  assert.deepEqual(stripVolatile(got), expected);
});

test('unknown runtime falls through to RAW', () => {
  const got = mapEvent('mystery', { foo: 1 }, ctx);
  assert.equal(got.length, 1);
  assert.equal(got[0].type, AGUIEventType.RAW);
});

test('mapper exception becomes RUN_ERROR', () => {
  const { registerMapper } = require('../lib/mapper');
  registerMapper({
    runtime: 'broken',
    map() { throw new Error('boom'); }
  });
  const got = mapEvent('broken', {}, ctx);
  assert.equal(got[0].type, AGUIEventType.RUN_ERROR);
  assert.equal(got[0].code, 'MAPPER_THREW');
});
