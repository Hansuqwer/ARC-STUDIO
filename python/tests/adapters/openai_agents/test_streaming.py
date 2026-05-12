import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, List

from agent_runtime_cockpit.adapters.openai_agents.streaming import stream_to_ag_ui
from agent_runtime_cockpit.ag_ui import MappingContext

import agent_runtime_cockpit.adapters.openai_agents.mapping.openai_agents  # noqa: F401


@dataclass
class _Agent:
    name: str

@dataclass
class _MsgItem:
    agent: _Agent
    raw_item: Any = None

@dataclass
class _RawItem:
    id: str
    name: str
    arguments: str

@dataclass
class _ToolCallItem:
    raw_item: _RawItem

@dataclass
class _ToolOut:
    tool_call_id: str
    output: Any

@dataclass
class _Handoff:
    source_agent: _Agent
    target_agent: _Agent

class AgentUpdatedStreamEvent:
    def __init__(self, agent: _Agent) -> None: self.new_agent = agent
class RunItemStreamEvent:
    def __init__(self, item: Any) -> None: self.item = item
class RawResponsesStreamEvent:
    def __init__(self, data: Any) -> None: self.data = data

class MessageOutputItem(_MsgItem): pass
class ToolCallItem(_ToolCallItem): pass
class ToolCallOutputItem(_ToolOut): pass
class HandoffOutputItem(_Handoff): pass


class FakeRunResultStreaming:
    def __init__(self, events: List[Any]) -> None:
        self._events = events

    async def stream_events(self) -> AsyncIterator[Any]:
        for e in self._events:
            yield e


def test_full_stream_maps_to_ag_ui():
    a = _Agent(name="writer")
    msg = MessageOutputItem(agent=a, raw_item=type("M", (), {"content": [type("T", (), {"text": "Hi"})]})())
    tool = ToolCallItem(raw_item=_RawItem(id="t1", name="search", arguments='{"q":"x"}'))
    res = ToolCallOutputItem(tool_call_id="t1", output={"hits": 1})
    h = HandoffOutputItem(source_agent=a, target_agent=_Agent("editor"))
    fake = FakeRunResultStreaming([
        AgentUpdatedStreamEvent(a),
        RunItemStreamEvent(msg),
        RunItemStreamEvent(tool),
        RunItemStreamEvent(res),
        RunItemStreamEvent(h),
        RawResponsesStreamEvent({"type": "response.completed"}),
    ])
    ctx = MappingContext(thread_id="th", run_id="r1", runtime="openai-agents")

    async def collect():
        out = []
        async for e in stream_to_ag_ui(fake, ctx):
            out.append(e)
        return out

    events = asyncio.run(collect())
    types = [e["type"] for e in events]
    assert "RUN_STARTED" in types
    assert "RUN_FINISHED" in types
    assert "TOOL_CALL_START" in types
    assert "TOOL_CALL_RESULT" in types
    assert any(e.get("delta") == "Hi" for e in events if e["type"] == "TEXT_MESSAGE_CONTENT")
