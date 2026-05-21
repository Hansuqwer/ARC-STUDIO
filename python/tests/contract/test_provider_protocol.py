from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import never_cancelled
from agent_runtime_cockpit.providers import (
    CostRates,
    ProviderCapability,
    ProviderClient,
    ProviderFeature,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    StreamChunk,
    UsageRecord,
    validate_provider_id,
)


class MockProvider:
    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="mock-provider",
            provider_name="Mock Provider",
            supported_models=["mock-1"],
            default_model="mock-1",
            features=[ProviderFeature.STREAMING],
            max_context_tokens=8192,
            cost_rates={"mock-1": CostRates(input_per_million=1.0, output_per_million=2.0)},
        )

    async def complete(self, request: ProviderRequest, *, cancellation_token) -> ProviderResponse:
        cancellation_token.raise_if_cancelled()
        return ProviderResponse(
            call_id=request.call_id,
            model=request.model,
            content="ok",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
        )

    async def stream(self, request: ProviderRequest, *, cancellation_token) -> AsyncIterator[StreamChunk]:
        cancellation_token.raise_if_cancelled()
        yield StreamChunk(call_id=request.call_id, chunk_type="start")
        yield StreamChunk(call_id=request.call_id, chunk_type="delta", delta="ok")
        yield StreamChunk(call_id=request.call_id, chunk_type="stop")

    async def cancel(self, call_id: str) -> None:
        return None


@pytest.mark.asyncio
async def test_mock_provider_satisfies_runtime_protocol() -> None:
    provider = MockProvider()
    assert isinstance(provider, ProviderClient)
    request = ProviderRequest(
        model="mock-1",
        messages=[ProviderMessage(role="user", content="hello")],
        max_tokens=8,
    )
    response = await provider.complete(request, cancellation_token=never_cancelled())
    assert response.content == "ok"
    chunks = [chunk async for chunk in provider.stream(request, cancellation_token=never_cancelled())]
    assert [chunk.chunk_type for chunk in chunks] == ["start", "delta", "stop"]


def test_provider_capability_validates_default_model_and_rates() -> None:
    with pytest.raises(ValueError, match="default_model"):
        ProviderCapability(
            provider_id="mock-provider",
            provider_name="Mock Provider",
            supported_models=["mock-1"],
            default_model="missing",
            max_context_tokens=8192,
            cost_rates={"mock-1": CostRates(input_per_million=1.0, output_per_million=2.0)},
        )
    with pytest.raises(ValueError, match="cost_rates"):
        ProviderCapability(
            provider_id="mock-provider",
            provider_name="Mock Provider",
            supported_models=["mock-1"],
            default_model="mock-1",
            max_context_tokens=8192,
            cost_rates={},
        )


def test_validate_provider_id_contract() -> None:
    assert validate_provider_id("anthropic") == "anthropic"
    assert validate_provider_id("ollama-local") == "ollama-local"
    with pytest.raises(ValueError):
        validate_provider_id("Bad Provider")
