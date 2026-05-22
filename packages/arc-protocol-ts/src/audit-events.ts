/**
 * Audit event schema types for ARC Studio.
 * Mirrors ADR-021 audit chain architecture.
 */

export type AuditEventType =
  | 'AUDIT_CHAIN_STARTED'
  | 'AUDIT_CHAIN_LINK_ADDED'
  | 'AUDIT_CHAIN_SEALED'
  | 'AUDIT_CHAIN_VERIFIED'
  | 'AUDIT_CHAIN_FAILED'
  | 'AUDIT_KEY_ROTATED'
  | 'AUDIT_EXPORTED';

export type AuditEventSeverity = 'info' | 'warning' | 'critical';

export interface AuditEvent {
  runId: string;
  eventType: AuditEventType;
  timestamp: string;
  sequence: number;
  severity: AuditEventSeverity;
  producer: string;
  data: Record<string, unknown>;
}

export interface AuditChainLink {
  chainId: string;
  previousHash: string;
  hash: string;
  event: AuditEvent;
  sealedAt: string | null;
}

export interface AuditChainManifest {
  chainId: string;
  runId: string;
  links: AuditChainLink[];
  schemaVersion: number;
  createdAt: string;
  sealedAt: string | null;
  verifiedAt: string | null;
  status: 'active' | 'sealed' | 'verified' | 'compromised';
}
