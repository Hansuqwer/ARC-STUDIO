"""Contract test for ProviderClient implementations."""

from __future__ import annotations

from typing import AsyncIterator

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.providers.base import (
    CostRates,
    ProviderCapability,
    ProviderClient,
    ProviderFeature,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
    UsageRecord,
)


class _FakeProviderClient:
    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="fake",
            provider_name="Fake Provider",
            supported_models=["fake-model"],
            default_model="fake-model",
            features=[ProviderFeature.STREAMING],
            max_context_tokens=100_000,
            cost_rates={"fake-model": CostRates(input_per_million=1.0, output_per_million=2.0)},
        )

    async def complete(
        self, request: ProviderRequest, *, cancellation_token: CancellationToken
    ) -> ProviderResponse:
        return ProviderResponse(
            call_id=request.call_id,
            model=request.model,
            content="ok",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=10, output_tokens=5),
        )

    async def stream(
        self, request: ProviderRequest, *, cancellation_token: CancellationToken
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(call_id=request.call_id, chunk_type="start")
        yield StreamChunk(call_id=request.call_id, chunk_type="delta", delta="ok")
        yield StreamChunk(call_id=request.call_id, chunk_type="stop")

    async def cancel(self, call_id: str) -> None:
        pass


def test_fake_implements_protocol():
    assert isinstance(_FakeProviderClient(), ProviderClient)


def test_fake_capabilities_round_trip():
    caps = _FakeProviderClient().capabilities()
    assert caps.provider_id == "fake"
    assert ProviderFeature.STREAMING in caps.features


def test_registry_has_anthropic():
    """Test that AnthropicClient is auto-registered."""
    from agent_runtime_cockpit.providers.registry import known

    assert "anthropic" in known()
