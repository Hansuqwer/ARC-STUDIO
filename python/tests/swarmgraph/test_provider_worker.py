from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.providers.base import (
    CostRates,
    ProviderCapability,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from agent_runtime_cockpit.swarmgraph.config import ExecutionMode
from agent_runtime_cockpit.swarmgraph.models import SwarmTask
from agent_runtime_cockpit.swarmgraph.nodes import worker as worker_module
from agent_runtime_cockpit.swarmgraph.nodes.worker import worker_execute, worker_execute_async


class _Cost:
    cost_usd = Decimal("0.001")


class _FakeProvider:
    def __init__(self, response: ProviderResponse | None = None, error: Exception | None = None):
        self.request: ProviderRequest | None = None
        self.error = error
        self.response = response or ProviderResponse(
            call_id="call-test",
            model="test-model",
            content="real output",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=2, output_tokens=3),
        )

    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id="test-provider",
            provider_name="Test Provider",
            supported_models=["test-model"],
            default_model="test-model",
            max_context_tokens=4096,
            cost_rates={"test-model": CostRates(input_per_million=1.0, output_per_million=2.0)},
        )

    def extract_cost(self, _response: ProviderResponse) -> _Cost:
        return _Cost()

    async def complete(self, request: ProviderRequest, *, cancellation_token) -> ProviderResponse:
        cancellation_token.raise_if_cancelled()
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response


def test_gated_local_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "test-provider")
    monkeypatch.setattr(worker_module, "get_provider", lambda _provider_id: provider)

    task = SwarmTask(prompt="test prompt")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)

    assert result.error is None
    assert result.output == "real output"
    assert result.cost_usd == 0.001
    assert result.token_count == 5
    assert provider.request is not None
    assert provider.request.messages[0].content == "test prompt"


def test_gated_local_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "missing-provider")
    monkeypatch.setattr(
        worker_module,
        "get_provider",
        lambda provider_id: (_ for _ in ()).throw(KeyError(provider_id)),
    )

    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)

    assert result.output == ""
    assert result.error is not None
    assert "provider not available: missing-provider" in result.error


def test_gated_local_provider_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider(error=RuntimeError("API error"))
    monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "test-provider")
    monkeypatch.setattr(worker_module, "get_provider", lambda _provider_id: provider)

    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)

    assert result.output == ""
    assert result.error is not None
    assert "API error" in result.error


@pytest.mark.asyncio
async def test_gated_local_async_calls_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "test-provider")
    monkeypatch.setattr(worker_module, "get_provider", lambda _provider_id: provider)

    task = SwarmTask(prompt="async prompt")
    result = await worker_execute_async(task, mode=ExecutionMode.gated_local)

    assert result.error is None
    assert result.output == "real output"
    assert provider.request is not None
    assert provider.request.messages[0].content == "async prompt"


@pytest.mark.skipif(
    not __import__("os").environ.get("ARC_SWARMGRAPH_PROVIDER_TESTS"),
    reason="set ARC_SWARMGRAPH_PROVIDER_TESTS=1 for live provider smoke",
)
def test_gated_local_live_provider_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARC_SWARMGRAPH_PROVIDER", "9router")
    monkeypatch.setenv("ARC_SWARMGRAPH_MODEL", "ag/gemini-3.5-flash-extra-low")

    task = SwarmTask(prompt="Reply with exactly: arc-live-ok")
    task.assigned_agent_id = "worker-live"
    result = worker_execute(task, mode=ExecutionMode.gated_local, timeout=60)

    assert result.error is None
    assert "arc-live-ok" in result.output.lower()
