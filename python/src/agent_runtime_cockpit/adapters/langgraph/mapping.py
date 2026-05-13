"""Native LangGraph → AG-UI mapping."""
from __future__ import annotations

import time
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    event = native.get("event", "")
    ts = time.time()
    if event == "on_chain_start":
        return [{"type": AGUIEventType.STEP_STARTED.value, "timestamp": ts,
                 "stepName": native.get("name", "?")}]
    if event == "on_chain_end":
        return [{"type": AGUIEventType.STEP_FINISHED.value, "timestamp": ts,
                 "stepName": native.get("name", "?")}]
    if event == "on_chat_model_stream":
        data = native.get("data", {})
        chunk = data.get("chunk", {})
        content = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)
        mid = f"{ctx.run_id}:{int(ts * 1000)}"
        return [{"type": AGUIEventType.TEXT_MESSAGE_CHUNK.value, "timestamp": ts,
                 "role": "assistant", "delta": content, "messageId": mid}]
    if event == "on_tool_start":
        return [{"type": AGUIEventType.TOOL_CALL_START.value, "timestamp": ts,
                 "toolCallId": native.get("run_id", "?"),
                 "toolCallName": native.get("name", "?")}]
    if event == "on_tool_end":
        return [{"type": AGUIEventType.TOOL_CALL_RESULT.value, "timestamp": ts,
                 "toolCallId": native.get("run_id", "?"),
                 "content": str(native.get("data", ""))}]
    return [{"type": AGUIEventType.RAW.value, "timestamp": ts,
             "event": native, "source": "langgraph"}]


register_mapper("langgraph", _map)
