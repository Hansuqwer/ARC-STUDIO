"""Multi-provider failover client (R-OPEN-HARDEN slice 4).

FallbackProviderClient wraps an ordered list of ProviderClients. On a *retryable*
ProviderError from one provider, it fails over to the next. Non-retryable errors
(AuthError, ValidationError, etc.) propagate immediately — failing over on a bad
API key or malformed request would not help.

Opt-in and additive: nothing constructs this by default. To use it, build it
explicitly with a primary + fallbacks and pass it as the TurnManager provider.

Composition note: if used as a TurnManager provider, the manager's _call_with_retry
wraps the whole chain, so a fully-failed chain is retried (retry-of-failover). That
is correct but means the primary may be tried again across retry rounds. For a
single failover pass, call complete() directly.

Streaming failover honors the same correctness boundary as the streaming retry
(Phase 124): once a chunk is emitted, no failover — switching providers mid-stream
would duplicate/diverge the output already shown.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from .base import (
    ProviderCapability,
    ProviderClient,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
)
from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken

log = logging.getLogger(__name__)


class FallbackProviderClient:
    """A ProviderClient that fails over across an ordered list of providers."""

    def __init__(self, clients: list[ProviderClient]) -> None:
        if not clients:
            raise ValueError("FallbackProviderClient requires at least one client")
        self._clients = clients

    def capabilities(self) -> ProviderCapability:
        # Report the primary's capabilities.
        return self._clients[0].capabilities()

    async def complete(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> ProviderResponse:
        last_exc: ProviderError | None = None
        for index, client in enumerate(self._clients):
            try:
                return await client.complete(request, cancellation_token=cancellation_token)
            except ProviderError as exc:
                if not exc.retryable:
                    # Non-retryable (auth/validation) — failover won't help.
                    raise
                last_exc = exc
                log.info(
                    "provider %d/%d failed (%s); failing over",
                    index + 1,
                    len(self._clients),
                    type(exc).__name__,
                )
        # All providers exhausted on retryable errors.
        raise last_exc  # type: ignore[misc]

    async def stream(
        self,
        request: ProviderRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> AsyncIterator[StreamChunk]:
        last_exc: ProviderError | None = None
        for index, client in enumerate(self._clients):
            emitted = False
            try:
                async for chunk in client.stream(request, cancellation_token=cancellation_token):
                    emitted = True
                    yield chunk
                return
            except ProviderError as exc:
                # Once a chunk is emitted, never fail over — would duplicate output.
                if emitted or not exc.retryable:
                    raise
                last_exc = exc
                log.info(
                    "provider %d/%d stream failed pre-chunk (%s); failing over",
                    index + 1,
                    len(self._clients),
                    type(exc).__name__,
                )
        raise last_exc  # type: ignore[misc]

    async def cancel(self, call_id: str) -> None:
        # Best-effort cancel across all providers.
        for client in self._clients:
            try:
                await client.cancel(call_id)
            except Exception:  # noqa: BLE001 — cancel is best-effort
                pass
