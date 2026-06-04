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
}

export function isMobileRuntimeEvent(obj: unknown): obj is MobileRuntimeEvent {
  return typeof obj === 'object' && obj !== null && 'event_hash' in obj && 'payload_hash' in obj;
}
