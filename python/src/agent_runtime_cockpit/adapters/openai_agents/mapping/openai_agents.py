"""Native → AG-UI mapping for the OpenAI Agents SDK adapter."""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    kind = native.get("kind")
    ts = time.time()
    if kind == "agent.updated":
        return [{"type": AGUIEventType.STEP_STARTED.value,
                 "timestamp": ts, "stepName": f"agent:{native['agent']}"}]
    if kind == "agent.text":
        mid = f"{ctx.run_id}:{int(ts * 1000)}"
        return [
            {"type": AGUIEventType.TEXT_MESSAGE_START.value, "messageId": mid, "role": "assistant"},
            {"type": AGUIEventType.TEXT_MESSAGE_CONTENT.value, "messageId": mid, "delta": native.get("text", "")},
            {"type": AGUIEventType.TEXT_MESSAGE_END.value, "messageId": mid},
        ]
    if kind == "tool.call":
        tool = native["tool"]
        return [
            {"type": AGUIEventType.TOOL_CALL_START.value,
             "toolCallId": tool["id"], "toolCallName": tool["name"]},
            {"type": AGUIEventType.TOOL_CALL_ARGS.value,
             "toolCallId": tool["id"], "delta": json.dumps(tool.get("args", {}))},
            {"type": AGUIEventType.TOOL_CALL_END.value, "toolCallId": tool["id"]},
        ]
    if kind == "tool.result":
        tid = native["tool_id"]
        return [{"type": AGUIEventType.TOOL_CALL_RESULT.value,
                 "toolCallId": tid, "messageId": f"{tid}:result",
                 "content": json.dumps(native.get("result"))}]
    if kind == "handoff":
        return [{"type": AGUIEventType.STEP_STARTED.value,
                 "stepName": f"handoff:{native['from']}->{native['to']}"}]
    if kind == "raw":
        return [{"type": AGUIEventType.RAW.value, "event": native.get("raw"), "source": "openai-agents"}]
    return [{"type": AGUIEventType.RAW.value, "event": native, "source": "openai-agents"}]


register_mapper("openai-agents", _map)
