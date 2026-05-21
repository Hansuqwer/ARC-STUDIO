from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken, never_cancelled
from agent_runtime_cockpit.provider_clients import (
    AnthropicClient,
    CancelledError,
    ProviderFeature,
    ProviderMessage,
    ProviderRequest,
    RateLimitError,
)


class _Messages:
    def __init__(self, response=None, stream=None, error=None) -> None:
        self.response = response
        self.stream_response = stream
        self.error = error
        self.create_kwargs = None
        self.stream_kwargs = None

    def create(self, **kwargs):
        self.create_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response

    def stream(self, **kwargs):
        self.stream_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.stream_response


class _Stream:
    def __init__(self, events) -> None:
        self.events = events

    def __enter__(self):
        return iter(self.events)

    def __exit__(self, *_args):
        return False


class _Sdk:
    def __init__(self, messages: _Messages) -> None:
        self.messages = messages


def _request() -> ProviderRequest:
    return ProviderRequest(
        model="claude-sonnet-4-6",
        messages=[
            ProviderMessage(role="system", content="be concise", trust="system"),
            ProviderMessage(role="user", content="hello", trust="user"),
        ],
        max_tokens=32,
    )


@pytest.mark.asyncio
async def test_complete_maps_response_and_usage() -> None:
    response = SimpleNamespace(
        model="claude-sonnet-4-6",
        content=[SimpleNamespace(text="hello back")],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=4,
            cache_creation_input_tokens=2,
            cache_read_input_tokens=3,
        ),
    )
    messages = _Messages(response=response)
    client = AnthropicClient(sdk_factory=lambda: _Sdk(messages))

    result = await client.complete(_request(), cancellation_token=never_cancelled())

    assert result.content == "hello back"
    assert result.finish_reason == "stop"
    assert result.usage.input_tokens == 10
    assert result.usage.cache_creation_input_tokens == 2
    assert messages.create_kwargs["system"] == "be concise"
    assert messages.create_kwargs["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.asyncio
async def test_complete_missing_usage_returns_degraded_response() -> None:
    response = SimpleNamespace(model="claude-sonnet-4-6", content=[SimpleNamespace(text="ok")], stop_reason="end_turn")
    client = AnthropicClient(sdk_factory=lambda: _Sdk(_Messages(response=response)))

    result = await client.complete(_request(), cancellation_token=never_cancelled())

    assert result.degraded is True
    assert result.usage.available is False
    assert result.degraded_reason == "provider usage data unavailable"


@pytest.mark.asyncio
async def test_stream_yields_start_delta_stop() -> None:
    events = [
        SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="he")),
        SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(text="llo")),
        SimpleNamespace(type="message_delta", usage=SimpleNamespace(input_tokens=1, output_tokens=2)),
    ]
    messages = _Messages(stream=_Stream(events))
    client = AnthropicClient(sdk_factory=lambda: _Sdk(messages))

    chunks = [chunk async for chunk in client.stream(_request(), cancellation_token=never_cancelled())]

    assert [chunk.chunk_type for chunk in chunks] == ["start", "delta", "delta", "stop"]
    assert "hello" == chunks[1].delta + chunks[2].delta
    assert chunks[-1].payload["usage"]["input_tokens"] == 1
    assert messages.stream_kwargs["stream"] is True


@pytest.mark.asyncio
async def test_cancelled_token_maps_to_provider_cancelled_error() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    client = AnthropicClient(sdk_factory=lambda: _Sdk(_Messages()))

    with pytest.raises(CancelledError):
        await client.complete(_request(), cancellation_token=token)


@pytest.mark.asyncio
async def test_rate_limit_error_is_mapped() -> None:
    class RateLimitAPIError(Exception):
        pass

    client = AnthropicClient(sdk_factory=lambda: _Sdk(_Messages(error=RateLimitAPIError("rate limit"))))

    with pytest.raises(RateLimitError):
        await client.complete(_request(), cancellation_token=never_cancelled())


def test_capabilities_include_streaming_and_prompt_caching() -> None:
    capability = AnthropicClient(sdk_factory=lambda: _Sdk(_Messages())).capabilities()
    assert capability.provider_id == "anthropic"
    assert capability.supports(ProviderFeature.STREAMING)
    assert capability.supports(ProviderFeature.PROMPT_CACHING)
