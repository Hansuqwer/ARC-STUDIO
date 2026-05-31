"""Paid-call gate wrapper for provider-backed execution.

``provider_backed`` runs whatever Provider is injected and does not, by itself,
apply a cost gate (that is intentional: offline providers like ``EchoProvider``
should run freely). When wrapping a *paid* provider (e.g. an HTTP API), wrap it
in :class:`GatedProvider` so a call is denied unless explicitly allowed.

The wrapper implements the :class:`swarmgraph.providers.Provider` protocol, so it
is a drop-in for ``SwarmGraphRunner(provider=...)``. ``capabilities()`` always
passes through; only ``complete()`` is gated.
"""

from __future__ import annotations

from ..providers import (
    CancellationTokenLike,
    Provider,
    ProviderCapability,
    ProviderRequest,
    ProviderResponse,
)


class PaidCallDeniedError(RuntimeError):
    """Raised when a gated provider call is attempted while disallowed."""


class GatedProvider:
    """Wrap a provider so ``complete()`` requires explicit allowance.

    Args:
        inner: The wrapped provider (e.g. ``HTTPChatProvider``).
        allow_paid_calls: When False (default), ``complete()`` raises
            :class:`PaidCallDeniedError` without invoking the inner provider.
    """

    def __init__(self, inner: Provider, *, allow_paid_calls: bool = False) -> None:
        self._inner = inner
        self._allow_paid_calls = allow_paid_calls

    @property
    def allow_paid_calls(self) -> bool:
        return self._allow_paid_calls

    def capabilities(self) -> ProviderCapability:
        return self._inner.capabilities()

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationTokenLike,
    ) -> ProviderResponse:
        if not self._allow_paid_calls:
            provider_id = self._inner.capabilities().provider_id
            raise PaidCallDeniedError(
                f"paid provider calls denied for {provider_id!r}; "
                "wrap with GatedProvider(allow_paid_calls=True) to enable"
            )
        return await self._inner.complete(request, cancellation_token=cancellation_token)
