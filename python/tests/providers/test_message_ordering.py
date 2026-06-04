"""P0-1: byte-stable message ordering for provider prefix caching."""

from __future__ import annotations

from agent_runtime_cockpit.providers.base import ProviderMessage, ProviderRequest
from agent_runtime_cockpit.providers.openai_compatible import OpenAICompatibleClient


def _req(roles_and_content: list[tuple[str, str]], tools: list | None = None) -> ProviderRequest:
    msgs = [ProviderMessage(role=r, content=c, trust="user") for r, c in roles_and_content]
    return ProviderRequest(
        model="gpt-4o-mini",
        messages=msgs,
        max_tokens=100,
        temperature=0.0,
        tools=tools or [],
    )


def _client() -> OpenAICompatibleClient:
    return OpenAICompatibleClient(vendor="openai")


def _kwargs(req: ProviderRequest) -> dict:
    return _client()._request_kwargs(req, stream=False)


# ── OpenAI ordering ────────────────────────────────────────────────────────


def test_openai_system_first() -> None:
    req = _req([("user", "hello"), ("system", "You are helpful."), ("user", "world")])
    messages = _kwargs(req)["messages"]
    assert messages[0]["role"] == "system"


def test_openai_tools_passed_separately_not_in_messages() -> None:
    tools = [{"name": "bash", "description": "run shell", "input_schema": {}}]
    req = _req([("system", "sys"), ("user", "hi")], tools=tools)
    kw = _kwargs(req)
    # tools are in kwargs["tools"], not embedded in messages
    for msg in kw["messages"]:
        assert msg.get("role") != "tool_definitions"
    assert len(kw["tools"]) == 1


def test_byte_stable_across_two_calls_same_session() -> None:
    req = _req([("system", "sys"), ("user", "turn1"), ("assistant", "reply1"), ("user", "turn2")])
    kw1 = _kwargs(req)
    kw2 = _kwargs(req)
    assert kw1["messages"] == kw2["messages"]


def test_new_tool_appended_not_inserted() -> None:
    """Adding a tool must not reorder existing tools (cache stability)."""
    tools_v1 = [{"name": "bash", "description": "run", "input_schema": {}}]
    tools_v2 = [
        {"name": "bash", "description": "run", "input_schema": {}},
        {"name": "read_file", "description": "read", "input_schema": {}},
    ]
    req1 = _req([("user", "hi")], tools=tools_v1)
    req2 = _req([("user", "hi")], tools=tools_v2)
    kw1 = _kwargs(req1)
    kw2 = _kwargs(req2)
    # First tool unchanged between v1 and v2
    assert kw1["tools"][0]["function"]["name"] == kw2["tools"][0]["function"]["name"]
    # New tool appended at end
    assert kw2["tools"][-1]["function"]["name"] == "read_file"


# ── Anthropic ordering ─────────────────────────────────────────────────────


def test_anthropic_system_block_set_before_messages() -> None:
    from agent_runtime_cockpit.providers.anthropic import AnthropicClient

    client = AnthropicClient.__new__(AnthropicClient)
    req = ProviderRequest(
        model="claude-3-haiku-20240307",
        messages=[
            ProviderMessage(role="system", content="You are helpful.", trust="system"),
            ProviderMessage(role="user", content="Hello", trust="user"),
        ],
        max_tokens=100,
        temperature=0.0,
    )
    kw = client._request_kwargs(req, stream=False)
    # system always set as a top-level key, not inside messages
    assert "system" in kw
    for msg in kw["messages"]:
        assert msg.get("role") != "system"
