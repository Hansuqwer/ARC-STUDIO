import * as fs from 'fs';
import * as path from 'path';
import {
  isMobileRuntimeEvent,
  isMobilePolicyDecision,
  type MobileRuntimeEvent,
  type MobilePolicyDecision,
} from '../mobile-events';
import { isMobileTrace, type MobileTrace } from '../mobile-trace';

const TRACE = path.resolve(
  __dirname,
  '../../../../runtimes/mobile/fixtures/traces/echo.simulated.jsonl',
);

describe('mobile events protocol mirror', () => {
  it('loads golden JSONL trace events', () => {
    const lines = fs
      .readFileSync(TRACE, 'utf8')
      .trim()
      .split('\n')
      .map((line) => JSON.parse(line) as MobileRuntimeEvent);
    expect(lines.length).toBeGreaterThanOrEqual(1);
    expect(lines.every((e) => typeof e.event_hash === 'string')).toBe(true);
    expect(lines.every((e) => e.mock === true)).toBe(true);
  });

  it('isMobileRuntimeEvent accepts event with prev_event_hash', () => {
    const event: MobileRuntimeEvent = {
      schema_version: 1,
      event_id: 'evt-001',
      event_type: 'mobile.step.simulated',
      plan_id: 'p1',
      timestamp: '2026-01-01T00:00:00Z',
      sequence: 0,
      allowed: true,
      mock: true,
      payload_hash: 'a'.repeat(64),
      prev_event_hash: '0'.repeat(64),
      event_hash: 'b'.repeat(64),
      metadata: {},
    };
    expect(isMobileRuntimeEvent(event)).toBe(true);
  });

  it('isMobileRuntimeEvent rejects object missing prev_event_hash', () => {
    const bad = {
      event_hash: 'x'.repeat(64),
      payload_hash: 'y'.repeat(64),
      // prev_event_hash missing
    };
    expect(isMobileRuntimeEvent(bad)).toBe(false);
  });

  it('isMobilePolicyDecision accepts valid decision', () => {
    const decision: MobilePolicyDecision = {
      allowed: false,
      approval_required: false,
      reason: 'denied',
      denied_rules: ['test'],
      required_approvals: [],
      mcp_exposable: false,
    };
    expect(isMobilePolicyDecision(decision)).toBe(true);
  });

  it('mobile trace interface is valid', () => {
    const trace: MobileTrace = {
      schema_version: 1,
      plan_id: 'p',
      events: [],
      trace_hash: '0'.repeat(64),
    };
    expect(isMobileTrace(trace)).toBe(true);
  });
});
