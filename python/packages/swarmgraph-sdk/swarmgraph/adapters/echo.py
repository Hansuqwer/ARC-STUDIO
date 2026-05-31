"""Deterministic, offline echo provider.

Implements the :class:`swarmgraph.providers.Provider` protocol without any
external dependency. Useful for SDK demos and tests: given a request, it returns
the content of the last user message (optionally prefixed), with zero cost and
zero token usage. It honours the cancellation token contract.
"""

from __future__ import annotations

from ..providers import (
    CancellationTokenLike,
    ProviderCapability,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)

_DEFAULT_MODEL = "echo-1"


class EchoProvider:
    """A deterministic provider that echoes the last user message.

    Args:
        prefix: Optional string prepended to the echoed content.
        model: Model identifier reported via ``capabilities()``.
    """

    def __init__(self, *, prefix: str = "echo: ", model: str = _DEFAULT_MODEL) -> None:
        self._prefix = prefix
        self._model = model

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="swarmgraph.echo",
            provider_name="SwarmGraph Echo",
            supported_models=[self._model],
            default_model=self._model,
            max_context_tokens=8192,
            cost_rates={},
        )

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationTokenLike,
    ) -> ProviderResponse:
        cancellation_token.raise_if_cancelled()
        user_messages = [m for m in request.messages if m.role == "user"]
        last = user_messages[-1].content if user_messages else ""
        content = f"{self._prefix}{last}"
        return ProviderResponse(
            call_id=request.call_id,
            model=request.model or self._model,
            content=content,
            finish_reason="stop",
            usage=UsageRecord(available=True, input_tokens=0, output_tokens=0),
        )
