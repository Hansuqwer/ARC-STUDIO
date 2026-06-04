import * as fs from 'fs';
import * as path from 'path';
import { isMobileRuntimeEvent, type MobileRuntimeEvent, type MobilePolicyDecision } from '../mobile-events';
import { isMobileTrace, type MobileTrace } from '../mobile-trace';

const TRACE = path.resolve(__dirname, '../../../../runtimes/mobile/fixtures/traces/echo.simulated.jsonl');

describe('mobile events protocol mirror', () => {
  it('loads golden JSONL trace events', () => {
    const events = fs.readFileSync(TRACE, 'utf8').trim().split('\n').map((line) => JSON.parse(line) as MobileRuntimeEvent);
    expect(events).toHaveLength(2);
    expect(events.every(isMobileRuntimeEvent)).toBe(true);
    expect(events.every((event) => event.mock)).toBe(true);
  });

  it('models mobile trace and policy decisions', () => {
    const trace: MobileTrace = { schema_version: 1, plan_id: 'p', events: [], trace_hash: '0'.repeat(64) };
    const decision: MobilePolicyDecision = {
      allowed: false,
      approval_required: false,
      capability_id: 'unknown',
      reason: 'unknown capability',
      denied_rules: ['unknown_capability'],
      required_approvals: [],
      mcp_exposable: false,
    };
    expect(isMobileTrace(trace)).toBe(true);
    expect(decision.allowed).toBe(false);
  });
});
