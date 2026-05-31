from __future__ import annotations

from decimal import Decimal
import time

import pytest

from agent_runtime_cockpit.swarmgraph.config import ExecutionMode, SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.models import SwarmTask
from agent_runtime_cockpit.swarmgraph.providers import (
    CostRates,
    ProviderCapability,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner
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


class _BlockingProvider(_FakeProvider):
    async def complete(self, request: ProviderRequest, *, cancellation_token) -> ProviderResponse:
        self.request = request
        time.sleep(0.2)
        return self.response


class _CancellationToken:
    def __init__(self) -> None:
        self.is_cancelled = True

    def raise_if_cancelled(self) -> None:
        raise RuntimeError("cancelled")


def test_gated_local_calls_provider() -> None:
    provider = _FakeProvider()

    task = SwarmTask(prompt="test prompt")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(
        task,
        mode=ExecutionMode.gated_local,
        provider=provider,
        allow_paid_calls=True,
    )

    assert result.error is None
    assert result.output == "real output"
    assert result.cost_usd == 0.001
    assert result.token_count == 5
    assert provider.request is not None
    assert provider.request.messages[0].content == "test prompt"


def test_gated_local_provider_unavailable() -> None:
    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(task, mode=ExecutionMode.gated_local)

    assert result.output == ""
    assert result.error is not None
    assert "provider not configured" in result.error


def test_gated_local_paid_call_denied_by_default() -> None:
    provider = _FakeProvider()
    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"

    result = worker_execute(task, mode=ExecutionMode.gated_local, provider=provider)

    assert result.output == ""
    assert result.error == "paid provider calls disabled; set allow_paid_calls=True"
    assert provider.request is None


def test_gated_local_provider_exception() -> None:
    provider = _FakeProvider(error=RuntimeError("API error"))

    task = SwarmTask(prompt="test")
    task.assigned_agent_id = "worker-1"
    result = worker_execute(
        task,
        mode=ExecutionMode.gated_local,
        provider=provider,
        allow_paid_calls=True,
    )

    assert result.output == ""
    assert result.error is not None
    assert "API error" in result.error


def test_gated_local_timeout_returns_without_hanging() -> None:
    provider = _BlockingProvider()

    task = SwarmTask(prompt="test")
    started = time.monotonic()
    result = worker_execute(
        task,
        mode=ExecutionMode.gated_local,
        timeout=0.01,
        provider=provider,
        allow_paid_calls=True,
    )

    assert time.monotonic() - started < 0.1
    assert result.error == "timeout"
    time.sleep(0.25)


@pytest.mark.asyncio
async def test_gated_local_async_calls_provider() -> None:
    provider = _FakeProvider()

    task = SwarmTask(prompt="async prompt")
    result = await worker_execute_async(
        task,
        mode=ExecutionMode.gated_local,
        provider=provider,
        allow_paid_calls=True,
    )

    assert result.error is None
    assert result.output == "real output"
    assert provider.request is not None
    assert provider.request.messages[0].content == "async prompt"


@pytest.mark.asyncio
async def test_gated_local_cancellation_token_reaches_provider() -> None:
    provider = _FakeProvider()
    task = SwarmTask(prompt="cancel")

    result = await worker_execute_async(
        task,
        mode=ExecutionMode.gated_local,
        provider=provider,
        allow_paid_calls=True,
        cancellation_token=_CancellationToken(),
    )

    assert result.output == ""
    assert result.error is not None
    assert "cancelled" in result.error


@pytest.mark.asyncio
async def test_runner_injects_provider_and_paid_gate() -> None:
    provider = _FakeProvider()
    cfg = SwarmGraphConfig(
        execution_mode=ExecutionMode.gated_local,
        allow_paid_calls=True,
        max_rounds=1,
    )

    result = await SwarmGraphRunner(config=cfg, provider=provider).run_async("runner prompt")

    assert result["status"] == "completed"
    assert result["results"][0]["output"] == "real output"
    assert provider.request is not None
    assert provider.request.messages[0].role == "user"
    assert "runner prompt" in provider.request.messages[0].content


def test_provider_models_do_not_require_arc_provider_types() -> None:
    request = ProviderRequest(
        model="test-model",
        messages=[ProviderMessage(role="user", content="hello")],
    )
    response = ProviderResponse(
        call_id=request.call_id,
        model="test-model",
        content="ok",
        finish_reason="stop",
        usage=UsageRecord(input_tokens=1, output_tokens=1),
    )

    assert request.messages[0].content == "hello"
    assert response.content == "ok"
