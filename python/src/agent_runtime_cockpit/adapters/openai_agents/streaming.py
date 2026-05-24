"""Bridge OpenAI Agents SDK streaming events into AG-UI."""

from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Iterable

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, map_event

_NATIVE_RUNTIME = "openai-agents"


def _stream_event_to_native(sdk_event: Any) -> Iterable[dict[str, Any]]:
    cls = type(sdk_event).__name__
    if cls == "AgentUpdatedStreamEvent":
        yield {"kind": "agent.updated", "agent": getattr(sdk_event.new_agent, "name", "?")}
        return
    if cls == "RawResponsesStreamEvent":
        data = getattr(sdk_event, "data", None)
        yield {"kind": "raw", "raw": _safe_to_dict(data)}
        return
    if cls == "RunItemStreamEvent":
        item = sdk_event.item
        item_cls = type(item).__name__
        if item_cls == "MessageOutputItem":
            yield {"kind": "agent.text", "agent": item.agent.name, "text": _message_text(item)}
        elif item_cls == "ToolCallItem":
            raw = getattr(item, "raw_item", item)
            yield {
                "kind": "tool.call",
                "tool": {
                    "id": getattr(raw, "id", uuid.uuid4().hex[:8]),
                    "name": getattr(raw, "name", "tool"),
                    "args": json.loads(getattr(raw, "arguments", "{}") or "{}"),
                },
            }
        elif item_cls == "ToolCallOutputItem":
            yield {
                "kind": "tool.result",
                "tool_id": getattr(item, "tool_call_id", "?"),
                "result": getattr(item, "output", None),
            }
        elif item_cls == "HandoffOutputItem":
            yield {
                "kind": "handoff",
                "from": getattr(item.source_agent, "name", "?"),
                "to": getattr(item.target_agent, "name", "?"),
            }
        return


def _safe_to_dict(o: Any) -> Any:
    if o is None:
        return None
    if hasattr(o, "model_dump"):
        return o.model_dump()
    if isinstance(o, dict):
        return o
    return {"repr": repr(o)}


def _message_text(item: Any) -> str:
    content = getattr(item, "raw_item", None)
    if content is None:
        return ""
    parts = getattr(content, "content", []) or []
    out = []
    for p in parts:
        text = getattr(p, "text", None)
        if isinstance(text, str):
            out.append(text)
    return "".join(out)


async def stream_to_ag_ui(
    run_result_streaming: Any,
    ctx: MappingContext,
) -> AsyncIterator[dict[str, Any]]:
    for event in from_singleton(AGUIEventType.RUN_STARTED, ctx):
        yield event
    async for sdk_event in run_result_streaming.stream_events():
        for native in _stream_event_to_native(sdk_event):
            for ag in map_event(_NATIVE_RUNTIME, native, ctx):
                yield ag
    for event in from_singleton(AGUIEventType.RUN_FINISHED, ctx):
        yield event


def from_singleton(t: AGUIEventType, ctx: MappingContext) -> Iterable[dict[str, Any]]:
    yield {"type": t.value, "threadId": ctx.thread_id, "runId": ctx.run_id}
