// Runtime-native event → AG-UI event mapping core.
// Adapter-specific mappers (swarmgraph.ts, langgraph.ts) plug in here.

import { AGUIEventType } from './event-types';
import { safeEvent } from './redaction';

export interface AGUIBaseEvent {
  type: AGUIEventType;
  timestamp?: number;
  rawEvent?: unknown;
}

export interface MappingContext {
  threadId: string;
  runId: string;
  runtime: string;            // 'swarmgraph' | 'langgraph' | 'openai-agents' | ...
}

export interface RuntimeEventMapper<TNative = unknown> {
  readonly runtime: string;
  map(native: TNative, ctx: MappingContext): AGUIBaseEvent[];
}

const REGISTRY = new Map<string, RuntimeEventMapper>();

export function registerMapper(m: RuntimeEventMapper): void {
  REGISTRY.set(m.runtime, m);
}

export function mapEvent(runtime: string, native: unknown, ctx: MappingContext): AGUIBaseEvent[] {
  const mapper = REGISTRY.get(runtime);
  if (!mapper) {
    return [safeEvent({
      type: AGUIEventType.RAW,
      timestamp: Date.now(),
      event: native,
      source: runtime,
    } as AGUIBaseEvent & { event: unknown; source: string })];
  }
  try {
    return mapper.map(native, ctx).map(safeEvent);
  } catch (err) {
    return [safeEvent({
      type: AGUIEventType.RUN_ERROR,
      timestamp: Date.now(),
      threadId: ctx.threadId,
      runId: ctx.runId,
      message: (err as Error).message,
      code: 'MAPPER_THREW',
    } as AGUIBaseEvent & Record<string, unknown>)];
  }
}

export function listRegisteredRuntimes(): string[] {
  return Array.from(REGISTRY.keys());
}
