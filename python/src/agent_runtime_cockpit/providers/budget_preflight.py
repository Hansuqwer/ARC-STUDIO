"""Provider-aware budget preflight helpers.

Keeps ``BudgetEnforcer`` provider-agnostic while giving provider-backed
runtime code a one-call path from request messages -> token estimate -> USD
estimate -> budget preflight.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from agent_runtime_cockpit.budget.schema import BudgetEnforcer

from .anthropic_estimator import build_estimate_fn, select_estimator
from .base import CostExtractionError


def preflight_with_estimator(
    enforcer: BudgetEnforcer,
    *,
    provider_capability: Any,
    request_model: str,
    request_messages: list[dict[str, Any]],
    provider_id: str,
    run_active: bool = False,
    workflow_active: bool = False,
    prefer_sdk_estimator: bool = False,
    sdk_client: Any = None,
) -> None:
    """Estimate request cost and run ``BudgetEnforcer.preflight``.

    Uses ``TiktokenApproximateEstimator`` by default (local, no network).
    Pass ``prefer_sdk_estimator=True`` and *sdk_client* to use the Anthropic
    SDK's ``messages.count_tokens`` instead.
    """
    estimator = select_estimator(
        prefer_sdk=prefer_sdk_estimator,
        sdk_client=sdk_client,
    )
    estimate_fn = build_estimate_fn(estimator, request_messages, model=request_model)
    input_tokens, output_tokens = estimate_fn()

    cost_rates = provider_capability.cost_rates.get(request_model)
    if cost_rates is None:
        raise CostExtractionError(
            model=request_model,
            provider_id=provider_id,
            configured_models=list(provider_capability.cost_rates.keys()),
        )

    input_cost = (Decimal(str(input_tokens)) * Decimal(str(cost_rates.input_per_million))) / Decimal("1_000_000")
    output_cost = (Decimal(str(output_tokens)) * Decimal(str(cost_rates.output_per_million))) / Decimal("1_000_000")
    estimated_cost_usd = (input_cost + output_cost).quantize(Decimal("1.00000000"), rounding=ROUND_HALF_EVEN)

    enforcer.preflight(
        estimated_cost_usd,
        provider_id=provider_id,
        run_active=run_active,
        workflow_active=workflow_active,
    )
