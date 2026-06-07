/**
 * ARC Mobile Runtime — Event and Policy Decision types.
 * Mirrors Python mobile/recorder.py MobileRuntimeEvent and policy.py MobilePolicyDecision.
 * Updated in PR17 to add prev_event_hash (tamper-evident chain, PR4).
 */

export interface MobileRuntimeEvent {
  schema_version: number;
  event_id: string;
  event_type: 'mobile.step.simulated';
  plan_id: string;
  step_id?: string | null;
  capability_id?: string | null;
  timestamp: string;
  sequence: number;
  allowed: boolean;
  mock: boolean;
  payload_hash: string;
  prev_event_hash: string;  // Added PR17: SHA-256 of preceding event; "0"*64 for first event
  event_hash: string;
  metadata: Record<string, unknown>;
}

export interface MobilePolicyDecision {
  allowed: boolean;
  approval_required: boolean;
  capability_id?: string | null;
  plan_id?: string | null;
  reason: string;
  denied_rules: string[];
  required_approvals: string[];
  mcp_exposable: boolean;
  policy_version?: string;  // Added PR12
}

export function isMobileRuntimeEvent(obj: unknown): obj is MobileRuntimeEvent {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'event_hash' in obj &&
    'payload_hash' in obj &&
    'prev_event_hash' in obj
  );
}

export function isMobilePolicyDecision(obj: unknown): obj is MobilePolicyDecision {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'allowed' in obj &&
    'reason' in obj &&
    'denied_rules' in obj
  );
}
