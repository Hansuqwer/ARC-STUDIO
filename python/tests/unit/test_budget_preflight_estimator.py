"""Tests for ``preflight_with_estimator`` — estimator-wired budget preflight."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.budget import (
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetState,
    ConfirmationRequired,
)
from agent_runtime_cockpit.providers import (
    CostRates,
    ProviderCapability,
    ProviderFeature,
    preflight_with_estimator,
)


def _capability() -> ProviderCapability:
    return ProviderCapability(
        provider_id="anthropic",
        provider_name="Anthropic",
        supported_models=["claude-sonnet-4-6"],
        default_model="claude-sonnet-4-6",
        features=[ProviderFeature.STREAMING],
        max_context_tokens=200_000,
        cost_rates={
            "claude-sonnet-4-6": CostRates(
                input_per_million=3.0,
                output_per_million=15.0,
                cache_write_per_million=3.75,
                cache_read_per_million=0.30,
            ),
        },
    )


def _enforcer(first_launch: bool = True) -> BudgetEnforcer:
    config = BudgetConfig(
        first_launch_confirmed=first_launch,
        caps=[],
    )
    state = BudgetState()
    return BudgetEnforcer(config, state)


MESSAGES = [{"role": "user", "content": "Write a Python function that computes fibonacci numbers."}]


class TestPreflightWithEstimator:
    def test_estimates_cost_and_passes_preflight(self):
        """Happy path: estimator produces tokens, preflight passes."""
        enforcer = _enforcer(first_launch=True)
        # Should not raise
        preflight_with_estimator(
            enforcer,
            provider_capability=_capability(),
            request_model="claude-sonnet-4-6",
            request_messages=MESSAGES,
            provider_id="anthropic",
        )

    def test_raises_budget_exceeded_when_over_cap(self):
        """Tiny cap should be exceeded by any real estimate."""
        config = BudgetConfig(
            first_launch_confirmed=True,
            caps=[],
        )
        state = BudgetState()
        enforcer = BudgetEnforcer(config, state)
        # Set session cap to very low
        enforcer._config._configured_cap = lambda *a, **kw: Decimal("0.000001")  # type: ignore[method-assign]
        with pytest.raises(BudgetExceeded):
            preflight_with_estimator(
                enforcer,
                provider_capability=_capability(),
                request_model="claude-sonnet-4-6",
                request_messages=MESSAGES,
                provider_id="anthropic",
            )

    def test_raises_confirmation_required_on_first_launch(self):
        """First launch with unconfirmed budget and large prompt should raise."""
        config = BudgetConfig(
            first_launch_confirmed=False,
            confirmation_required_above_usd=Decimal("0.00"),  # any cost triggers
        )
        state = BudgetState()
        enforcer = BudgetEnforcer(config, state)
        with pytest.raises(ConfirmationRequired):
            preflight_with_estimator(
                enforcer,
                provider_capability=_capability(),
                request_model="claude-sonnet-4-6",
                request_messages=[{"role": "user", "content": "x" * 5000}],
                provider_id="anthropic",
            )

    def test_raises_cost_extraction_error_for_unknown_model(self):
        """A model not in cost_rates should raise."""
        from agent_runtime_cockpit.providers import CostExtractionError

        enforcer = _enforcer(first_launch=True)
        with pytest.raises(CostExtractionError, match="not in rate map"):
            preflight_with_estimator(
                enforcer,
                provider_capability=_capability(),
                request_model="unknown-model",
                request_messages=MESSAGES,
                provider_id="anthropic",
            )

    def test_raises_cost_extraction_error_lists_configured_models(self):
        """Error message must enumerate configured models."""
        from agent_runtime_cockpit.providers import CostExtractionError

        enforcer = _enforcer(first_launch=True)
        with pytest.raises(CostExtractionError) as excinfo:
            preflight_with_estimator(
                enforcer,
                provider_capability=_capability(),
                request_model="claude-opus-4-7",
                request_messages=MESSAGES,
                provider_id="anthropic",
            )
        assert "claude-sonnet-4-6" in str(excinfo.value)
