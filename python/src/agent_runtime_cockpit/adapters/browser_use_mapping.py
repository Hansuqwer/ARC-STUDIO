"""Browser Use → AG-UI event mapping."""

from __future__ import annotations

import time
from typing import Any

from ..ag_ui import AGUIEventType, MappingContext, register_mapper


def _map(native: dict[str, Any], ctx: MappingContext) -> list[dict[str, Any]]:
    kind = native.get("type", "")
    ts = native.get("timestamp", time.time())
    data = native.get("data", {})

    if kind == "BROWSER_USE_RUN_START":
        return [{"type": AGUIEventType.RUN_STARTED.value, "timestamp": ts}]
    if kind == "BROWSER_USE_RUN_END":
        mid = f"{ctx.run_id}:browser-use"
        output = str(data.get("output", ""))
        return [
            {
                "type": AGUIEventType.TEXT_MESSAGE_START.value,
                "timestamp": ts,
                "messageId": mid,
                "role": "assistant",
            },
            {
                "type": AGUIEventType.TEXT_MESSAGE_CONTENT.value,
                "timestamp": ts,
                "messageId": mid,
                "delta": output,
            },
            {"type": AGUIEventType.TEXT_MESSAGE_END.value, "timestamp": ts, "messageId": mid},
            {"type": AGUIEventType.RUN_FINISHED.value, "timestamp": ts},
        ]
    if kind == "BROWSER_USE_RUN_ERROR":
        return [
            {
                "type": AGUIEventType.RUN_ERROR.value,
                "timestamp": ts,
                "message": data.get("error", "unknown"),
            }
        ]
    return [{"type": AGUIEventType.RAW.value, "timestamp": ts, "raw": native}]


register_mapper("browser-use", _map)
