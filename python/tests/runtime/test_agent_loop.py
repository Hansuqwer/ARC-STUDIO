from __future__ import annotations

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import (
    CancellationReason,
    CancellationToken,
    never_cancelled,
)
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderResponse, StreamChunk, UsageRecord
from agent_runtime_cockpit.runtime.agent_loop import AgentLoop
from agent_runtime_cockpit.runtime.turn_manager import TurnManager
from agent_runtime_cockpit.tools import default_tool_registry


class Provider:
    def __init__(self, responses=None, chunks=None):
        self.responses = list(responses or [])
        self.chunks = list(chunks or [])
        self.requests = []

    async def complete(self, request, *, cancellation_token):
        self.requests.append(request)
        cancellation_token.raise_if_cancelled()
        return self.responses.pop(0)

    async def stream(self, request, *, cancellation_token):
        self.requests.append(request)
        for chunk in self.chunks:
            yield chunk

    async def cancel(self, call_id: str) -> None:
        return None


def response(content="done", *, tool_calls=None, finish="stop"):
    return ProviderResponse(
        call_id="c",
        model="m",
        content=content,
        finish_reason=finish,
        usage=UsageRecord(input_tokens=1, output_tokens=1),
        tool_calls=tool_calls or [],
    )


@pytest.mark.asyncio
async def test_turn_manager_sends_tool_definitions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = Provider([response()])
    session = ChatSession(tools_enabled=True)
    manager = TurnManager(
        provider, model="m", tool_registry=default_tool_registry(tmp_path, tmp_path / "trust.json")
    )
    await manager.run_turn(session, "hi", cancellation_token=never_cancelled())
    tool_names = {tool["name"] for tool in provider.requests[0].tools}
    assert {"read_file", "write_file", "edit_file", "create_file", "bash"}.issubset(tool_names)


@pytest.mark.asyncio
async def test_turn_manager_handles_tool_use_after_streaming(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = Provider(
        responses=[response("Done")],
        chunks=[
            StreamChunk(call_id="c", chunk_type="start"),
            StreamChunk(
                call_id="c",
                chunk_type="tool_use",
                payload={
                    "tool_calls": [
                        {"name": "create_file", "args": {"path": "a.txt", "content": "x"}}
                    ]
                },
            ),
            StreamChunk(
                call_id="c",
                chunk_type="stop",
                payload={"usage": {"input_tokens": 1, "output_tokens": 1}},
            ),
        ],
    )
    session = ChatSession(tools_enabled=True)
    manager = TurnManager(
        provider, model="m", tool_registry=default_tool_registry(tmp_path, tmp_path / "trust.json")
    )
    result = await manager.run_turn(
        session, "create", cancellation_token=never_cancelled(), stream=True
    )
    assert result.content == "Done"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "x"


@pytest.mark.asyncio
async def test_agent_loop_completes_simple_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = Provider(
        [
            response(
                "create",
                finish="tool_use",
                tool_calls=[
                    {"name": "create_file", "args": {"path": "hello.txt", "content": "hi"}}
                ],
            ),
            response("Done. Created hello.txt."),
        ]
    )
    session = ChatSession(tools_enabled=True)
    manager = TurnManager(
        provider, model="m", tool_registry=default_tool_registry(tmp_path, tmp_path / "trust.json")
    )
    result = await AgentLoop(manager, session).run("create hello", never_cancelled())
    assert result.degraded is False
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hi"


@pytest.mark.asyncio
async def test_agent_loop_respects_max_turns():
    provider = Provider(
        [response("again", finish="tool_use", tool_calls=[{"name": "missing", "args": {}}])] * 3
    )
    session = ChatSession(tools_enabled=False)
    manager = TurnManager(provider, model="m")
    result = await AgentLoop(manager, session, max_turns=1).run("loop", never_cancelled())
    assert result.degraded is True
    assert result.degraded_reason == "max_turns_reached"


@pytest.mark.asyncio
async def test_agent_loop_cancellation_preserves_state():
    provider = Provider([response("nope")])
    session = ChatSession(tools_enabled=True)
    manager = TurnManager(provider, model="m")
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    with pytest.raises(Exception):
        await AgentLoop(manager, session).run("task", token)
    assert any(message["role"] == "system" for message in session.history)
