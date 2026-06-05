import { describe, expect, it } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'path';

import * as protocol from './index';
import {
  assertNeverEvent,
  isEventOfType,
  isKnownEvent,
  KNOWN_RUN_EVENT_TYPES,
  parseRunEvent,
  TypedRunEvent,
} from './run-events';

const intentionallyUntypedCanonicalTypes = [
  'AGENT_START',
  'AGENT_END',
  'TOOL_CALL_ARGS',
  'TOOL_CALL_END',
  'TOOL_END',
  'HANDOFF',
  'NODE_UPDATE',
  'MESSAGE_CHUNK',
  'TEXT_MESSAGE_START',
  'TEXT_MESSAGE_CONTENT',
  'TEXT_MESSAGE_END',
  'TEXT_MESSAGE_CHUNK',
  'STATE_SNAPSHOT',
  'CONTRACT_PROPOSED',
  'CONTRACT_ACCEPTED',
  'CONTRACT_FULFILLED',
  'CONTRACT_VIOLATED',
  'RECEIPT_GENERATED',
  'FAILURE_AUTOPSY_GENERATED',
  'EVIDENCE_REF_CREATED',
  'BATTLE_STARTED',
  'BATTLE_CANDIDATE_READY',
  'BATTLE_VOTE_COMMITTED',
  'BATTLE_VOTE_REVEALED',
  'BATTLE_CONSENSUS_REACHED',
  'BATTLE_HITL_REQUIRED',
  'BATTLE_COMPLETED',
  'CONSENSUS_DIFFERENTIATOR',
  'CONSENSUS_EVAL',
  'CONSENSUS_EVAL_RUN',
  'CUSTOM',
] as const;

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

  it('isKnownEvent returns true for quota_warning', () => {
    const event = parseRunEvent({ ...baseEvent, type: 'QUOTA_WARNING',
      data: { dimension: 'session', usage_pct: 0.85, limit: 10.0, current: 8.5 } });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('KNOWN_RUN_EVENT_TYPES includes QUOTA_WARNING', () => {
    expect(KNOWN_RUN_EVENT_TYPES).toContain('QUOTA_WARNING');
  });

  it('exports the single known event type source used by guards', () => {
    expect(KNOWN_RUN_EVENT_TYPES).toContain('RUN_STARTED');
    expect(KNOWN_RUN_EVENT_TYPES).toContain('POLICY_BYPASS_WARNING');
    expect(KNOWN_RUN_EVENT_TYPES).toContain('RAW');
    expect(new Set(KNOWN_RUN_EVENT_TYPES).size).toBe(KNOWN_RUN_EVENT_TYPES.length);
  });

  it('accounts for every canonical Python registry event as typed or intentionally untyped', () => {
    const registryPath = path.resolve(__dirname, '../../../protocol/fixtures/run-event-registry.json');
    const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8')) as {
      eventTypes: Array<{ type: string }>;
    };
    const canonicalTypes = registry.eventTypes.map((entry) => entry.type).sort();
    const accountedTypes = [
      ...KNOWN_RUN_EVENT_TYPES,
      ...intentionallyUntypedCanonicalTypes,
    ].sort();

    expect(accountedTypes).toEqual(canonicalTypes);
  });

  it('isKnownEvent recognizes QUOTA_WARNING', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'QUOTA_WARNING',
      data: { dimension: 'session', usage_pct: 85.0, limit: 10.0, current: 8.5 },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('KNOWN_RUN_EVENT_TYPES includes QUOTA_WARNING', () => {
    expect(KNOWN_RUN_EVENT_TYPES).toContain('QUOTA_WARNING');
  });

  it('parseRunEvent recognizes CONTEXT_COMPACTED', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'CONTEXT_COMPACTED',
      data: { tokens_before: 170000, tokens_after: 120000, messages_evicted_count: 4, evicted_handles: [] },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(event.type).toBe('CONTEXT_COMPACTED');
  });

  it('CONTEXT_COMPACTED extra fields are ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'CONTEXT_COMPACTED',
      data: { tokens_before: 1, tokens_after: 2, messages_evicted_count: 1, future_field: 'ignored' },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('parseRunEvent recognizes TOOL_OUTPUT_VIRTUALIZED', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'TOOL_OUTPUT_VIRTUALIZED',
      data: { tool_name: 'bash', original_size_bytes: 9000, handle_uri: 'arc://output/sha256/abc', estimated_tokens_saved: 2200 },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(event.type).toBe('TOOL_OUTPUT_VIRTUALIZED');
  });

  it('TOOL_OUTPUT_VIRTUALIZED extra fields are ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'TOOL_OUTPUT_VIRTUALIZED',
      data: { tool_name: 'x', original_size_bytes: 1, handle_uri: 'arc://output/sha256/ff', estimated_tokens_saved: 1, future_field: 42 },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('parseRunEvent recognizes MODEL_CHANGED', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'MODEL_CHANGED',
      data: { previous_model: 'gpt-4o', current_model: 'kimi-k2.6', capabilities_added: ['vision'], capabilities_removed: [] },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(event.type).toBe('MODEL_CHANGED');
  });

  it('MODEL_CHANGED extra fields are ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'MODEL_CHANGED',
      data: { previous_model: 'a', current_model: 'b', future_field: 'ignored' },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('parseRunEvent recognizes PRICING_FEED_REFRESHED', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'PRICING_FEED_REFRESHED',
      data: { feed_url: 'https://openrouter.ai/api/v1/models', feed_hash: 'abc123', rows_seen: 91, source: 'openrouter' },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(KNOWN_RUN_EVENT_TYPES).toContain('PRICING_FEED_REFRESHED');
  });

  it('PRICING_FEED_REFRESHED extra fields ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'PRICING_FEED_REFRESHED',
      data: { feed_url: 'x', feed_hash: 'y', rows_seen: 1, source: 'cache', future: 1 },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('parseRunEvent recognizes BUDGET_BROKER_SYNC', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'BUDGET_BROKER_SYNC',
      data: { scope: 'SESSION', amount_usd: 1.5, local_approved: true, remote_approved: true, fell_back: false },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(KNOWN_RUN_EVENT_TYPES).toContain('BUDGET_BROKER_SYNC');
  });

  it('BUDGET_BROKER_SYNC extra fields ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'BUDGET_BROKER_SYNC',
      data: { scope: 'RUN', amount_usd: 1, local_approved: true, remote_approved: false, fell_back: true, future: 1 },
    });
    expect(isKnownEvent(event)).toBe(true);
  });

  it('parseRunEvent recognizes OBSERVABILITY_EXPORT_STARTED', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'OBSERVABILITY_EXPORT_STARTED',
      data: { destination: 'https://otlp.example', protocol: 'otlp', span_count: 3 },
    });
    expect(isKnownEvent(event)).toBe(true);
    expect(KNOWN_RUN_EVENT_TYPES).toContain('OBSERVABILITY_EXPORT_STARTED');
  });

  it('OBSERVABILITY_EXPORT_STARTED extra fields ignored (forward-compat)', () => {
    const event = parseRunEvent({
      ...baseEvent,
      type: 'OBSERVABILITY_EXPORT_STARTED',
      data: { destination: 'x', protocol: 'langfuse', span_count: 1, future: 1 },
    });
    expect(isKnownEvent(event)).toBe(true);
  });
});
