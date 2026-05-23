import { describe, expect, it } from '@jest/globals';

import * as protocol from './index';
import {
  assertNeverEvent,
  isEventOfType,
  isKnownEvent,
  parseRunEvent,
  TypedRunEvent,
} from './run-events';

const baseEvent = {
  schema_version: 2,
  type: 'RUN_STARTED',
  timestamp: '2026-05-23T00:00:00.000Z',
  run_id: 'run-1',
  sequence: 1,
  data: { workflow_id: 'wf-1', runtime: 'swarmgraph' },
};

describe('run-events helpers', () => {
  it('parseRunEvent accepts a valid typed event', () => {
    const parsed = parseRunEvent(baseEvent);

    expect(parsed.type).toBe('RUN_STARTED');
    expect(parsed.schema_version).toBe(2);
    expect(parsed.data).toEqual({ workflow_id: 'wf-1', runtime: 'swarmgraph' });
  });

  it('parseRunEvent defaults schema_version and data for older traces', () => {
    const parsed = parseRunEvent({
      type: 'CUSTOM_EVENT',
      timestamp: '2026-05-23T00:00:00.000Z',
      run_id: 'run-1',
      sequence: 2,
    });

    expect(parsed.schema_version).toBe(1);
    expect(parsed.data).toEqual({});
  });

  it('parseRunEvent rejects non-object input', () => {
    expect(() => parseRunEvent(null)).toThrow('Invalid event: not an object');
    expect(() => parseRunEvent('not-json')).toThrow('Invalid event: not an object');
  });

  it('parseRunEvent validates required base fields', () => {
    expect(() => parseRunEvent({ ...baseEvent, type: 123 })).toThrow('missing or invalid type');
    expect(() => parseRunEvent({ ...baseEvent, run_id: 123 })).toThrow('missing or invalid run_id');
    expect(() => parseRunEvent({ ...baseEvent, timestamp: 123 })).toThrow('missing or invalid timestamp');
    expect(() => parseRunEvent({ ...baseEvent, sequence: '1' })).toThrow('missing or invalid sequence');
  });

  it('isEventOfType narrows by event type', () => {
    const event = parseRunEvent(baseEvent);

    expect(isEventOfType(event, 'RUN_STARTED')).toBe(true);
    expect(isEventOfType(event, 'RUN_COMPLETED')).toBe(false);
  });

  it('isKnownEvent distinguishes known and custom events', () => {
    const known = parseRunEvent(baseEvent);
    const unknown = parseRunEvent({ ...baseEvent, type: 'CUSTOM_EVENT' });

    expect(isKnownEvent(known)).toBe(true);
    expect(isKnownEvent(unknown)).toBe(false);
  });

  it('assertNeverEvent throws the unhandled event type', () => {
    expect(() => assertNeverEvent({ ...baseEvent, type: 'SURPRISE' } as never)).toThrow(
      'Unhandled event type: SURPRISE'
    );
  });

  it('index exports run event helpers', () => {
    expect(protocol.parseRunEvent).toBe(parseRunEvent);
    expect(protocol.isKnownEvent).toBe(isKnownEvent);
  });

  it('KnownRunEvent guards include RAW and policy warnings', () => {
    const raw = parseRunEvent({ ...baseEvent, type: 'RAW' }) as TypedRunEvent;
    const warning = parseRunEvent({ ...baseEvent, type: 'POLICY_BYPASS_WARNING' }) as TypedRunEvent;

    expect(isKnownEvent(raw)).toBe(true);
    expect(isKnownEvent(warning)).toBe(true);
  });
});
