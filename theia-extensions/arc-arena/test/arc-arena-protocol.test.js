const assert = require('node:assert/strict');
const { describe, it } = require('node:test');

describe('ARC Arena Protocol Types', () => {
  it('has correct mode values', () => {
    const modes = ['battle', 'direct', 'code', 'agent-arena-preview'];
    assert.equal(modes.length, 4);
    assert.ok(modes.includes('battle'));
    assert.ok(modes.includes('direct'));
    assert.ok(modes.includes('code'));
    assert.ok(modes.includes('agent-arena-preview'));
  });

  it('has correct privacy levels', () => {
    const levels = ['Private', 'Debug', 'Research'];
    assert.equal(levels.length, 3);
  });
});
