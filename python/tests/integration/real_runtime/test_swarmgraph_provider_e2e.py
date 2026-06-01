"""Opt-in live provider-backed SwarmGraph E2E.

Skipped by default. This is evidence only for the selected provider/model path
when explicitly run with live gates and an env-referenced API key. It does not
make default CI/network calls and does not prove broad provider-backed adoption.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from agent_runtime_cockpit.providers import registry
from agent_runtime_cockpit.providers.e2e_evidence import (
    build_provider_e2e_evidence,
    resolve_provider_e2e_artifact_path,
    utc_now_iso,
    write_provider_e2e_evidence,
)
from agent_runtime_cockpit.providers.base import ProviderRequest as ArcProviderRequest
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

pytestmark = pytest.mark.real_runtime

_LIVE_GATE = "ARC_RUN_LIVE_PROVIDER_E2E"
_PROVIDER_ENV = "ARC_SWARMGRAPH_PROVIDER"
_MODEL_ENV = "ARC_SWARMGRAPH_MODEL"


class _NeverCancelled:
    is_cancelled = False

    def raise_if_cancelled(self) -> None:
        return None


class _RecordingArcProviderAdapter:
    """Bridge ARC ProviderClient into swarmgraph-sdk Provider and record live calls."""

    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self._model = model
        self.calls: list[dict[str, Any]] = []

    def capabilities(self) -> ProviderCapability:
        caps = self._client.capabilities()
        return ProviderCapability(
            provider_id=caps.provider_id,
            provider_name=caps.provider_name,
            supported_models=[self._model],
            default_model=self._model,
            max_context_tokens=caps.max_context_tokens,
            cost_rates={self._model: CostRates(input_per_million=0.0, output_per_million=0.0)},
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
        self.calls.append(
            {
                "model": response.model,
                "content_length": len(response.content),
                "degraded": response.degraded,
            }
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


def _skip_unless_live_provider_ready() -> tuple[str, str]:
    if os.environ.get(_LIVE_GATE) != "1":
        pytest.skip(f"set {_LIVE_GATE}=1 to run live provider-backed SwarmGraph E2E")
    if os.environ.get("ARC_ALLOW_LIVE_PROVIDER_TESTS") != "true":
        pytest.skip("set ARC_ALLOW_LIVE_PROVIDER_TESTS=true to permit live provider tests")
    provider = os.environ.get(_PROVIDER_ENV, "crofai")
    model = os.environ.get(_MODEL_ENV, "deepseek-v4-pro-precision")
    required_envs = {
        "crofai": ("CROFAI_API_KEY", "CROF_API_KEY", "CROFAI"),
        "9router": ("NINEROUTER_API_KEY", "ROUTER9_API_KEY"),
    }.get(provider, ())
    if required_envs and not any(os.environ.get(name) for name in required_envs):
        pytest.skip(f"set one provider key env ref for {provider}; raw key is never logged/stored")
    return provider, model


def test_live_provider_backed_swarmgraph_e2e_opt_in_only() -> None:
    provider_name, model = _skip_unless_live_provider_ready()
    provider = _RecordingArcProviderAdapter(registry.get(provider_name), model)
    prompt = "Reply with a concise confirmation that includes the token ARC_E2E_OK."
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        allow_paid_calls=True,
        num_workers=1,
        max_rounds=1,
        worker_timeout_seconds=45,
    )

    started_at = utc_now_iso()
    result = SwarmGraphRunner(config=config, provider=provider).run_result(prompt)
    ended_at = utc_now_iso()

    event_kinds = {event["kind"] for event in result.events}
    assert result.status == "completed"
    assert result.completed_tasks == 1
    assert result.results[0].output.strip()
    assert provider.calls and provider.calls[0]["content_length"] > 0
    assert {"topology", "worker", "consensus"}.issubset(event_kinds)

    evidence = build_provider_e2e_evidence(
        provider=provider_name,
        model=model,
        prompt=prompt,
        output=result.results[0].output,
        status=result.status,
        completed_tasks=result.completed_tasks,
        events=result.events,
        calls=provider.calls,
        started_at=started_at,
        ended_at=ended_at,
    )
    write_provider_e2e_evidence(
        evidence,
        resolve_provider_e2e_artifact_path(provider=provider_name, model=model),
    )
