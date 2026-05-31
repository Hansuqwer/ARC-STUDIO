from __future__ import annotations

import pytest

from swarmgraph.adapters import EchoProvider, HTTPChatProvider
from swarmgraph.providers import ProviderMessage, ProviderRequest


class _NeverCancelled:
    is_cancelled = False

    def raise_if_cancelled(self) -> None:
        return None


_TOKEN = _NeverCancelled()


def _request(content: str) -> ProviderRequest:
    return ProviderRequest(
        model="echo-1",
        messages=[ProviderMessage(role="user", content=content)],
    )


@pytest.mark.asyncio
async def test_echo_provider_is_deterministic_and_offline() -> None:
    provider = EchoProvider()
    caps = provider.capabilities()
    assert caps.provider_id == "swarmgraph.echo"

    response = await provider.complete(_request("hello"), cancellation_token=_TOKEN)
    assert response.content == "echo: hello"
    assert response.finish_reason == "stop"
    assert response.usage.input_tokens == 0
    assert response.usage.output_tokens == 0


@pytest.mark.asyncio
async def test_http_chat_provider_requires_transport() -> None:
    provider = HTTPChatProvider(base_url="https://api.example.com/v1", model="gpt-test")
    with pytest.raises(RuntimeError, match="no transport"):
        await provider.complete(_request("hi"), cancellation_token=_TOKEN)


@pytest.mark.asyncio
async def test_http_chat_provider_uses_injected_transport() -> None:
    captured: dict[str, object] = {}

    async def fake_transport(url, headers, json_body):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json_body
        return {
            "model": "gpt-test",
            "choices": [
                {"message": {"role": "assistant", "content": "pong"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        }

    provider = HTTPChatProvider(
        base_url="https://api.example.com/v1/",
        model="gpt-test",
        api_key="secret",
        transport=fake_transport,
    )

    response = await provider.complete(_request("ping"), cancellation_token=_TOKEN)

    assert response.content == "pong"
    assert response.model == "gpt-test"
    assert response.usage.input_tokens == 3
    assert response.usage.output_tokens == 1
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer secret"


def test_http_chat_provider_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        HTTPChatProvider(base_url="", model="x")
