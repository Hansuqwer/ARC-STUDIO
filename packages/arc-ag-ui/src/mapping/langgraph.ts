import { AGUIEventType } from '../event-types';
import { AGUIBaseEvent, MappingContext, RuntimeEventMapper, registerMapper } from '../mapper';

// LangGraph astream_events v2 payloads, minimal shape we care about.
interface LangGraphEvent {
  event: string;                       // e.g. on_chain_start, on_chat_model_stream
  name?: string;
  run_id?: string;
  data?: Record<string, unknown>;
  ts?: number;
}

export const LangGraphMapper: RuntimeEventMapper<LangGraphEvent> = {
  runtime: 'langgraph',
  map(native, ctx): AGUIBaseEvent[] {
    const ts = native.ts ?? Date.now();
    const base = { timestamp: ts, rawEvent: native } as const;
    switch (native.event) {
      case 'on_chain_start':
        if (native.name && native.name.toLowerCase() === 'langgraph') {
          return [{ ...base, type: AGUIEventType.RUN_STARTED, threadId: ctx.threadId, runId: ctx.runId } as AGUIBaseEvent];
        }
        return [{ ...base, type: AGUIEventType.STEP_STARTED, stepName: native.name ?? 'step' } as AGUIBaseEvent];
      case 'on_chain_end':
        if (native.name && native.name.toLowerCase() === 'langgraph') {
          return [{ ...base, type: AGUIEventType.RUN_COMPLETED, threadId: ctx.threadId, runId: ctx.runId } as AGUIBaseEvent];
        }
        return [{ ...base, type: AGUIEventType.STEP_FINISHED, stepName: native.name ?? 'step' } as AGUIBaseEvent];
      case 'on_chat_model_stream': {
        const chunk = (native.data?.chunk as { content?: string } | undefined)?.content ?? '';
        return [{ ...base, type: AGUIEventType.TEXT_MESSAGE_CHUNK, messageId: native.run_id, role: 'assistant', delta: chunk } as AGUIBaseEvent];
      }
      case 'on_tool_start': {
        const id = native.run_id ?? `${ctx.runId}:${ts}`;
        return [
          { ...base, type: AGUIEventType.TOOL_CALL_START, toolCallId: id, toolCallName: native.name ?? 'tool' } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TOOL_CALL_ARGS, toolCallId: id, delta: JSON.stringify(native.data?.input ?? {}) } as AGUIBaseEvent,
        ];
      }
      case 'on_tool_end': {
        const id = native.run_id ?? `${ctx.runId}:${ts}`;
        return [
          { ...base, type: AGUIEventType.TOOL_CALL_END, toolCallId: id } as AGUIBaseEvent,
          { ...base, type: AGUIEventType.TOOL_CALL_RESULT, toolCallId: id, messageId: `${id}:result`, content: JSON.stringify(native.data?.output ?? null) } as AGUIBaseEvent,
        ];
      }
      case 'on_chain_state':
        return [{ ...base, type: AGUIEventType.STATE_SNAPSHOT, snapshot: (native.data ?? {}) as Record<string, unknown> } as AGUIBaseEvent];
      case 'on_error':
        return [{ ...base, type: AGUIEventType.RUN_FAILED, message: String(native.data?.error ?? 'unknown'), code: 'LANGGRAPH_ERROR' } as AGUIBaseEvent];
      default:
        return [{ ...base, type: AGUIEventType.RAW, event: native, source: 'langgraph' } as AGUIBaseEvent];
    }
  },
};

registerMapper(LangGraphMapper);
