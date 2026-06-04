import type { MobileRuntimeEvent } from './mobile-events';

export interface MobileTrace {
  schema_version: number;
  plan_id: string;
  events: MobileRuntimeEvent[];
  trace_hash: string;
}

export function isMobileTrace(obj: unknown): obj is MobileTrace {
  return typeof obj === 'object' && obj !== null && 'events' in obj && Array.isArray((obj as MobileTrace).events);
}
