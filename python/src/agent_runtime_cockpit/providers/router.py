"""Multi-provider router — gated default-off (ARC_ENABLE_PROVIDER_ROUTER=1)."""

from __future__ import annotations

import os
from typing import Awaitable, Callable, TypeVar

from .base import ProviderError

T = TypeVar("T")

ENABLED = os.getenv("ARC_ENABLE_PROVIDER_ROUTER", "").lower() in ("1", "true")


class ProviderRouter:
    """Cascading failover across an ordered list of provider callables.

    Only activated when ARC_ENABLE_PROVIDER_ROUTER=1.
    Wiring into turn_manager is a follow-on slice.
    """

    def __init__(self, providers: list[Callable[[], Awaitable[T]]]) -> None:
        self._providers = providers

    async def call(self) -> T:
        last_exc: Exception | None = None
        for provider_fn in self._providers:
            try:
                return await provider_fn()
            except ProviderError as exc:
                if not exc.retryable:
                    raise
                last_exc = exc
        raise last_exc or RuntimeError("ProviderRouter: no providers configured")
