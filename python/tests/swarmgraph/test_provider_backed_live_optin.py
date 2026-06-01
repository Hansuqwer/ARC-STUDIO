from __future__ import annotations

import os
from typing import Any

import pytest

from agent_runtime_cockpit.providers import registry
from agent_runtime_cockpit.providers.base import (
    ProviderRequest as ArcProviderRequest,
)
from swarmgraph.config import ExecutionMode, SwarmGraphConfig
from swarmgraph.providers import (
    CostRates,
    ProviderCapability,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from swarmgraph.runner import SwarmGraphRunner


_LIVE_GATE = "ARC_SWARMGRAPH_PROVIDER_E2E"
_PROVIDER_ENV = "ARC_SWARMGRAPH_PROVIDER"
_MODEL_ENV = "ARC_SWARMGRAPH_MODEL"


class _NeverCancelled:
    is_cancelled = False

    def raise_if_cancelled(self) -> None:
        return None


class _ArcProviderAdapter:
    """Test-only bridge from ARC ProviderClient to swarmgraph-sdk Provider."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model

    def capabilities(self) -> ProviderCapability:
        caps = self._client.capabilities()
        return ProviderCapability(
            provider_id=caps.provider_id,
            provider_name=caps.provider_name,
            supported_models=[self._model],
            default_model=self._model,
            max_context_tokens=caps.max_context_tokens,
            cost_rates={
                self._model: CostRates(
                    input_per_million=0.0,
                    output_per_million=0.0,
                )
            },
        )

    async def complete(self, request: ProviderRequest, *, cancellation_token) -> ProviderResponse:
        response = await self._client.complete(
            ArcProviderRequest(
                model=self._model,
                messages=[
                    ProviderMessage(role=message.role, content=message.content).model_dump()
                    for message in request.messages
                ],
                max_tokens=min(request.max_tokens, 64),
                temperature=request.temperature,
            ),
            cancellation_token=_NeverCancelled(),
        )
        return ProviderResponse(
            call_id=request.call_id,
            model=response.model,
            content=response.content,
            finish_reason=response.finish_reason,
            usage=UsageRecord(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_creation_input_tokens=response.usage.cache_creation_input_tokens,
                cache_read_input_tokens=response.usage.cache_read_input_tokens,
            ),
            degraded=response.degraded,
            degraded_reason=response.degraded_reason,
            tool_calls=response.tool_calls,
        )


def _live_enabled() -> bool:
    return os.environ.get(_LIVE_GATE) == "1"


def test_provider_backed_live_e2e_is_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_LIVE_GATE, raising=False)
    assert not _live_enabled()


@pytest.mark.skipif(
    not _live_enabled(),
    reason=f"set {_LIVE_GATE}=1 plus {_PROVIDER_ENV}/{_MODEL_ENV} for opt-in live provider smoke",
)
def test_provider_backed_live_e2e_opt_in_only() -> None:
    provider_name = os.environ.get(_PROVIDER_ENV, "9router")
    model = os.environ.get(_MODEL_ENV, "ag/gemini-3.5-flash-extra-low")
    client = registry.get(provider_name)
    provider = _ArcProviderAdapter(client, model)
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        num_workers=1,
        max_rounds=1,
        worker_timeout_seconds=30,
    )

    result = SwarmGraphRunner(config=config, provider=provider).run_result(
        "Reply with the single word: ok"
    )

    assert result.status == "completed"
    assert result.completed_tasks == 1
    assert result.results[0].output.strip()
