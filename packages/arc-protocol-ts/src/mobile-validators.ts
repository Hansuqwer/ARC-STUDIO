/**
 * ARC Mobile Runtime — TypeScript runtime validators.
 *
 * Validates unknown objects against the mobile protocol types.
 * No external dependencies — pure TypeScript field checks.
 * These are deliberately strict: unknown/missing required fields throw ArcValidationError.
 */

import type {
  MobileCapability,
  MobileRuntimeManifest,
  MobileActionPlan,
  MobileRuntimeEvent,
  MobilePolicyDecision,
} from './mobile-runtime';

export class ArcValidationError extends Error {
  constructor(
    message: string,
    public readonly field?: string,
    public readonly value?: unknown,
  ) {
    super(message);
    this.name = 'ArcValidationError';
  }
}

function requireString(o: Record<string, unknown>, key: string): string {
  const v = o[key];
  if (typeof v !== 'string' || v.length === 0)
    throw new ArcValidationError(`Expected non-empty string for '${key}'`, key, v);
  return v;
}

function requireBoolean(o: Record<string, unknown>, key: string): boolean {
  const v = o[key];
  if (typeof v !== 'boolean')
    throw new ArcValidationError(`Expected boolean for '${key}'`, key, v);
  return v;
}

function requireArray(o: Record<string, unknown>, key: string): unknown[] {
  const v = o[key];
  if (!Array.isArray(v))
    throw new ArcValidationError(`Expected array for '${key}'`, key, v);
  return v;
}

function asRecord(obj: unknown, context: string): Record<string, unknown> {
  if (typeof obj !== 'object' || obj === null)
    throw new ArcValidationError(`Expected object at '${context}'`, context, obj);
  return obj as Record<string, unknown>;
}

const VALID_SENSITIVITY = ['none', 'low', 'medium', 'high', 'critical'] as const;
const VALID_APPROVAL = ['none', 'recommended', 'required', 'blocking'] as const;
const VALID_PLATFORMS = ['ios', 'android', 'flutter', 'expo', 'react_native', 'web', 'all'] as const;

/** Validate an unknown object as MobileCapability. Throws ArcValidationError on failure. */
export function validateMobileCapability(obj: unknown): MobileCapability {
  const o = asRecord(obj, 'MobileCapability');
  requireString(o, 'id');
  requireString(o, 'name');
  requireBoolean(o, 'reads');
  requireBoolean(o, 'writes');
  requireBoolean(o, 'network');
  requireBoolean(o, 'background');
  requireBoolean(o, 'replayable');
  requireBoolean(o, 'auditable');
  requireBoolean(o, 'mcp_exposable');
  requireBoolean(o, 'simulator_supported');
  requireBoolean(o, 'test_fixture_supported');
  requireBoolean(o, 'requires_trust');
  requireBoolean(o, 'requires_hitl');
  requireBoolean(o, 'paid');
  requireArray(o, 'platforms');
  requireArray(o, 'required_permissions');
  if (!VALID_SENSITIVITY.includes(o['data_sensitivity'] as typeof VALID_SENSITIVITY[number]))
    throw new ArcValidationError(`Invalid data_sensitivity: '${o['data_sensitivity']}'`, 'data_sensitivity');
  if (!VALID_APPROVAL.includes(o['approval_mode'] as typeof VALID_APPROVAL[number]))
    throw new ArcValidationError(`Invalid approval_mode: '${o['approval_mode']}'`, 'approval_mode');
  return o as unknown as MobileCapability;
}

/** Validate an unknown object as MobileRuntimeManifest. Throws ArcValidationError on failure. */
export function validateMobileManifest(obj: unknown): MobileRuntimeManifest {
  const o = asRecord(obj, 'MobileRuntimeManifest');
  requireString(o, 'id');
  requireString(o, 'name');
  requireBoolean(o, 'simulator_mode');
  requireBoolean(o, 'background_execution');
  requireBoolean(o, 'network_by_default');
  requireArray(o, 'capabilities');
  requireArray(o, 'platforms');
  if (o['background_execution'] === true)
    throw new ArcValidationError('background_execution must be false in simulator mode', 'background_execution');
  if (o['network_by_default'] === true)
    throw new ArcValidationError('network_by_default must be false in simulator mode', 'network_by_default');
  return o as unknown as MobileRuntimeManifest;
}

/** Validate an unknown object as MobileActionPlan. Throws ArcValidationError on failure. */
export function validateActionPlan(obj: unknown): MobileActionPlan {
  const o = asRecord(obj, 'MobileActionPlan');
  requireString(o, 'plan_id');
  requireBoolean(o, 'requires_network');
  requireBoolean(o, 'requires_background');
  requireArray(o, 'steps');
  if (o['requires_network'] === true)
    throw new ArcValidationError('requires_network must be false', 'requires_network');
  if (o['requires_background'] === true)
    throw new ArcValidationError('requires_background must be false', 'requires_background');
  return o as unknown as MobileActionPlan;
}

/** Validate an unknown object as MobileRuntimeEvent. Throws ArcValidationError on failure. */
export function validateMobileEvent(obj: unknown): MobileRuntimeEvent {
  const o = asRecord(obj, 'MobileRuntimeEvent');
  requireString(o, 'event_id');
  requireString(o, 'plan_id');
  requireString(o, 'timestamp');
  requireString(o, 'payload_hash');
  requireString(o, 'event_hash');
  requireBoolean(o, 'allowed');
  requireBoolean(o, 'mock');
  return o as unknown as MobileRuntimeEvent;
}

/** Validate an unknown object as MobilePolicyDecision. Throws ArcValidationError on failure. */
export function validatePolicyDecision(obj: unknown): MobilePolicyDecision {
  const o = asRecord(obj, 'MobilePolicyDecision');
  requireBoolean(o, 'allowed');
  requireBoolean(o, 'approval_required');
  requireBoolean(o, 'mcp_exposable');
  requireString(o, 'reason');
  requireArray(o, 'denied_rules');
  requireArray(o, 'required_approvals');
  return o as unknown as MobilePolicyDecision;
}

export { VALID_SENSITIVITY, VALID_APPROVAL, VALID_PLATFORMS };
