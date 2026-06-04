"""Tests for Anthropic cache-control wire format."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.providers.anthropic import AnthropicClient
from agent_runtime_cockpit.providers.base import CacheBreakpoint, ProviderMessage, ProviderRequest


def _request(
    cache_control: list | None = None,
    system_prompt: str | None = None,
    user_message: str = "hello",
    tools: list | None = None,
) -> ProviderRequest:
    messages = []
    if system_prompt:
        messages.append(ProviderMessage(role="system", content=system_prompt, trust="system"))
    messages.append(ProviderMessage(role="user", content=user_message, trust="user"))
    return ProviderRequest(
        model="claude-sonnet-4-6",
        messages=messages,
        max_tokens=32,
        cache_control=cache_control or [],
        tools=tools or [],
    )


class TestSystemCacheControl:
    def test_system_without_explicit_cache_control_gets_auto_breakpoint(self) -> None:
        """P0-2: auto-injection means system block always gets cache_control ephemeral."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(system_prompt="be concise"),
            stream=False,
        )
        assert isinstance(kwargs["system"], list)
        assert kwargs["system"][-1].get("cache_control") == {"type": "ephemeral"}

    def test_system_with_cache_control_is_content_block(self):
        """With system cache control, system prompt becomes a content block list."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(
                system_prompt="be concise",
                cache_control=[CacheBreakpoint(position="system", index=0)],
            ),
            stream=False,
        )
        assert isinstance(kwargs["system"], list)
        assert len(kwargs["system"]) == 1
        block = kwargs["system"][0]
        assert block["type"] == "text"
        assert block["text"] == "be concise"
        assert "cache_control" in block
        assert block["cache_control"]["type"] == "ephemeral"

    def test_system_multiple_texts_joined_with_cache(self):
        """Multiple system messages are joined and cached as one block."""
        messages = [
            ProviderMessage(role="system", content="rule 1", trust="system"),
            ProviderMessage(role="system", content="rule 2", trust="system"),
            ProviderMessage(role="user", content="hi", trust="user"),
        ]
        request = ProviderRequest(
            model="claude-sonnet-4-6",
            messages=messages,
            max_tokens=32,
            cache_control=[CacheBreakpoint(position="system", index=0)],
        )
        client = AnthropicClient()
        kwargs = client._request_kwargs(request, stream=False)
        block = kwargs["system"][0]
        assert block["text"] == "rule 1\n\nrule 2"


class TestMessageCacheControl:
    def test_no_cache_control_messages_are_plain_strings(self):
        """Without cache control, message content stays as plain strings."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(user_message="hello"),
            stream=False,
        )
        assert kwargs["messages"][-1]["content"] == "hello"

    def test_messages_breakpoint_applies_to_specified_index(self):
        messages = [
            ProviderMessage(role="user", content="first", trust="user"),
            ProviderMessage(role="assistant", content="second", trust="workspace"),
            ProviderMessage(role="user", content="third", trust="user"),
        ]
        request = ProviderRequest(
            model="claude-sonnet-4-6",
            messages=messages,
            max_tokens=32,
            cache_control=[CacheBreakpoint(position="messages", index=1)],
        )
        client = AnthropicClient()
        kwargs = client._request_kwargs(request, stream=False)
        assert kwargs["messages"][0]["content"] == "first"
        assert kwargs["messages"][1]["content"][0]["cache_control"] == {"type": "ephemeral"}
        assert kwargs["messages"][2]["content"] == "third"

    def test_multiple_message_breakpoints_apply_to_each_index(self):
        messages = [
            ProviderMessage(role="user", content="a", trust="user"),
            ProviderMessage(role="assistant", content="b", trust="workspace"),
            ProviderMessage(role="user", content="c", trust="user"),
            ProviderMessage(role="assistant", content="d", trust="workspace"),
        ]
        request = ProviderRequest(
            model="claude-sonnet-4-6",
            messages=messages,
            max_tokens=32,
            cache_control=[
                CacheBreakpoint(position="messages", index=0),
                CacheBreakpoint(position="messages", index=2),
            ],
        )
        client = AnthropicClient()
        kwargs = client._request_kwargs(request, stream=False)
        assert kwargs["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}
        assert kwargs["messages"][1]["content"] == "b"
        assert kwargs["messages"][2]["content"][0]["cache_control"] == {"type": "ephemeral"}
        assert kwargs["messages"][3]["content"] == "d"

    def test_message_breakpoint_out_of_range_raises(self):
        client = AnthropicClient()
        with pytest.raises(ValueError, match="out of range"):
            client._request_kwargs(
                _request(cache_control=[CacheBreakpoint(position="messages", index=5)]),
                stream=False,
            )

    def test_no_message_breakpoints_returns_messages_unchanged(self):
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(cache_control=[CacheBreakpoint(position="system", index=0)]),
            stream=False,
        )
        assert kwargs["messages"] == [{"role": "user", "content": "hello"}]

    def test_total_breakpoints_exceeding_four_raises(self):
        messages = [ProviderMessage(role="user", content=f"m{i}", trust="user") for i in range(5)]
        request = ProviderRequest(
            model="claude-sonnet-4-6",
            messages=messages,
            max_tokens=32,
            cache_control=[CacheBreakpoint(position="messages", index=i) for i in range(5)],
        )
        client = AnthropicClient()
        with pytest.raises(ValueError, match="at most 4 cache breakpoints"):
            client._request_kwargs(request, stream=False)

    def test_system_breakpoint_rejects_nonzero_index(self):
        with pytest.raises(ValidationError, match="requires index=0"):
            CacheBreakpoint(position="system", index=1)

    def test_tools_breakpoint_rejects_nonzero_index(self):
        with pytest.raises(ValidationError, match="requires index=0"):
            CacheBreakpoint(position="tools", index=2)


class TestToolsCacheControl:
    def test_tools_breakpoint_applies_cache_control_to_last_tool(self):
        request_dict = {
            "tools": [
                {"name": "tool_a", "description": "a"},
                {"name": "tool_b", "description": "b"},
                {"name": "tool_c", "description": "c"},
            ],
        }
        breakpoints = [CacheBreakpoint(position="tools", index=0)]
        result = AnthropicClient._apply_cache_breakpoints_to_request(request_dict, breakpoints)

        assert "cache_control" not in result["tools"][0]
        assert "cache_control" not in result["tools"][1]
        assert result["tools"][2]["cache_control"] == {"type": "ephemeral"}

    def test_no_tools_breakpoint_leaves_tools_unchanged(self):
        request_dict = {
            "tools": [{"name": "tool_a"}],
            "messages": [{"role": "user", "content": "x"}],
        }
        breakpoints = [CacheBreakpoint(position="messages", index=0)]
        result = AnthropicClient._apply_cache_breakpoints_to_request(request_dict, breakpoints)

        assert "cache_control" not in result["tools"][0]

    def test_tools_breakpoint_with_empty_tools_is_noop(self):
        request_dict = {"tools": []}
        breakpoints = [CacheBreakpoint(position="tools", index=0)]
        result = AnthropicClient._apply_cache_breakpoints_to_request(request_dict, breakpoints)
        assert result["tools"] == []

    def test_tools_breakpoint_without_tools_key_is_noop(self):
        request_dict = {}
        breakpoints = [CacheBreakpoint(position="tools", index=0)]
        result = AnthropicClient._apply_cache_breakpoints_to_request(request_dict, breakpoints)
        assert "tools" not in result


class TestStreamingPreserved:
    def test_cache_control_with_streaming(self):
        """Cache control works with streaming requests."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(
                system_prompt="be concise",
                cache_control=[CacheBreakpoint(position="system", index=0)],
            ),
            stream=True,
        )
        assert kwargs["stream"] is True
        assert isinstance(kwargs["system"], list)


class TestAutoBreakpointInjection:
    """P0-2: default breakpoints injected when caller doesn't set cache_control."""

    def test_system_block_gets_cache_control_by_default(self) -> None:
        client = AnthropicClient()
        kw = client._request_kwargs(_request(system_prompt="be concise"), stream=False)
        system = kw["system"]
        assert isinstance(system, list)
        assert system[-1].get("cache_control") == {"type": "ephemeral"}

    def test_last_tool_def_gets_cache_control_by_default(self) -> None:
        client = AnthropicClient()
        tools = [
            {"name": "bash", "description": "run", "input_schema": {}},
            {"name": "read", "description": "read file", "input_schema": {}},
        ]
        kw = client._request_kwargs(
            _request(system_prompt="sys", user_message="hi", tools=tools), stream=False
        )
        assert kw["tools"][-1].get("cache_control") == {"type": "ephemeral"}
        # First tool should NOT have cache_control (only last tool gets it)
        assert "cache_control" not in kw["tools"][0]

    def test_explicit_cache_control_not_overridden(self) -> None:
        client = AnthropicClient()
        explicit = [CacheBreakpoint(position="system", index=0)]
        kw = client._request_kwargs(
            _request(system_prompt="sys", cache_control=explicit), stream=False
        )
        # Explicit path: system is a content block list (from _system_with_cache_control)
        assert isinstance(kw["system"], list)

    def test_no_auto_injection_when_no_system_or_tools(self) -> None:
        client = AnthropicClient()
        kw = client._request_kwargs(_request(user_message="hello"), stream=False)
        # No system key set, no tools key set
        assert "system" not in kw
        assert kw.get("tools") is None or kw.get("tools") == []

    def test_idempotent_two_calls_same_input(self) -> None:
        client = AnthropicClient()
        req = _request(system_prompt="sys", user_message="hi")
        kw1 = client._request_kwargs(req, stream=False)
        kw2 = client._request_kwargs(req, stream=False)
        assert kw1["system"] == kw2["system"]
