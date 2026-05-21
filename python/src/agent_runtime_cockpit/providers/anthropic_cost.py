"""Anthropic cost extraction — maps a ``ProviderResponse`` to a ``CostRecord``.

The extraction function is kept separate from the client so it can be
unit-tested without mocking the Anthropic SDK.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from agent_runtime_cockpit.protocol.cost_record import CostRecord
from agent_runtime_cockpit.providers.base import (
    CostExtractionError,
    CostRates,
    ProviderCapability,
    ProviderResponse,
    UsageRecord,
)


def _compute_cost(usage: UsageRecord, rates: CostRates) -> Decimal:
    """Compute the USD cost from a ``UsageRecord`` and ``CostRates``.

    Formula::

        cost = (input_tokens * input_rate
                + output_tokens * output_rate
                + cache_creation * cache_write_rate
                + cache_read * cache_read_rate) / 1_000_000

    Result is quantized to 8 decimal places using banker's rounding.
    """
    rates_per_token = {
        "input": (usage.input_tokens, Decimal(str(rates.input_per_million))),
        "output": (usage.output_tokens, Decimal(str(rates.output_per_million))),
    }
    if usage.cache_creation_input_tokens and rates.cache_write_per_million is not None:
        rates_per_token["cache_write"] = (
            usage.cache_creation_input_tokens,
            Decimal(str(rates.cache_write_per_million)),
        )
    if usage.cache_read_input_tokens and rates.cache_read_per_million is not None:
        rates_per_token["cache_read"] = (
            usage.cache_read_input_tokens,
            Decimal(str(rates.cache_read_per_million)),
        )

    total = sum(
        (Decimal(str(tokens)) * rate_per_million) / Decimal("1_000_000")
        for tokens, rate_per_million in rates_per_token.values()
    )
    return total.quantize(Decimal("1.00000000"), rounding=ROUND_HALF_EVEN)


def extract_cost(
    response: ProviderResponse,
    capability: ProviderCapability,
    *,
    estimate_fn: Callable[[], tuple[int, int]] | None = None,
) -> CostRecord:
    """Extract a ``CostRecord`` from a completed provider response.

    Args:
        response: The completed ``ProviderResponse`` containing usage data.
        capability: The ``ProviderCapability`` containing cost rates for
            the model.
        estimate_fn: Optional callable that returns ``(input_tokens,
            output_tokens)`` for the degraded path. When provided and
            the response is degraded, this replaces the default
            hardcoded fallback (100 input / 32 output tokens). The
            ``AnthropicClient`` passes an estimator-based function here.

    Returns:
        A ``CostRecord`` with ``source`` set to ``"measured"`` when usage
        is available (``not response.degraded``), or ``"estimated"`` when
        usage data was unavailable.

    Raises:
        CostExtractionError: If the response model is not found in the
            capability's cost rates.
    """
    model = response.model
    rates = capability.cost_rates.get(model)
    if rates is None:
        raise CostExtractionError(
            model=model,
            provider_id=capability.provider_id,
            configured_models=list(capability.cost_rates.keys()),
        )

    usage = response.usage
    source: str = "measured" if not response.degraded and usage.available else "estimated"
    degraded = source == "estimated"

    cost_usd: Decimal
    if source == "measured":
        cost_usd = _compute_cost(usage, rates)
    elif estimate_fn is not None:
        # Use the caller-provided estimator (e.g., from anthropic_estimator)
        estimated_input, estimated_output = estimate_fn()
        fallback_usage = UsageRecord(
            available=False,
            input_tokens=estimated_input,
            output_tokens=estimated_output,
        )
        cost_usd = _compute_cost(fallback_usage, rates)
    else:
        # Hardcoded fallback — used when no estimator is wired in
        estimated_input = max(usage.input_tokens, 100) if usage.input_tokens else 100
        estimated_output = max(usage.output_tokens, 32) if usage.output_tokens else 32
        fallback_usage = UsageRecord(
            available=False,
            input_tokens=estimated_input,
            output_tokens=estimated_output,
        )
        cost_usd = _compute_cost(fallback_usage, rates)

    return CostRecord(
        provider_id=capability.provider_id,
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_creation_input_tokens=usage.cache_creation_input_tokens,
        cache_read_input_tokens=usage.cache_read_input_tokens,
        cost_usd=cost_usd,
        source=source,  # type: ignore[arg-type]
        degraded=degraded,
        currency="USD",
    )
