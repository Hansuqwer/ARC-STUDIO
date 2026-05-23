/**
 * Tests for PolicyBypassWarning event types (Phase 22.1).
 */
import {
  PolicyBypassReason,
  PolicyBypassWarning,
  TypedRunEvent,
  isEventOfType,
} from './run-events';

describe('PolicyBypassWarning', () => {
  it('type guard narrows to PolicyBypassWarning', () => {
    // Create a PolicyBypassWarning event
    const event: TypedRunEvent = {
      schema_version: 2,
      type: 'POLICY_BYPASS_WARNING',
      timestamp: '2026-05-23T08:00:00Z',
      run_id: 'run_123',
      sequence: 1,
      data: {
        policy_id: 'trust_gate',
        bypass_reason: 'unknown_provider_plugin',
        surface: 'provider_call',
        surface_identifier: 'custom_provider.execute',
        suggested_remediation: 'Instrument the custom provider with enforcement hooks',
      },
    };

    // Type guard should narrow the type
    if (isEventOfType(event, 'POLICY_BYPASS_WARNING')) {
      // TypeScript should know event is PolicyBypassWarning here
      expect(event.data.policy_id).toBe('trust_gate');
      expect(event.data.bypass_reason).toBe('unknown_provider_plugin');
      expect(event.data.surface).toBe('provider_call');
      expect(event.data.surface_identifier).toBe('custom_provider.execute');
      expect(event.data.suggested_remediation).toBe('Instrument the custom provider with enforcement hooks');
    } else {
      fail('Type guard should have narrowed to PolicyBypassWarning');
    }
  });

  it('JSON serialization round-trip preserves all fields', () => {
    const original: PolicyBypassWarning = {
      schema_version: 2,
      type: 'POLICY_BYPASS_WARNING',
      timestamp: '2026-05-23T08:00:00Z',
      run_id: 'run_456',
      sequence: 5,
      data: {
        policy_id: 'network_gate',
        bypass_reason: 'custom_http_client',
        surface: 'network_access',
        surface_identifier: 'requests.Session.custom',
        suggested_remediation: 'Use the instrumented HTTP client wrapper',
        parent_run_id: 'run_parent_123',
      },
    };

    // Serialize to JSON
    const json = JSON.stringify(original);
    
    // Deserialize back
    const restored = JSON.parse(json) as PolicyBypassWarning;

    // Verify all fields match
    expect(restored.schema_version).toBe(original.schema_version);
    expect(restored.type).toBe(original.type);
    expect(restored.timestamp).toBe(original.timestamp);
    expect(restored.run_id).toBe(original.run_id);
    expect(restored.sequence).toBe(original.sequence);
    expect(restored.data.policy_id).toBe(original.data.policy_id);
    expect(restored.data.bypass_reason).toBe(original.data.bypass_reason);
    expect(restored.data.surface).toBe(original.data.surface);
    expect(restored.data.surface_identifier).toBe(original.data.surface_identifier);
    expect(restored.data.suggested_remediation).toBe(original.data.suggested_remediation);
    expect(restored.data.parent_run_id).toBe(original.data.parent_run_id);
  });

  it('all PolicyBypassReason values are valid', () => {
    // Verify all 5 bypass reason values can be used
    const reasons: PolicyBypassReason[] = [
      'unknown_provider_plugin',
      'custom_http_client',
      'custom_subprocess_runner',
      'uninstrumented_tool',
      'upstream_bypassed_boundary',
    ];

    // Create a warning for each reason to verify they're all valid
    reasons.forEach((reason) => {
      const warning: PolicyBypassWarning = {
        schema_version: 2,
        type: 'POLICY_BYPASS_WARNING',
        timestamp: '2026-05-23T08:00:00Z',
        run_id: 'run_test',
        sequence: 1,
        data: {
          policy_id: 'test_policy',
          bypass_reason: reason,
          surface: 'test_surface',
          surface_identifier: 'test.identifier',
          suggested_remediation: 'Test remediation',
        },
      };

      expect(warning.data.bypass_reason).toBe(reason);
    });

    // Verify we have exactly 5 reasons
    expect(reasons).toHaveLength(5);
  });
});
