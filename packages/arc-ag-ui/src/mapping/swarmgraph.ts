import { AGUIEventType } from '../event-types';
import { AGUIBaseEvent, MappingContext, RuntimeEventMapper, registerMapper } from '../mapper';

interface SwarmGraphNativeEvent {
  kind: string;
  ts?: number;
  agent?: string;
  payload?: Record<string, unknown>;
  text?: string;
  tool?: { id: string; name: string; args?: unknown; result?: unknown };
  error?: { code?: string; message: string };
  state?: Record<string, unknown>;
}

export const SwarmGraphMapper: RuntimeEventMapper<SwarmGraphNativeEvent> = {
  runtime: 'swarmgraph',
  map(native, ctx): AGUIBaseEvent[] {
    const ts = native.ts ?? Date.now();
    const base = { timestamp: ts, rawEvent: native } as const;
    switch (native.kind) {
      case 'run.start':
        return [{ ...base, type: AGUIEventType.RUN_STARTED, threadId: ctx.threadId, runId: ctx.runId } as AGUIBaseEvent];
      case 'run.finish':
        return [{ ...base, type: AGUIEventType.RUN_FINISHED, threadId: ctx.threadId, runId: ctx.runId } as AGUIBaseEvent];
      case 'run.error':
        return [{ ...base, type: AGUIEventType.RUN_ERROR, message: native.error?.message ?? 'unknown', code: native.error?.code } as AGUIBaseEvent];
      case 'handoff':
        return [{ ...base, type: AGUIEventType.STEP_STARTED, stepName: `handoff:${native.agent ?? '?'}` } as AGUIBaseEvent];
      case 'agent.text': {
        const msgId = `${ctx.runId}:${ts}`;
        return [
          { ...base, type: AGUIEventType.TEXT_MESSAGE_START, messageId: msgId, role: 'assistant' } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TEXT_MESSAGE_CONTENT, messageId: msgId, delta: native.text ?? '' } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TEXT_MESSAGE_END, messageId: msgId } as AGUIBaseEvent,
        ];
      }
      case 'tool.call': {
        const id = native.tool!.id;
        return [
          { ...base, type: AGUIEventType.TOOL_CALL_START, toolCallId: id, toolCallName: native.tool!.name } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TOOL_CALL_ARGS, toolCallId: id, delta: JSON.stringify(native.tool!.args ?? {}) } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TOOL_CALL_END, toolCallId: id } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TOOL_CALL_RESULT, toolCallId: id, messageId: `${id}:result`, content: JSON.stringify(native.tool!.result ?? null) } as AGUIBaseEvent,
        ];
      }
      case 'state':
        return [{ ...base, type: AGUIEventType.STATE_SNAPSHOT, snapshot: native.state ?? {} } as AGUIBaseEvent];
      default:
        return [{ ...base, type: AGUIEventType.RAW, event: native, source: 'swarmgraph' } as AGUIBaseEvent];
    }
  },
};

registerMapper(SwarmGraphMapper);
