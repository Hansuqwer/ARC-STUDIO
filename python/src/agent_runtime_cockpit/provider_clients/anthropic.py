"""Anthropic ProviderClient implementation skeleton.

The client is dependency-injected/testable and imports the Anthropic SDK lazily
so default test suites never require credentials or make network calls.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, AsyncIterator

from agent_runtime_cockpit.cli_repl.cancellation import Cancelled, CancellationToken

from .base import (
    AuthError,
    CancelledError,
    CostRates,
    ModelError,
    NetworkError,
    ProviderCapability,
    ProviderFeature,
    ProviderRequest,
    ProviderResponse,
    RateLimitError,
    StreamChunk,
    UsageRecord,
    ValidationError,
)


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"


class AnthropicClient:
    def __init__(self, *, sdk_factory: Callable[[], Any] | None = None) -> None:
        self._sdk_factory = sdk_factory
        self._client: Any | None = None
        self._cancelled_calls: set[str] = set()

    def capabilities(self) -> ProviderCapability:
        model = os.environ.get("ARC_ANTHROPIC_DEFAULT_MODEL", DEFAULT_ANTHROPIC_MODEL)
        timeout = int(os.environ.get("ARC_ANTHROPIC_TIMEOUT_SECONDS", "60"))
        return ProviderCapability(
            provider_id="anthropic",
            provider_name="Anthropic",
            supported_models=[model],
            default_model=model,
            features=[ProviderFeature.STREAMING, ProviderFeature.PROMPT_CACHING, ProviderFeature.TOOL_USE, ProviderFeature.SYSTEM_PROMPT],
            max_context_tokens=200_000,
            cost_rates={
                model: CostRates(
                    input_per_million=3.0,
                    output_per_million=15.0,
                    cache_write_per_million=3.75,
                    cache_read_per_million=0.30,
                )
            },
            timeout_seconds=timeout,
        )

    async def complete(self, request: ProviderRequest, *, cancellation_token: CancellationToken) -> ProviderResponse:
        try:
            cancellation_token.raise_if_cancelled()
            response = self._client_instance().messages.create(**self._request_kwargs(request, stream=False))
            cancellation_token.raise_if_cancelled()
        except Cancelled as exc:
            raise CancelledError(str(exc)) from exc
        except Exception as exc:  # provider SDK types are optional at import time
            raise self._map_error(exc) from exc
        return ProviderResponse(
            call_id=request.call_id,
            model=str(getattr(response, "model", request.model)),
            content=self._extract_content(response),
            finish_reason=self._finish_reason(getattr(response, "stop_reason", None)),
            usage=self._usage_record(getattr(response, "usage", None)),
            degraded=getattr(response, "usage", None) is None,
            degraded_reason=None if getattr(response, "usage", None) is not None else "provider usage data unavailable",
        )

    async def stream(self, request: ProviderRequest, *, cancellation_token: CancellationToken) -> AsyncIterator[StreamChunk]:
        try:
            cancellation_token.raise_if_cancelled()
            yield StreamChunk(call_id=request.call_id, chunk_type="start")
            stream = self._client_instance().messages.stream(**self._request_kwargs(request, stream=True))
            usage: UsageRecord | None = None
            with stream as events:
                for event in events:
                    cancellation_token.raise_if_cancelled()
                    event_type = getattr(event, "type", "")
                    if event_type == "content_block_delta":
                        delta = getattr(getattr(event, "delta", None), "text", "")
                        if delta:
                            yield StreamChunk(call_id=request.call_id, chunk_type="delta", delta=str(delta))
                    elif event_type == "message_delta":
                        usage = self._usage_record(getattr(event, "usage", None))
            yield StreamChunk(call_id=request.call_id, chunk_type="stop", payload={"usage": usage.model_dump(mode="json") if usage else None})
        except Cancelled as exc:
            raise CancelledError(str(exc)) from exc
        except Exception as exc:
            yield StreamChunk(call_id=request.call_id, chunk_type="error", payload={"error": str(self._map_error(exc))})

    async def cancel(self, call_id: str) -> None:
        self._cancelled_calls.add(call_id)

    def _client_instance(self) -> Any:
        if self._client is None:
            if self._sdk_factory is not None:
                self._client = self._sdk_factory()
            else:
                try:
                    from anthropic import Anthropic
                except ImportError as exc:
                    raise AuthError("anthropic SDK is not installed") from exc
                self._client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"), timeout=self.capabilities().timeout_seconds)
        return self._client

    def _request_kwargs(self, request: ProviderRequest, *, stream: bool) -> dict[str, Any]:
        system = [message.content for message in request.messages if message.role == "system"]
        messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
            if message.role != "system"
        ]
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if system:
            kwargs["system"] = "\n\n".join(system)
        if request.stop_sequences:
            kwargs["stop_sequences"] = request.stop_sequences
        if request.tools:
            kwargs["tools"] = request.tools
        if stream:
            kwargs["stream"] = True
        return kwargs

    @staticmethod
    def _extract_content(response: Any) -> str:
        parts: list[str] = []
        for block in getattr(response, "content", []) or []:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
        return "".join(parts)

    @staticmethod
    def _usage_record(usage: Any) -> UsageRecord:
        if usage is None:
            return UsageRecord(available=False, input_tokens=0, output_tokens=0)
        return UsageRecord(
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cache_creation_input_tokens=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
            cache_read_input_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        )

    @staticmethod
    def _finish_reason(stop_reason: Any) -> str:
        mapping = {"end_turn": "stop", "max_tokens": "length", "tool_use": "tool_use"}
        return mapping.get(str(stop_reason), "stop")

    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        name = type(exc).__name__.lower()
        text = str(exc)
        if "rate" in name or "rate" in text.lower():
            return RateLimitError(text)
        if "auth" in name or "401" in text or "api key" in text.lower():
            return AuthError(text)
        if "validation" in name or "400" in text:
            return ValidationError(text)
        if "connection" in name or "network" in name or "timeout" in name:
            return NetworkError(text)
        return ModelError(text)
