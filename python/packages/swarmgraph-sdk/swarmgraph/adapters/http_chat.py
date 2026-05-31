"""OpenAI-style HTTP chat-completions provider adapter.

This adapter shows the *shape* of an HTTP-backed provider while keeping the SDK
free of any concrete HTTP client dependency and free of surprise network calls:

- The caller injects an async ``transport`` callable. The adapter builds the
  request payload and parses the response, but never opens a socket itself.
- Without a transport, ``complete`` raises ``RuntimeError`` immediately, so it
  is impossible for tests to accidentally hit a live endpoint.

The transport contract is intentionally tiny so it can be backed by ``httpx``,
``aiohttp``, a recorded fixture, or an in-memory fake::

    async def transport(url: str, headers: dict, json_body: dict) -> dict:
        ...  # return the parsed JSON response body as a dict
"""

from __future__ import annotations

from typing import Any, Protocol

from ..providers import (
    CancellationTokenLike,
    CostRates,
    ProviderCapability,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)


class HTTPTransport(Protocol):
    """Async callable that performs the actual HTTP POST and returns JSON."""

    async def __call__(
        self,
        url: str,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> dict[str, Any]: ...


class HTTPChatProvider:
    """OpenAI-compatible chat-completions provider.

    Args:
        base_url: Endpoint base, e.g. ``https://api.example.com/v1``.
        model: Default model identifier.
        api_key: Optional bearer token included as ``Authorization`` header.
        transport: Async callable performing the request. Required for
            ``complete`` to succeed; omitted only for capability inspection.
        cost_rates: Optional per-model cost rates for cost accounting.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        transport: HTTPTransport | None = None,
        cost_rates: dict[str, CostRates] | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._transport = transport
        self._cost_rates = cost_rates or {}

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="swarmgraph.http_chat",
            provider_name="SwarmGraph HTTP Chat",
            supported_models=[self._model],
            default_model=self._model,
            max_context_tokens=128_000,
            cost_rates=self._cost_rates,
        )

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationTokenLike,
    ) -> ProviderResponse:
        cancellation_token.raise_if_cancelled()
        if self._transport is None:
            raise RuntimeError(
                "HTTPChatProvider has no transport configured; "
                "inject an async transport to perform requests"
            )

        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }

        body = await self._transport(
            f"{self._base_url}/chat/completions",
            headers,
            payload,
        )
        cancellation_token.raise_if_cancelled()
        return _parse_chat_response(body, request, self._model)


def _parse_chat_response(
    body: dict[str, Any],
    request: ProviderRequest,
    default_model: str,
) -> ProviderResponse:
    choices = body.get("choices") or []
    content = ""
    finish_reason = "stop"
    if choices:
        first = choices[0] or {}
        message = first.get("message") or {}
        content = str(message.get("content") or "")
        raw_reason = first.get("finish_reason") or "stop"
        finish_reason = raw_reason if raw_reason in _VALID_FINISH else "stop"

    usage_raw = body.get("usage") or {}
    usage = UsageRecord(
        available=bool(usage_raw),
        input_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
        output_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
    )

    return ProviderResponse(
        call_id=request.call_id,
        model=str(body.get("model") or request.model or default_model),
        content=content,
        finish_reason=finish_reason,  # type: ignore[arg-type]
        usage=usage,
    )


_VALID_FINISH = {"stop", "length", "tool_use", "content_filter", "cancelled", "error"}
