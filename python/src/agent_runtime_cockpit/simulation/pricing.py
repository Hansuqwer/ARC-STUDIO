"""MT-2: Derive a per-call cost estimate for the simulator from live CostRates.

Usage::

    from agent_runtime_cockpit.simulation.pricing import simulation_cost_per_call
    from agent_runtime_cockpit.simulation.models import SimulationConfig

    cfg = SimulationConfig(
        cost_per_paid_call_usd=simulation_cost_per_call("anthropic", "claude-sonnet-4-5"),
    )

The estimate assumes a representative call of 1 000 input tokens + 500 output
tokens — a conservative low-end for most agentic workflows. The value is
intentionally not a maximum; it's a floor for cost gate comparisons.

Falls back to ``None`` (simulator uses ``_PAID_CALL_COST_FLOOR``) if the
provider / model is unknown or pricing data is unavailable.
"""

from __future__ import annotations

from typing import Optional

# Representative token counts for a "typical" agentic call.
_TYPICAL_INPUT_TOKENS = 1_000
_TYPICAL_OUTPUT_TOKENS = 500


def simulation_cost_per_call(
    provider_id: str,
    model_id: str,
    *,
    input_tokens: int = _TYPICAL_INPUT_TOKENS,
    output_tokens: int = _TYPICAL_OUTPUT_TOKENS,
) -> Optional[float]:
    """Return an estimated USD cost per paid call for the given provider+model.

    Uses ``input_tokens`` / ``output_tokens`` as the representative call size.
    Returns ``None`` if pricing data is unavailable (caller falls back to the
    ``_PAID_CALL_COST_FLOOR`` constant in the simulator).
    """
    try:
        from ..providers.openai_compatible import OpenAICompatibleClient

        caps = OpenAICompatibleClient(vendor=provider_id).capabilities()
        rates = (caps.cost_rates or {}).get(model_id)
        if rates is None:
            return None
        if getattr(rates, "is_free_tier", False):
            return 0.0
        input_usd = (input_tokens / 1_000_000) * rates.input_per_million
        output_usd = (output_tokens / 1_000_000) * rates.output_per_million
        return round(input_usd + output_usd, 8)
    except Exception:
        return None


__all__ = ["simulation_cost_per_call"]
