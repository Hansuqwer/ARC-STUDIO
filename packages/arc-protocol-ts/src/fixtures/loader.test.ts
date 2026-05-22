/**
 * Cross-language fixture validation tests.
 * 
 * Tests that JSON fixtures in protocol/fixtures/ are valid according to
 * TypeScript types and can round-trip through serialization.
 */

import { describe, it, expect } from '@jest/globals';
import {
  ArcEnvelope,
  RunEvent,
  validateEnvelope,
  parseEvent,
} from '../arc-protocol-types';
import {
  loadFixture,
  loadAndValidate,
  validateRoundTrip,
  listFixtures,
  listCategories,
} from './loader';

// Type validators
function validateArcEnvelope(data: unknown): ArcEnvelope {
  if (!validateEnvelope(data)) {
    throw new Error('Invalid ArcEnvelope');
  }
  return data as ArcEnvelope;
}

function validateRunEvent(data: unknown): RunEvent {
  if (typeof data !== 'object' || data === null) {
    throw new Error('Invalid RunEvent: not an object');
  }
  const event = data as Record<string, unknown>;
  if (typeof event.type !== 'string') {
    throw new Error('Invalid RunEvent: missing type');
  }
  if (typeof event.run_id !== 'string') {
    throw new Error('Invalid RunEvent: missing run_id');
  }
  return data as RunEvent;
}

describe('FixtureLoader', () => {
  describe('listCategories', () => {
    it('discovers fixture categories', () => {
      const categories = listCategories();
      expect(categories).toContain('arc-envelope');
      expect(categories).toContain('run-event');
      expect(categories).toContain('runtime-capabilities');
    });
  });

  describe('listFixtures', () => {
    it('discovers fixtures within a category', () => {
      const fixtures = listFixtures('arc-envelope');
      expect(fixtures).toContain('success');
      expect(fixtures).toContain('error-run-failed');
    });
  });

  describe('loadFixture', () => {
    it('loads a fixture as raw JSON', () => {
      const data = loadFixture('arc-envelope', 'success') as Record<string, unknown>;
      expect(data.ok).toBe(true);
      expect(data.version).toBe('1.0');
    });

    it('throws when fixture not found', () => {
      expect(() => {
        loadFixture('arc-envelope', 'nonexistent');
      }).toThrow('Fixture not found');
    });
  });
});

describe('ArcEnvelopeFixtures', () => {
  it('validates success envelope fixture', () => {
    const envelope = loadAndValidate('arc-envelope', 'success', validateArcEnvelope);
    expect(envelope.ok).toBe(true);
    expect(envelope.error).toBeNull();
    expect(envelope.data).not.toBeNull();
    expect(envelope.meta.adapter).toBe('swarmgraph');
  });

  it('validates error envelope fixture', () => {
    const envelope = loadAndValidate('arc-envelope', 'error-run-failed', validateArcEnvelope);
    expect(envelope.ok).toBe(false);
    expect(envelope.data).toBeNull();
    expect(envelope.error).not.toBeNull();
    expect(envelope.error?.code).toBe('RUN_FAILED');
  });

  it('validates workspace not found error fixture', () => {
    const envelope = loadAndValidate('arc-envelope', 'error-workspace-not-found', validateArcEnvelope);
    expect(envelope.ok).toBe(false);
    expect(envelope.error?.code).toBe('WORKSPACE_NOT_FOUND');
  });

  it('round-trips success envelope through serialization', () => {
    const [original, serialized] = validateRoundTrip(
      'arc-envelope',
      'success',
      validateArcEnvelope
    );
    const orig = original as Record<string, unknown>;
    const ser = serialized as Record<string, unknown>;
    
    // Core fields must match
    expect(orig.ok).toBe(ser.ok);
    expect(orig.version).toBe(ser.version);
    
    // Meta fields must be present
    expect(ser.meta).toBeDefined();
    const origMeta = orig.meta as Record<string, unknown>;
    const serMeta = ser.meta as Record<string, unknown>;
    expect(serMeta.adapter).toBe(origMeta.adapter);
  });
});

describe('RunEventFixtures', () => {
  it('validates RUN_STARTED event fixture', () => {
    const event = loadAndValidate('run-event', 'run-started', validateRunEvent);
    expect(event.type).toBe('RUN_STARTED');
    expect(event.schema_version).toBe(2);
    expect(event.data.workflow_id).toBe('workflow-xyz789');
  });

  it('validates RUN_COMPLETED event fixture', () => {
    const event = loadAndValidate('run-event', 'run-completed', validateRunEvent);
    expect(event.type).toBe('RUN_COMPLETED');
    expect(event.schema_version).toBe(2);
    expect(event.data.duration_ms).toBeDefined();
  });

  it('validates RUN_FAILED event fixture', () => {
    const event = loadAndValidate('run-event', 'run-failed', validateRunEvent);
    expect(event.type).toBe('RUN_FAILED');
    expect(event.schema_version).toBe(2);
    expect(event.data.error).toBeDefined();
  });

  it('validates RUN_CANCELLED event fixture', () => {
    const event = loadAndValidate('run-event', 'run-cancelled', validateRunEvent);
    expect(event.type).toBe('RUN_CANCELLED');
    expect(event.schema_version).toBe(2);
    expect(event.data.cancel_reason).toBe('user_requested');
  });

  it('round-trips RUN_COMPLETED event through serialization', () => {
    const [original, serialized] = validateRoundTrip(
      'run-event',
      'run-completed',
      validateRunEvent
    );
    const orig = original as Record<string, unknown>;
    const ser = serialized as Record<string, unknown>;
    
    expect(orig.type).toBe(ser.type);
    expect(orig.schema_version).toBe(ser.schema_version);
    expect(orig.run_id).toBe(ser.run_id);
  });

  it('parses events with parseEvent helper', () => {
    const data = loadFixture('run-event', 'run-completed');
    const event = parseEvent(JSON.stringify(data));
    expect(event.type).toBe('RUN_COMPLETED');
    expect(event.schema_version).toBe(2);
  });
});

describe('CrossLanguageConsistency', () => {
  it('loads all fixtures in all categories as JSON', () => {
    const categories = listCategories();
    for (const category of categories) {
      const fixtures = listFixtures(category);
      for (const fixtureName of fixtures) {
        // Should not throw
        const data = loadFixture(category, fixtureName);
        expect(typeof data).toBe('object');
        expect(data).not.toBeNull();
      }
    }
  });

  it('validates all RunEvent fixtures use schema_version 2', () => {
    const fixtures = listFixtures('run-event');
    for (const fixtureName of fixtures) {
      const event = loadAndValidate('run-event', fixtureName, validateRunEvent);
      expect(event.schema_version).toBe(2);
    }
  });

  it('validates all ArcEnvelope fixtures use version 1.0', () => {
    const fixtures = listFixtures('arc-envelope');
    for (const fixtureName of fixtures) {
      const envelope = loadAndValidate('arc-envelope', fixtureName, validateArcEnvelope);
      expect(envelope.version).toBe('1.0');
    }
  });
});

const CANONICAL_ERROR_CODES = [
  'WORKSPACE_NOT_FOUND',
  'NO_RUNTIME_DETECTED',
  'ADAPTER_ERROR',
  'ADAPTER_NOT_SUPPORTED',
  'SCHEMA_EXPORT_FAILED',
  'WORKFLOW_EXPORT_FAILED',
  'RUN_FAILED',
  'RUN_NOT_FOUND',
  'CONTEXT_PROVIDER_ERROR',
  'CONFORMANCE_FAILED',
  'INVALID_INPUT',
  'INTERNAL_ERROR',
  'TIMEOUT',
  'NOT_IMPLEMENTED',
  'PERMISSION_DENIED',
  'UNKNOWN',
] as const;

function kebabToUpperSnake(value: string): string {
  return value.replace(/-/g, '_').toUpperCase();
}

describe('ErrorCodeFixtures', () => {
  it('discovers ADR-023 error-code fixtures', () => {
    expect(listFixtures('error-codes').length).toBeGreaterThanOrEqual(5);
  });

  it('validates every error-code fixture shape and canonical code', () => {
    for (const fixtureName of listFixtures('error-codes')) {
      const data = loadFixture('error-codes', fixtureName) as Record<string, unknown>;
      expect(typeof data.code).toBe('string');
      expect(CANONICAL_ERROR_CODES).toContain(data.code as typeof CANONICAL_ERROR_CODES[number]);
      expect(typeof data.message).toBe('string');
      expect(data.message).not.toBe('');
      if (data.details !== undefined) {
        expect(typeof data.details).toBe('object');
        expect(data.details).not.toBeNull();
      }
    }
  });

  it('round-trips fixture filename kebab-case to UPPER_SNAKE_CASE code', () => {
    for (const fixtureName of listFixtures('error-codes')) {
      const data = loadFixture('error-codes', fixtureName) as Record<string, unknown>;
      expect(data.code).toBe(kebabToUpperSnake(fixtureName));
    }
  });

  it('round-trips every error-code fixture through JSON serialization', () => {
    for (const fixtureName of listFixtures('error-codes')) {
      const data = loadFixture('error-codes', fixtureName);
      expect(JSON.parse(JSON.stringify(data))).toEqual(data);
    }
  });
});
