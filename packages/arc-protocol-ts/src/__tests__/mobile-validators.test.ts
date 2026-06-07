/**
 * Tests for the mobile runtime validators (ArcValidationError + 5 validators).
 * Covers happy paths, type failures (string/boolean/array/object), enum checks,
 * and the simulator-safety constraints (no background / no network by default).
 */
import {
  ArcValidationError,
  validateMobileCapability,
  validateMobileManifest,
  validateActionPlan,
  validateMobileEvent,
  validatePolicyDecision,
  VALID_SENSITIVITY,
  VALID_APPROVAL,
  VALID_PLATFORMS,
} from '../mobile-validators';

const validCapability = {
  id: 'app.test.read',
  name: 'Test Read',
  reads: true,
  writes: false,
  network: false,
  background: false,
  replayable: true,
  auditable: true,
  mcp_exposable: true,
  simulator_supported: true,
  test_fixture_supported: true,
  requires_trust: false,
  requires_hitl: false,
  paid: false,
  platforms: ['ios'],
  required_permissions: [],
  data_sensitivity: 'low',
  approval_mode: 'none',
};

const validManifest = {
  id: 'test.runtime',
  name: 'Test Runtime',
  simulator_mode: true,
  background_execution: false,
  network_by_default: false,
  capabilities: [],
  platforms: ['ios'],
};

const validPlan = {
  plan_id: 'plan-1',
  requires_network: false,
  requires_background: false,
  steps: [],
};

const validEvent = {
  event_id: 'e1',
  plan_id: 'plan-1',
  timestamp: '2026-01-01T00:00:00Z',
  payload_hash: 'abc',
  event_hash: 'def',
  allowed: true,
  mock: true,
};

const validDecision = {
  allowed: true,
  approval_required: false,
  mcp_exposable: true,
  reason: 'ok',
  denied_rules: [],
  required_approvals: [],
};

describe('ArcValidationError', () => {
  it('carries message, field, value, and a stable name', () => {
    const e = new ArcValidationError('bad', 'id', 42);
    expect(e).toBeInstanceOf(Error);
    expect(e.name).toBe('ArcValidationError');
    expect(e.message).toBe('bad');
    expect(e.field).toBe('id');
    expect(e.value).toBe(42);
  });

  it('exposes the validation enums', () => {
    expect(VALID_SENSITIVITY).toContain('critical');
    expect(VALID_APPROVAL).toContain('blocking');
    expect(VALID_PLATFORMS).toContain('expo');
  });
});

describe('validateMobileCapability', () => {
  it('accepts a valid capability and returns it', () => {
    expect(validateMobileCapability(validCapability)).toBe(validCapability);
  });

  it('throws on a non-object', () => {
    expect(() => validateMobileCapability(null)).toThrow(ArcValidationError);
    expect(() => validateMobileCapability('x')).toThrow(/Expected object/);
  });

  it('throws on a missing/empty string field', () => {
    expect(() => validateMobileCapability({ ...validCapability, id: '' })).toThrow(/non-empty string for 'id'/);
  });

  it('throws on a non-boolean flag', () => {
    expect(() => validateMobileCapability({ ...validCapability, reads: 'yes' })).toThrow(/boolean for 'reads'/);
  });

  it('throws on a non-array field', () => {
    expect(() => validateMobileCapability({ ...validCapability, platforms: 'ios' })).toThrow(/array for 'platforms'/);
  });

  it('throws on an invalid data_sensitivity', () => {
    expect(() => validateMobileCapability({ ...validCapability, data_sensitivity: 'extreme' })).toThrow(
      /Invalid data_sensitivity/,
    );
  });

  it('throws on an invalid approval_mode', () => {
    expect(() => validateMobileCapability({ ...validCapability, approval_mode: 'maybe' })).toThrow(
      /Invalid approval_mode/,
    );
  });
});

describe('validateMobileManifest', () => {
  it('accepts a valid simulator manifest', () => {
    expect(validateMobileManifest(validManifest)).toBe(validManifest);
  });

  it('rejects background_execution=true (simulator safety)', () => {
    expect(() => validateMobileManifest({ ...validManifest, background_execution: true })).toThrow(
      /background_execution must be false/,
    );
  });

  it('rejects network_by_default=true (simulator safety)', () => {
    expect(() => validateMobileManifest({ ...validManifest, network_by_default: true })).toThrow(
      /network_by_default must be false/,
    );
  });

  it('throws on a missing capabilities array', () => {
    const { capabilities, ...rest } = validManifest;
    expect(() => validateMobileManifest(rest)).toThrow(/array for 'capabilities'/);
  });
});

describe('validateActionPlan', () => {
  it('accepts a valid plan', () => {
    expect(validateActionPlan(validPlan)).toBe(validPlan);
  });

  it('rejects requires_network=true', () => {
    expect(() => validateActionPlan({ ...validPlan, requires_network: true })).toThrow(
      /requires_network must be false/,
    );
  });

  it('rejects requires_background=true', () => {
    expect(() => validateActionPlan({ ...validPlan, requires_background: true })).toThrow(
      /requires_background must be false/,
    );
  });

  it('throws on a missing plan_id', () => {
    expect(() => validateActionPlan({ ...validPlan, plan_id: '' })).toThrow(/non-empty string for 'plan_id'/);
  });
});

describe('validateMobileEvent', () => {
  it('accepts a valid event', () => {
    expect(validateMobileEvent(validEvent)).toBe(validEvent);
  });

  it('throws on a missing hash field', () => {
    expect(() => validateMobileEvent({ ...validEvent, event_hash: '' })).toThrow(/non-empty string for 'event_hash'/);
  });

  it('throws on a non-boolean allowed', () => {
    expect(() => validateMobileEvent({ ...validEvent, allowed: 1 })).toThrow(/boolean for 'allowed'/);
  });
});

describe('validatePolicyDecision', () => {
  it('accepts a valid decision', () => {
    expect(validatePolicyDecision(validDecision)).toBe(validDecision);
  });

  it('throws on a non-boolean approval_required', () => {
    expect(() => validatePolicyDecision({ ...validDecision, approval_required: 'no' })).toThrow(
      /boolean for 'approval_required'/,
    );
  });

  it('throws on a non-array denied_rules', () => {
    expect(() => validatePolicyDecision({ ...validDecision, denied_rules: {} })).toThrow(/array for 'denied_rules'/);
  });

  it('throws on a missing reason', () => {
    expect(() => validatePolicyDecision({ ...validDecision, reason: '' })).toThrow(/non-empty string for 'reason'/);
  });
});
