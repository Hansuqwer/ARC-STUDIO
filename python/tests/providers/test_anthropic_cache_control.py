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
    )


class TestSystemCacheControl:
    def test_system_without_cache_control_is_plain_string(self):
        """Without cache control, system prompt is a plain string."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(system_prompt="be concise"),
            stream=False,
        )
        assert kwargs["system"] == "be concise"
        assert isinstance(kwargs["system"], str)

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
