/**
 * Performance tests for virtualized event list
 * Verifies that the AG-UI mapping layer can handle 1000+ events efficiently
 */

const { test } = require('node:test');
const assert = require('node:assert');
const { mapEvent, AGUIEventType } = require('../lib/index.js');

// SwarmGraphMapper is auto-registered on import

// Generate large event dataset
function generateLargeEventSet(count) {
  const events = [];
  const eventKinds = [
    'run.start',
    'run.finish',
    'agent.text',
    'tool.call',
    'state',
    'handoff',
  ];
  
  for (let i = 0; i < count; i++) {
    const kind = eventKinds[i % eventKinds.length];
    const event = {
      kind,
      ts: Date.now() + i * 1000,
    };
    
    if (kind === 'agent.text') {
      event.text = `Message ${i}`;
    } else if (kind === 'tool.call') {
      event.tool = { id: `tool-${i}`, name: `tool_${i % 5}`, args: {}, result: {} };
    } else if (kind === 'state') {
      event.state = { step: i };
    }
    
    events.push(event);
  }
  
  return events;
}

test('maps 1000 events in under 100ms', () => {
  const events = generateLargeEventSet(1000);
  const ctx = { threadId: 'perf-thread', runId: 'perf-run', runtime: 'swarmgraph' };
  const startTime = Date.now();
  
  const mapped = events.flatMap(event => mapEvent('swarmgraph', event, ctx));
  
  const duration = Date.now() - startTime;
  
  assert.ok(mapped.length >= 1000, 'Should map at least 1000 events');
  assert.ok(duration < 100, `Mapping 1000 events took ${duration}ms (should be < 100ms)`);
  
  // Verify all events were mapped correctly
  mapped.forEach((event, idx) => {
    assert.ok(event.type, `Event ${idx} should have a type`);
    assert.ok(Object.values(AGUIEventType).includes(event.type), `Event ${idx} type should be valid AG-UI type`);
  });
});

test('maps 10000 events in under 1000ms', () => {
  const events = generateLargeEventSet(10000);
  const ctx = { threadId: 'perf-thread', runId: 'perf-run', runtime: 'swarmgraph' };
  const startTime = Date.now();
  
  const mapped = events.flatMap(event => mapEvent('swarmgraph', event, ctx));
  
  const duration = Date.now() - startTime;
  
  assert.ok(mapped.length >= 10000, 'Should map at least 10000 events');
  assert.ok(duration < 1000, `Mapping 10000 events took ${duration}ms (should be < 1000ms)`);
});

test('redaction performance with 1000 events', () => {
  const { safeEvent } = require('../lib/index.js');
  const events = generateLargeEventSet(1000).map(e => ({
    ...e,
    api_key: 'sk-1234567890abcdef',
    token: 'ghp_abcdefghijklmnop',
  }));
  
  const startTime = Date.now();
  
  const redacted = events.map(event => safeEvent(event));
  
  const duration = Date.now() - startTime;
  
  assert.strictEqual(redacted.length, 1000, 'Should redact all 1000 events');
  assert.ok(duration < 50, `Redacting 1000 events took ${duration}ms (should be < 50ms)`);
  
  // Verify redaction worked
  redacted.forEach((data, idx) => {
    assert.strictEqual(data.api_key, '«REDACTED»', `Event ${idx} api_key should be redacted`);
    assert.strictEqual(data.token, '«REDACTED»', `Event ${idx} token should be redacted`);
  });
});
