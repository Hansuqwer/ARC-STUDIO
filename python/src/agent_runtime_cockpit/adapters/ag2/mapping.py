"""Native AG2 → AG-UI mapping."""
from __future__ import annotations

import time
from typing import Any

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    et = native.get("event")
    if et == "run.start":
        return [{"type": AGUIEventType.RUN_STARTED.value,
                 "threadId": ctx.thread_id, "runId": ctx.run_id}]
    if et == "run.finish":
        return [{"type": AGUIEventType.RUN_FINISHED.value,
                 "threadId": ctx.thread_id, "runId": ctx.run_id}]
    if et == "run.error":
        return [{"type": AGUIEventType.RUN_ERROR.value,
                 "message": native.get("message", "unknown"), "code": "AG2_ERROR"}]
    if et == "speaker.changed":
        return [{"type": AGUIEventType.STEP_STARTED.value,
                 "stepName": f"speaker:{native.get('sender','?')}"}]
    if et == "message":
        mid = f"{ctx.run_id}:{int(time.time()*1000)}"
        return [
            {"type": AGUIEventType.TEXT_MESSAGE_START.value, "messageId": mid,
             "role": "assistant", "name": native.get("sender")},
            {"type": AGUIEventType.TEXT_MESSAGE_CONTENT.value, "messageId": mid,
             "delta": str(native.get("content", ""))},
            {"type": AGUIEventType.TEXT_MESSAGE_END.value, "messageId": mid},
        ]
    return [{"type": AGUIEventType.RAW.value, "event": native, "source": "ag2"}]


register_mapper("ag2", _map)
