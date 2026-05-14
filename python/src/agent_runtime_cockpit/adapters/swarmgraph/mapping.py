"""Native SwarmGraph → AG-UI mapping."""
from __future__ import annotations

import time
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    kind = native.get("kind")
    ts = native.get("ts", time.time())
    if kind == "run.start":
        return [{"type": AGUIEventType.RUN_STARTED.value, "timestamp": ts}]
    if kind == "run.finish":
        return [{"type": AGUIEventType.RUN_FINISHED.value, "timestamp": ts}]
    if kind == "run.error":
        return [{"type": AGUIEventType.RUN_ERROR.value, "timestamp": ts,
                 "message": native.get("error", {}).get("message", "unknown"),
                 "code": native.get("error", {}).get("code", "UNKNOWN")}]
    if kind == "agent.text":
        mid = f"{ctx.run_id}:{int(ts * 1000)}"
        return [
            {"type": AGUIEventType.TEXT_MESSAGE_START.value, "timestamp": ts,
             "messageId": mid, "role": "assistant"},
            {"type": AGUIEventType.TEXT_MESSAGE_CONTENT.value, "timestamp": ts,
             "messageId": mid, "delta": native.get("text", "")},
            {"type": AGUIEventType.TEXT_MESSAGE_END.value, "timestamp": ts, "messageId": mid},
        ]
    if kind == "tool.call":
        tool = native.get("tool", {})
        return [
            {"type": AGUIEventType.TOOL_CALL_START.value, "timestamp": ts,
             "toolCallId": tool.get("id", "?"), "toolCallName": tool.get("name", "tool")},
            {"type": AGUIEventType.TOOL_CALL_ARGS.value, "timestamp": ts,
             "toolCallId": tool.get("id", "?"), "delta": str(tool.get("args", {}))},
            {"type": AGUIEventType.TOOL_CALL_END.value, "timestamp": ts,
             "toolCallId": tool.get("id", "?")},
        ]
    if kind == "tool.result":
        return [{"type": AGUIEventType.TOOL_CALL_RESULT.value, "timestamp": ts,
                 "toolCallId": native.get("tool_id", "?"),
                 "content": str(native.get("result", ""))}]
    if kind == "handoff":
        return [{"type": AGUIEventType.STEP_STARTED.value, "timestamp": ts,
                 "stepName": f"handoff:{native.get('agent', '?')}"}]
    if kind == "state":
        return [{"type": AGUIEventType.STATE_SNAPSHOT.value, "timestamp": ts,
                 "snapshot": native.get("state", {})}]
    return [{"type": AGUIEventType.RAW.value, "timestamp": ts,
             "event": native, "source": "swarmgraph"}]


register_mapper("swarmgraph", _map)
