from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from .schema import (
    BudgetCap,
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetScope,
    BudgetState,
    ConfirmationRequired,
    ScopeSpend,
)

__all__ = [
    "BudgetCap",
    "BudgetConfig",
    "BudgetEnforcer",
    "BudgetExceeded",
    "BudgetScope",
    "BudgetState",
    "ConfirmationRequired",
    "preflight_with_estimator",
    "ScopeSpend",
]


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
    """Convenience: estimate cost from request content and run preflight.

    Combines the :mod:`~agent_runtime_cockpit.providers.anthropic_estimator`
    tokenizer with :class:`BudgetEnforcer.preflight` in one call.

    Uses :class:`~agent_runtime_cockpit.providers.anthropic_estimator.TiktokenApproximateEstimator`
    by default (local, no network). Pass ``prefer_sdk_estimator=True`` and
    *sdk_client* to use the Anthropic SDK's ``count_tokens`` instead.

    Args:
        enforcer: The ``BudgetEnforcer`` instance.
        provider_capability: A ``ProviderCapability`` (duck-typed; must have
            ``.cost_rates`` dict and ``.provider_id``).
        request_model: The model name (e.g. ``"claude-sonnet-4-6"``).
        request_messages: The Anthropic-shaped message dicts that will be
            sent to the provider.
        provider_id: Provider identifier for scoping (e.g. ``"anthropic"``).
        run_active: Whether a run scope is active.
        workflow_active: Whether a workflow scope is active.
        prefer_sdk_estimator: If True and *sdk_client* is provided, use the
            SDK's ``count_tokens`` for a more accurate estimate.
        sdk_client: An object implementing the ``count_tokens`` protocol.

    Raises:
        ConfirmationRequired: First-launch cost above threshold.
        BudgetExceeded: Estimated cost would exceed a configured cap.
        CostExtractionError: *request_model* not in *provider_capability*'s
            cost rates.
    """
    from agent_runtime_cockpit.providers.anthropic_estimator import (
        build_estimate_fn,
        select_estimator,
    )
    from agent_runtime_cockpit.providers.base import CostExtractionError

    estimator = select_estimator(
        prefer_sdk=prefer_sdk_estimator,
        sdk_client=sdk_client,
    )
    estimate_fn = build_estimate_fn(estimator, request_messages)
    input_tokens, output_tokens = estimate_fn()

    # Look up cost rates and compute estimated USD cost
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
