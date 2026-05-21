"""Anthropic ProviderClient implementation skeleton.

The client is dependency-injected/testable and imports the Anthropic SDK lazily
so default test suites never require credentials or make network calls.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any, AsyncIterator

from agent_runtime_cockpit.cli_repl.cancellation import Cancelled, CancellationToken
from agent_runtime_cockpit.protocol.cost_record import CostRecord

from .anthropic_cost import extract_cost
from .anthropic_estimator import build_estimate_fn, select_estimator
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
_ANTHROPIC_MAX_BREAKPOINTS = 4


class AnthropicClient:
    def __init__(self, *, sdk_factory: Callable[[], Any] | None = None) -> None:
        self._sdk_factory = sdk_factory
        self._client: Any | None = None
        self._cancelled_calls: set[str] = set()
        self._last_request_kwargs: dict[str, Any] | None = None
        self._last_estimate_fn: Callable[[], tuple[int, int]] | None = None

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

    def extract_cost(
        self,
        response: ProviderResponse,
        *,
        estimate_fn: Callable[[], tuple[int, int]] | None = None,
    ) -> CostRecord:
        """Extract a ``CostRecord`` from a completed provider response.

        Uses the model's cost rates from :meth:`capabilities` to compute
        the USD cost of the call.

        Args:
            response: A ``ProviderResponse`` returned by :meth:`complete`.
            estimate_fn: Optional callable that returns ``(input_tokens,
                output_tokens)`` for the degraded path. When provided,
                replaces the hardcoded 100/32 fallback with a real
                tokenizer-based estimate. Built automatically by
                :meth:`complete` when the response is degraded; if not
                provided and the response is degraded, falls back to
                ``self._last_estimate_fn`` (set by the most recent
                :meth:`complete` call).

        Returns:
            A ``CostRecord`` with ``source="measured"`` when usage data is
            available, ``"estimated"`` otherwise.

        Raises:
            CostExtractionError: If the response model is not found in
                cost rates.
        """
        fn = estimate_fn or self._last_estimate_fn
        return extract_cost(response, self.capabilities(), estimate_fn=fn)

    async def complete(self, request: ProviderRequest, *, cancellation_token: CancellationToken) -> ProviderResponse:
        try:
            cancellation_token.raise_if_cancelled()
            kwargs = self._request_kwargs(request, stream=False)
            self._last_request_kwargs = kwargs
            response = self._client_instance().messages.create(**kwargs)
            cancellation_token.raise_if_cancelled()
        except Cancelled as exc:
            raise CancelledError(str(exc)) from exc
        except Exception as exc:  # provider SDK types are optional at import time
            raise self._map_error(exc) from exc
        provider_response = ProviderResponse(
            call_id=request.call_id,
            model=str(getattr(response, "model", request.model)),
            content=self._extract_content(response),
            finish_reason=self._finish_reason(getattr(response, "stop_reason", None)),
            usage=self._usage_record(getattr(response, "usage", None)),
            degraded=getattr(response, "usage", None) is None,
            degraded_reason=None if getattr(response, "usage", None) is not None else "provider usage data unavailable",
        )
        # If degraded, wire the estimator for subsequent extract_cost() calls
        if provider_response.degraded:
            try:
                estimator = select_estimator(
                    prefer_sdk=self._client is not None,
                    sdk_client=self._client,
                )
                messages = kwargs.get("messages", [])
                if messages:
                    self._last_estimate_fn = build_estimate_fn(
                        estimator,
                        messages,
                        model=provider_response.model,
                    )
                else:
                    self._last_estimate_fn = None
            except (ImportError, ValueError):
                self._last_estimate_fn = None
        return provider_response

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
        system_texts = [message.content for message in request.messages if message.role == "system"]
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
        if system_texts:
            kwargs["system"] = self._system_with_cache_control(system_texts, request.cache_control)
        if request.stop_sequences:
            kwargs["stop_sequences"] = request.stop_sequences
        if request.tools:
            kwargs["tools"] = request.tools
        if stream:
            kwargs["stream"] = True
        if request.cache_control:
            kwargs = self._apply_cache_breakpoints_to_request(kwargs, request.cache_control)
        return kwargs

    @staticmethod
    def _apply_cache_breakpoints_to_request(
        request_dict: dict[str, Any],
        cache_control: list,
    ) -> dict[str, Any]:
        """Apply all Anthropic cache breakpoints to a request dict.

        Enforces the Anthropic 4-breakpoint limit across system, tools, and
        messages combined.
        """
        if len(cache_control) > _ANTHROPIC_MAX_BREAKPOINTS:
            raise ValueError(
                f"Anthropic allows at most {_ANTHROPIC_MAX_BREAKPOINTS} cache breakpoints per request, "
                f"got {len(cache_control)}"
            )
        updated = dict(request_dict)
        has_tools_breakpoint = any(
            (hasattr(bp, "position") and bp.position == "tools")
            or (isinstance(bp, dict) and bp.get("position") == "tools")
            for bp in cache_control
        )
        if has_tools_breakpoint and updated.get("tools"):
            updated["tools"] = AnthropicClient._apply_tools_cache_control(updated["tools"])
        if "messages" in updated:
            updated["messages"] = AnthropicClient._apply_message_cache_control(
                updated["messages"],
                cache_control,
            )
        return updated

    @staticmethod
    def _apply_tools_cache_control(tools: list[dict]) -> list[dict]:
        """Apply Anthropic ephemeral cache_control to the tools block.

        Anthropic treats tools as a single cacheable block; the marker is
        placed on the last tool definition and caches all tools up to and
        including it.
        """
        if not tools:
            return tools
        annotated = [dict(tool) for tool in tools]
        annotated[-1] = {**annotated[-1], "cache_control": {"type": "ephemeral"}}
        return annotated

    @staticmethod
    def _system_with_cache_control(
        system_texts: list[str],
        cache_control: list,
    ) -> str | list[dict]:
        """Build the system parameter, optionally wrapping in a content block
        for cache control.

        When a system-position breakpoint is present, the system prompt must
        be sent as a content block list to attach ``cache_control``:
        ``[{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}]``
        """
        text = "\n\n".join(system_texts)
        has_system_cache = any(
            getattr(bp, "position", None) == "system"
            or (isinstance(bp, dict) and bp.get("position") == "system")
            for bp in cache_control
        )
        if has_system_cache:
            block: dict = {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}
            return [block]
        return text

    @staticmethod
    def _apply_message_cache_control(
        messages: list[dict],
        cache_control: list,
    ) -> list[dict]:
        """Apply cache control to specific message indices.

        Each ``CacheBreakpoint(position="messages", index=i)`` places a
        cache-control marker on ``messages[i]``. Anthropic caches all content
        up to and including each marked message.
        """
        if not cache_control:
            return messages
        message_breakpoints = [
            bp
            for bp in cache_control
            if (hasattr(bp, "position") and bp.position == "messages")
            or (isinstance(bp, dict) and bp.get("position") == "messages")
        ]
        if not message_breakpoints or not messages:
            return messages
        annotated = [dict(message) for message in messages]
        for bp in message_breakpoints:
            index = bp.index if hasattr(bp, "index") else bp.get("index", 0)
            if index >= len(annotated):
                raise ValueError(
                    f"CacheBreakpoint index={index} out of range for messages of length {len(annotated)}"
                )
            content = annotated[index]["content"]
            if isinstance(content, str):
                annotated[index]["content"] = [
                    {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}},
                ]
            elif isinstance(content, list) and content:
                content = [dict(block) if isinstance(block, dict) else block for block in content]
                last_block = content[-1]
                if isinstance(last_block, dict):
                    last_block["cache_control"] = {"type": "ephemeral"}
                annotated[index]["content"] = content
        return annotated

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
