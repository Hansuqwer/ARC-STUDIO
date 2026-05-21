"""Tests for Anthropic cache-control wire format."""

from __future__ import annotations

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

    def test_context_cache_control_wraps_last_message_content(self):
        """With context breakpoint, last message content becomes a block list."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(
                user_message="long context here",
                cache_control=[
                    CacheBreakpoint(position="system", index=0),
                    CacheBreakpoint(position="context", index=0),
                ],
            ),
            stream=False,
        )
        last = kwargs["messages"][-1]
        assert isinstance(last["content"], list)
        block = last["content"][0]
        assert block["type"] == "text"
        assert block["text"] == "long context here"
        assert block["cache_control"]["type"] == "ephemeral"

    def test_messages_cache_control_applied_to_last_message(self):
        """Cache control at 'messages' position wraps the last message."""
        client = AnthropicClient()
        kwargs = client._request_kwargs(
            _request(
                user_message="final message",
                cache_control=[CacheBreakpoint(position="messages", index=0)],
            ),
            stream=False,
        )
        last = kwargs["messages"][-1]
        assert isinstance(last["content"], list)
        assert last["content"][0]["cache_control"]["type"] == "ephemeral"

    def test_multiple_messages_only_last_gets_cache(self):
        """Only the last message gets cache control, others stay as strings."""
        messages = [
            ProviderMessage(role="user", content="first", trust="user"),
            ProviderMessage(role="assistant", content="response", trust="workspace"),
            ProviderMessage(role="user", content="second", trust="user"),
        ]
        request = ProviderRequest(
            model="claude-sonnet-4-6",
            messages=messages,
            max_tokens=32,
            cache_control=[CacheBreakpoint(position="context", index=0)],
        )
        client = AnthropicClient()
        kwargs = client._request_kwargs(request, stream=False)
        # Only the last message should have content as a list
        assert kwargs["messages"][0]["content"] == "first"
        assert kwargs["messages"][1]["content"] == "response"
        assert isinstance(kwargs["messages"][2]["content"], list)


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
