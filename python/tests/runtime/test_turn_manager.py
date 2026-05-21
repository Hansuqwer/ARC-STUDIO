from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken, never_cancelled
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderResponse, StreamChunk, UsageRecord
from agent_runtime_cockpit.runtime.turn_manager import TurnManager


@dataclass
class _Event:
    name: str
    payload: dict


class _Provider:
    def __init__(self, response: ProviderResponse | None = None, chunks: list[StreamChunk] | None = None) -> None:
        self.response = response or ProviderResponse(
            call_id="c1",
            model="claude-test",
            content="assistant response",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=2),
        )
        self.chunks = chunks or []
        self.complete_request = None
        self.stream_request = None

    async def complete(self, request, *, cancellation_token):
        self.complete_request = request
        cancellation_token.raise_if_cancelled()
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
