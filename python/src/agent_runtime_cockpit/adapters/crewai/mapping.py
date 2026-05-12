"""Native CrewAI → AG-UI mapping."""
from __future__ import annotations

import json
import time
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    k = native.get("kind")
    if k == "crew.start":
        return [{"type": AGUIEventType.RUN_STARTED.value,
                 "threadId": ctx.thread_id, "runId": ctx.run_id}]
    if k == "crew.finish":
        return [{"type": AGUIEventType.RUN_FINISHED.value,
                 "threadId": ctx.thread_id, "runId": ctx.run_id}]
    if k == "crew.error":
        return [{"type": AGUIEventType.RUN_ERROR.value,
                 "message": str(native.get("error", "unknown")),
                 "code": "CREWAI_ERROR"}]
    if k == "agent.start":
        return [{"type": AGUIEventType.STEP_STARTED.value,
                 "stepName": f"agent:{native['agent']}"}]
    if k == "agent.text":
        mid = f"{ctx.run_id}:{int(time.time()*1000)}"
        return [
            {"type": AGUIEventType.TEXT_MESSAGE_START.value, "messageId": mid, "role": "assistant"},
            {"type": AGUIEventType.TEXT_MESSAGE_CONTENT.value, "messageId": mid, "delta": native.get("text", "")},
            {"type": AGUIEventType.TEXT_MESSAGE_END.value, "messageId": mid},
        ]
    if k == "task.start":
        return [{"type": AGUIEventType.STEP_STARTED.value,
                 "stepName": f"task:{native.get('task','?')}"}]
    if k == "task.finish":
        return [{"type": AGUIEventType.STEP_FINISHED.value,
                 "stepName": f"task:{native.get('task','?')}"}]
    if k == "tool.call":
        t = native["tool"]
        return [
            {"type": AGUIEventType.TOOL_CALL_START.value,
             "toolCallId": t["id"], "toolCallName": t["name"]},
            {"type": AGUIEventType.TOOL_CALL_ARGS.value,
             "toolCallId": t["id"], "delta": json.dumps(t.get("args", {}))},
            {"type": AGUIEventType.TOOL_CALL_END.value, "toolCallId": t["id"]},
        ]
    if k == "tool.result":
        tid = native["tool_id"]
        return [{"type": AGUIEventType.TOOL_CALL_RESULT.value,
                 "toolCallId": tid, "messageId": f"{tid}:result",
                 "content": json.dumps(native.get("result"))}]
    if k == "llm.chunk":
        return [{"type": AGUIEventType.TEXT_MESSAGE_CHUNK.value,
                 "role": "assistant", "delta": native.get("delta", "")}]
    return [{"type": AGUIEventType.RAW.value, "event": native, "source": "crewai"}]


register_mapper("crewai", _map)
