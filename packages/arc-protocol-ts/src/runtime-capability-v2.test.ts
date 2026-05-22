/**
 * Tests for RuntimeCapability v2 schema and migration.
 */

import { describe, it, expect } from '@jest/globals';
import {
  RuntimeMode,
  fromLegacyRuntimeMode,
  isPaidMode,
} from './runtime-mode';
import {
  RuntimeCapabilityV2,
  migrateV1ToV2,
  validatePaidInvariants,
  normalizeCapability,
} from './runtime-capability-v2';
import { loadFixture } from './fixtures/loader';

describe('RuntimeMode', () => {
  describe('fromLegacyRuntimeMode', () => {
    it('accepts canonical values without warning', () => {
      expect(fromLegacyRuntimeMode('fake')).toBe(RuntimeMode.FAKE);
      expect(fromLegacyRuntimeMode('gated_local')).toBe(RuntimeMode.GATED_LOCAL);
      expect(fromLegacyRuntimeMode('provider_backed')).toBe(RuntimeMode.PROVIDER_BACKED);
    });

    it('maps legacy values with warning', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      expect(fromLegacyRuntimeMode('offline')).toBe(RuntimeMode.FAKE);
      expect(fromLegacyRuntimeMode('local')).toBe(RuntimeMode.GATED_LOCAL);
      expect(fromLegacyRuntimeMode('gated')).toBe(RuntimeMode.GATED_LOCAL);
      expect(fromLegacyRuntimeMode('live')).toBe(RuntimeMode.PROVIDER_BACKED);
      
      expect(consoleSpy).toHaveBeenCalledTimes(4);
      consoleSpy.mockRestore();
    });

    it('passes through RuntimeMode instances', () => {
      expect(fromLegacyRuntimeMode(RuntimeMode.FAKE)).toBe(RuntimeMode.FAKE);
      expect(fromLegacyRuntimeMode(RuntimeMode.GATED_LOCAL)).toBe(RuntimeMode.GATED_LOCAL);
    });

    it('throws on unknown values', () => {
      expect(() => fromLegacyRuntimeMode('unknown')).toThrow('Unknown runtime mode');
    });

    it('normalizes case and whitespace', () => {
      expect(fromLegacyRuntimeMode('  FAKE  ')).toBe(RuntimeMode.FAKE);
      expect(fromLegacyRuntimeMode('Gated_Local')).toBe(RuntimeMode.GATED_LOCAL);
    });
  });

  describe('isPaidMode', () => {
    it('returns true only for provider_backed', () => {
      expect(isPaidMode(RuntimeMode.FAKE)).toBe(false);
      expect(isPaidMode(RuntimeMode.GATED_LOCAL)).toBe(false);
      expect(isPaidMode(RuntimeMode.PROVIDER_BACKED)).toBe(true);
    });
  });
});

describe('RuntimeCapabilityV2', () => {
  describe('validatePaidInvariants', () => {
    it('accepts valid configurations', () => {
      const validCases: RuntimeCapabilityV2[] = [
        {
          schema_version: 2,
          mode: RuntimeMode.FAKE,
          profile_id: 'default',
          isolation_id: 'none',
          allow_paid_calls: false,
          cost_source_default: 'estimated',
          supports_cancellation: true,
          supports_streaming: false,
        },
        {
          schema_version: 2,
          mode: RuntimeMode.PROVIDER_BACKED,
          profile_id: 'prod',
          isolation_id: 'workspace-123',
          allow_paid_calls: true,
          cost_source_default: 'measured',
          supports_cancellation: true,
          supports_streaming: true,
        },
      ];

      validCases.forEach(cap => {
        expect(() => validatePaidInvariants(cap)).not.toThrow();
      });
    });

    it('rejects allow_paid_calls=true with non-provider_backed mode', () => {
      const invalid: RuntimeCapabilityV2 = {
        schema_version: 2,
        mode: RuntimeMode.FAKE,
        profile_id: 'default',
        isolation_id: 'none',
        allow_paid_calls: true,
        cost_source_default: 'estimated',
        supports_cancellation: true,
        supports_streaming: false,
      };

      expect(() => validatePaidInvariants(invalid)).toThrow(
        'allow_paid_calls=true requires mode=provider_backed'
      );
    });

    it('rejects measured cost source with non-provider_backed mode', () => {
      const invalid: RuntimeCapabilityV2 = {
        schema_version: 2,
        mode: RuntimeMode.GATED_LOCAL,
        profile_id: 'default',
        isolation_id: 'none',
        allow_paid_calls: false,
        cost_source_default: 'measured',
        supports_cancellation: true,
        supports_streaming: false,
      };

      expect(() => validatePaidInvariants(invalid)).toThrow(
        'measured cost source requires mode=provider_backed'
      );
    });
  });

  describe('migrateV1ToV2', () => {
    it('passes through v2 payloads unchanged', () => {
      const v2: RuntimeCapabilityV2 = {
        schema_version: 2,
        mode: RuntimeMode.GATED_LOCAL,
        profile_id: 'default',
        isolation_id: 'none',
        allow_paid_calls: false,
        cost_source_default: 'estimated',
        supports_cancellation: true,
        supports_streaming: false,
      };

      const result = migrateV1ToV2(v2 as unknown as Record<string, unknown>);
      expect(result).toEqual(v2);
    });

    it('migrates v1 to v2 with defaults', () => {
      const v1 = {
        schema_version: 1,
        support_level: 'stable',
        can_run: true,
      };

      const result = migrateV1ToV2(v1);
      expect(result.schema_version).toBe(2);
      expect(result.mode).toBe(RuntimeMode.FAKE);
      expect(result.profile_id).toBe('default');
      expect(result.isolation_id).toBe('none');
      expect(result.allow_paid_calls).toBe(false);
      expect(result.cost_source_default).toBe('estimated');
      expect(result.supports_cancellation).toBe(true);
      expect(result.supports_streaming).toBe(false);
    });

    it('infers allow_paid_calls from provider_backed mode', () => {
      const v1 = {
        schema_version: 1,
        mode: 'provider_backed',
      };

      const result = migrateV1ToV2(v1);
      expect(result.mode).toBe(RuntimeMode.PROVIDER_BACKED);
      expect(result.allow_paid_calls).toBe(true);
      expect(result.cost_source_default).toBe('measured');
    });

    it('maps runtime_id to profile_id', () => {
      const v1 = {
        schema_version: 1,
        runtime_id: 'swarmgraph',
      };

      const result = migrateV1ToV2(v1);
      expect(result.profile_id).toBe('swarmgraph');
    });

    it('throws on unsupported schema versions', () => {
      const unsupported = { schema_version: 99 };
      expect(() => migrateV1ToV2(unsupported)).toThrow(
        'Unsupported runtime capability schema_version: 99'
      );
    });

    it('validates paid invariants after migration', () => {
      const invalid = {
        schema_version: 1,
        mode: 'fake',
        allow_paid_calls: true,
      };

      expect(() => migrateV1ToV2(invalid)).toThrow(
        'allow_paid_calls=true requires mode=provider_backed'
      );
    });
  });

  describe('normalizeCapability', () => {
    it('is an alias for migrateV1ToV2', () => {
      const v1 = { schema_version: 1 };
      const result = normalizeCapability(v1);
      expect(result.schema_version).toBe(2);
    });
  });

  describe('fixture loading', () => {
    it('loads and validates v2-gated-local fixture', () => {
      const data = loadFixture('runtime-capabilities', 'v2-gated-local') as Record<string, unknown>;
      const capability = migrateV1ToV2(data);
      
      expect(capability.schema_version).toBe(2);
      expect(capability.mode).toBe(RuntimeMode.GATED_LOCAL);
      expect(capability.allow_paid_calls).toBe(false);
      expect(capability.cost_source_default).toBe('estimated');
    });

    it('loads and validates v2-provider-backed fixture', () => {
      const data = loadFixture('runtime-capabilities', 'v2-provider-backed') as Record<string, unknown>;
      const capability = migrateV1ToV2(data);
      
      expect(capability.schema_version).toBe(2);
      expect(capability.mode).toBe(RuntimeMode.PROVIDER_BACKED);
      expect(capability.allow_paid_calls).toBe(true);
      expect(capability.cost_source_default).toBe('measured');
    });
  });
});
