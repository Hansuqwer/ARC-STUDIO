/**
 * Runtime capability v2 schema and v1 migration.
 * 
 * Mirrors python/src/agent_runtime_cockpit/protocol/runtime_capability.py
 */

import { RuntimeMode, fromLegacyRuntimeMode, isPaidMode } from './runtime-mode';
import { RuntimeCapabilities } from './arc-protocol-types';

export interface RuntimeCapabilityV2 {
  schema_version: 2;
  mode: RuntimeMode;
  profile_id: string;
  isolation_id: string;
  allow_paid_calls: boolean;
  cost_source_default: 'estimated' | 'measured';
  supports_cancellation: boolean;
  supports_streaming: boolean;
}

/**
 * Validate paid-call invariants for RuntimeCapability v2.
 * 
 * Rules:
 * - If allow_paid_calls=true, mode must be provider_backed
 * - If cost_source_default='measured', mode must be provider_backed
 * 
 * Throws Error if invariants are violated.
 */
export function validatePaidInvariants(capability: RuntimeCapabilityV2): void {
  if (capability.allow_paid_calls && capability.mode !== RuntimeMode.PROVIDER_BACKED) {
    throw new Error('allow_paid_calls=true requires mode=provider_backed');
  }
  if (capability.cost_source_default === 'measured' && capability.mode !== RuntimeMode.PROVIDER_BACKED) {
    throw new Error('measured cost source requires mode=provider_backed');
  }
}

/**
 * Migrate a v1 capability payload to canonical v2.
 * 
 * Idempotent for already-v2 payloads. Unknown v1 keys are preserved.
 * 
 * @param payload - Raw capability object (v1 or v2)
 * @returns Migrated v2 capability
 * @throws Error if schema_version is unsupported or validation fails
 */
export function migrateV1ToV2(payload: Record<string, unknown>): RuntimeCapabilityV2 {
  const schemaVersion = payload.schema_version;

  // Already v2: validate and return
  if (schemaVersion === 2) {
    const capability = payload as unknown as RuntimeCapabilityV2;
    validatePaidInvariants(capability);
    return capability;
  }

  // Not v1: unsupported
  if (schemaVersion !== 1) {
    throw new Error(`Unsupported runtime capability schema_version: ${schemaVersion}`);
  }

  // Migrate v1 → v2
  const v1 = payload as unknown as RuntimeCapabilities;
  const mode = fromLegacyRuntimeMode((payload.mode as string) || RuntimeMode.FAKE);
  const paid = isPaidMode(mode);

  const migrated: RuntimeCapabilityV2 = {
    schema_version: 2,
    mode,
    profile_id: String(payload.profile_id || payload.runtime_id || 'default'),
    isolation_id: String(payload.isolation_id || 'none'),
    allow_paid_calls: Boolean(payload.allow_paid_calls ?? paid),
    cost_source_default: String(payload.cost_source_default || (paid ? 'measured' : 'estimated')) as 'estimated' | 'measured',
    supports_cancellation: Boolean(payload.supports_cancellation ?? true),
    supports_streaming: Boolean(payload.supports_streaming ?? false),
  };

  validatePaidInvariants(migrated);
  return migrated;
}

/**
 * Normalize a capability payload to v2, auto-migrating if needed.
 * 
 * Convenience wrapper around migrateV1ToV2() for use in parsers.
 */
export function normalizeCapability(payload: Record<string, unknown>): RuntimeCapabilityV2 {
  return migrateV1ToV2(payload);
}
