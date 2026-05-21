from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken, never_cancelled
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderResponse, StreamChunk, UsageRecord
from agent_runtime_cockpit.runtime.turn_manager import TurnManager
from agent_runtime_cockpit.tools import ToolRegistry
from agent_runtime_cockpit.tools.builtin import GetCurrentTimeTool


@dataclass
class _Event:
    name: str
    payload: dict


class _Provider:
    def __init__(self, response: ProviderResponse | None = None, chunks: list[StreamChunk] | None = None, responses: list[ProviderResponse] | None = None) -> None:
        self.response = response or ProviderResponse(
            call_id="c1",
            model="claude-test",
            content="assistant response",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=2),
        )
        self.responses = list(responses or [])
        self.chunks = chunks or []
        self.complete_requests = []
        self.complete_request = None
        self.stream_request = None

    async def complete(self, request, *, cancellation_token):
        self.complete_request = request
        self.complete_requests.append(request)
        cancellation_token.raise_if_cancelled()
        if self.responses:
            return self.responses.pop(0)
        return self.response

    async def stream(self, request, *, cancellation_token):
        self.stream_request = request
        for chunk in self.chunks:
            cancellation_token.raise_if_cancelled()
            yield chunk

    async def cancel(self, call_id: str) -> None:
        return None


def _sink(events: list[_Event]):
    def emit(name: str, payload: dict) -> None:
        events.append(_Event(name, payload))
    return emit


@pytest.mark.asyncio
async def test_run_turn_complete_emits_started_completed_and_updates_history() -> None:
    events: list[_Event] = []
    provider = _Provider()
    manager = TurnManager(provider, model="claude-test", event_sink=_sink(events))
    session = ChatSession()

    result = await manager.run_turn(session, "hello", cancellation_token=never_cancelled())

    assert result.content == "assistant response"
    assert [event.name for event in events] == ["turn.started", "turn.completed"]
    assert [message["role"] for message in session.history] == ["user", "assistant"]
    assert session.history[0]["content"] == "hello"
    assert session.history[1]["content"] == "assistant response"
    assert provider.complete_request.messages[-1].content == "hello"


@pytest.mark.asyncio
async def test_run_turn_stream_emits_chunk_events_and_final_history() -> None:
    events: list[_Event] = []
    chunks = [
        StreamChunk(call_id="c1", chunk_type="start"),
        StreamChunk(call_id="c1", chunk_type="delta", delta="he"),
        StreamChunk(call_id="c1", chunk_type="delta", delta="llo"),
        StreamChunk(call_id="c1", chunk_type="stop", payload={"usage": {"input_tokens": 1, "output_tokens": 2}}),
    ]
    provider = _Provider(chunks=chunks)
    manager = TurnManager(provider, model="claude-test", event_sink=_sink(events))
    session = ChatSession()

    result = await manager.run_turn(session, "hello", cancellation_token=never_cancelled(), stream=True)

    assert result.content == "hello"
    assert [event.name for event in events] == [
        "turn.started",
        "stream.chunk.start",
        "stream.chunk.delta",
        "stream.chunk.delta",
        "stream.chunk.stop",
        "turn.completed",
    ]
    assert session.history[-1]["role"] == "assistant"
    assert session.history[-1]["content"] == "hello"


@pytest.mark.asyncio
async def test_run_turn_cancelled_before_complete_preserves_state() -> None:
    events: list[_Event] = []
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    provider = _Provider()
    manager = TurnManager(provider, model="claude-test", event_sink=_sink(events))
    session = ChatSession()

    result = await manager.run_turn(session, "hello", cancellation_token=token)

    assert result.degraded is True
    assert result.degraded_reason == "cancelled"
    assert result.partial is True
    assert [event.name for event in events] == ["turn.started", "turn.cancelled"]
    assert [message["role"] for message in session.history] == ["user"]


@pytest.mark.asyncio
async def test_run_turn_executes_single_tool_roundtrip() -> None:
    events: list[_Event] = []
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    provider = _Provider(responses=[
        ProviderResponse(
            call_id="c1",
            model="claude-test",
            content="need time",
            finish_reason="tool_use",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
            tool_calls=[{"name": "get_current_time", "args": {}}],
        ),
        ProviderResponse(
            call_id="c2",
            model="claude-test",
            content="done",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=2, output_tokens=2),
        ),
    ])
    manager = TurnManager(provider, model="claude-test", event_sink=_sink(events), tool_registry=registry)
    session = ChatSession(tools_enabled=True)

    result = await manager.run_turn(session, "what time", cancellation_token=never_cancelled())

    assert result.content == "done"
    assert [event.name for event in events] == [
        "turn.started",
        "tool.requested",
        "tool.executed",
        "turn.completed",
    ]
    assert [message["role"] for message in session.history] == ["user", "tool", "assistant"]
    assert 'trust="trusted" tool="get_current_time"' in session.history[1]["content"]
    assert len(provider.complete_requests) == 2


@pytest.mark.asyncio
async def test_run_turn_blocks_tool_not_in_allowlist() -> None:
    events: list[_Event] = []
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    provider = _Provider(responses=[
        ProviderResponse(
            call_id="c1",
            model="claude-test",
            content="need time",
            finish_reason="tool_use",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
            tool_calls=[{"name": "get_current_time", "args": {}}],
        ),
        ProviderResponse(
            call_id="c2",
            model="claude-test",
            content="blocked result handled",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=2, output_tokens=2),
        ),
    ])
    manager = TurnManager(provider, model="claude-test", event_sink=_sink(events), tool_registry=registry)
    session = ChatSession(tools_enabled=True, available_tools=["read_file"])

    result = await manager.run_turn(session, "what time", cancellation_token=never_cancelled())

    assert result.content == "blocked result handled"
    assert session.history[1]["content"] == '<tool_result trust="blocked" tool="get_current_time" reason="tool_not_allowed"/>'
    assert [event.name for event in events] == ["turn.started", "tool.result.blocked", "turn.completed"]


@pytest.mark.asyncio
async def test_run_turn_degrades_at_tool_iteration_cap() -> None:
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    looping_response = ProviderResponse(
        call_id="c1",
        model="claude-test",
        content="loop",
        finish_reason="tool_use",
        usage=UsageRecord(input_tokens=1, output_tokens=1),
        tool_calls=[{"name": "get_current_time", "args": {}}],
    )
    provider = _Provider(responses=[looping_response, looping_response, looping_response])
    manager = TurnManager(provider, model="claude-test", tool_registry=registry)
    session = ChatSession(tools_enabled=True, max_tool_iterations=1)

    result = await manager.run_turn(session, "loop", cancellation_token=never_cancelled())

    assert result.degraded is True
    assert result.degraded_reason == "max_tool_iterations_reached"
    assert result.response is not None
    assert result.response.degraded is True
