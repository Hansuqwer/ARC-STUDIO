/**
 * Tests for audit event schema types.
 */
import {
  AuditEventType,
  AuditEventSeverity,
  AuditEvent,
  AuditChainLink,
  AuditChainManifest,
} from './audit-events';

describe('AuditEventType', () => {
  it('should have all expected values', () => {
    const expected: AuditEventType[] = [
      'AUDIT_CHAIN_STARTED',
      'AUDIT_CHAIN_LINK_ADDED',
      'AUDIT_CHAIN_SEALED',
      'AUDIT_CHAIN_VERIFIED',
      'AUDIT_CHAIN_FAILED',
      'AUDIT_KEY_ROTATED',
      'AUDIT_EXPORTED',
    ];
    // TypeScript compile-time check — these are literal types, not enums
    const values: readonly AuditEventType[] = expected;
    expect(values).toHaveLength(7);
  });
});

describe('AuditEventSeverity', () => {
  it('should have info, warning, critical', () => {
    const severities: AuditEventSeverity[] = ['info', 'warning', 'critical'];
    expect(severities).toHaveLength(3);
  });
});

describe('AuditEvent interface shape', () => {
  it('should have required fields', () => {
    const event: AuditEvent = {
      runId: 'run-sg-abc123',
      eventType: 'AUDIT_CHAIN_STARTED',
      timestamp: '2026-05-22T10:00:00.000Z',
      sequence: 0,
      severity: 'info',
      producer: 'arc-backend',
      data: { workflow: 'wf-swarmgraph-fixture' },
    };
    expect(event.runId).toBe('run-sg-abc123');
    expect(event.eventType).toBe('AUDIT_CHAIN_STARTED');
    expect(event.sequence).toBe(0);
    expect(event.severity).toBe('info');
  });
});

describe('AuditChainLink interface shape', () => {
  it('should link events with hashes', () => {
    const event: AuditEvent = {
      runId: 'run-sg-abc123',
      eventType: 'AUDIT_CHAIN_LINK_ADDED',
      timestamp: '2026-05-22T10:00:01.000Z',
      sequence: 1,
      severity: 'info',
      producer: 'arc-backend',
      data: {},
    };
    const link: AuditChainLink = {
      chainId: 'chain-abc',
      previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
      hash: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
      event,
      sealedAt: null,
    };
    expect(link.chainId).toBe('chain-abc');
    expect(link.previousHash).toBeTruthy();
    expect(link.event.eventType).toBe('AUDIT_CHAIN_LINK_ADDED');
    expect(link.sealedAt).toBeNull();
  });
});

describe('AuditChainManifest', () => {
  it('should default schemaVersion to 1', () => {
    const event: AuditEvent = {
      runId: 'run-sg-abc123',
      eventType: 'AUDIT_CHAIN_STARTED',
      timestamp: '2026-05-22T10:00:00.000Z',
      sequence: 0,
      severity: 'info',
      producer: 'arc-backend',
      data: {},
    };
    const manifest: AuditChainManifest = {
      chainId: 'chain-abc',
      runId: 'run-sg-abc123',
      links: [],
      schemaVersion: 1,
      createdAt: '2026-05-22T10:00:00.000Z',
      sealedAt: null,
      verifiedAt: null,
      status: 'active',
    };
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.status).toBe('active');
  });

  it('should accept sealed state', () => {
    const manifest: AuditChainManifest = {
      chainId: 'chain-def',
      runId: 'run-sg-def456',
      links: [],
      schemaVersion: 1,
      createdAt: '2026-05-22T10:00:00.000Z',
      sealedAt: '2026-05-22T11:00:00.000Z',
      verifiedAt: '2026-05-22T11:05:00.000Z',
      status: 'verified',
    };
    expect(manifest.sealedAt).toBe('2026-05-22T11:00:00.000Z');
    expect(manifest.verifiedAt).toBe('2026-05-22T11:05:00.000Z');
    expect(manifest.status).toBe('verified');
  });
});
