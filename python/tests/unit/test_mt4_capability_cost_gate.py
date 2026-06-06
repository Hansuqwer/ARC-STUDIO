"""MT-4: Capability-Card cost gate via preflight_with_estimator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.budget import BudgetConfig, BudgetEnforcer, BudgetState
from agent_runtime_cockpit.providers import (
    CostRates,
    ProviderCapability,
    ProviderFeature,
    preflight_with_estimator,
)
from agent_runtime_cockpit.providers.budget_preflight import CapabilityBudgetExceeded


def _capability() -> ProviderCapability:
    return ProviderCapability(
        provider_id="anthropic",
        provider_name="Anthropic",
        supported_models=["claude-sonnet-4-5"],
        default_model="claude-sonnet-4-5",
        features=[ProviderFeature.STREAMING],
        max_context_tokens=200_000,
        cost_rates={
            "claude-sonnet-4-5": CostRates(
                input_per_million=3.0,
                output_per_million=15.0,
            ),
        },
    )


def _enforcer() -> BudgetEnforcer:
    return BudgetEnforcer(BudgetConfig(first_launch_confirmed=True, caps=[]), BudgetState())


_MESSAGES = [{"role": "user", "content": "hello world"}]


# ── Default: no capability gate ───────────────────────────────────────────────


def test_no_gate_passes_through():
    """Without capability_max_cost_usd, no CapabilityBudgetExceeded is raised."""
    preflight_with_estimator(
        _enforcer(),
        provider_capability=_capability(),
        request_model="claude-sonnet-4-5",
        request_messages=_MESSAGES,
        provider_id="anthropic",
        capability_max_cost_usd=None,
    )  # no exception


# ── Gate below estimated cost raises ─────────────────────────────────────────


def test_gate_raises_when_estimate_exceeds_cap():
    """capability_max_cost_usd below the estimated cost raises CapabilityBudgetExceeded."""
    with pytest.raises(CapabilityBudgetExceeded) as exc_info:
        preflight_with_estimator(
            _enforcer(),
            provider_capability=_capability(),
            request_model="claude-sonnet-4-5",
            request_messages=_MESSAGES,
            provider_id="anthropic",
            capability_max_cost_usd=0.000001,  # impossibly tight cap
        )
    err = exc_info.value
    assert err.max_usd == 0.000001
    assert err.estimated_usd > Decimal("0.000001")
    assert "anthropic" in str(err)
    assert "claude-sonnet-4-5" in str(err)


def test_gate_passes_when_cap_high_enough():
    """capability_max_cost_usd above the estimated cost does not raise."""
    preflight_with_estimator(
        _enforcer(),
        provider_capability=_capability(),
        request_model="claude-sonnet-4-5",
        request_messages=_MESSAGES,
        provider_id="anthropic",
        capability_max_cost_usd=1.0,  # generous cap
    )  # no exception


# ── Gate is checked before BudgetEnforcer scopes ─────────────────────────────


def test_capability_gate_raises_before_budget_scope():
    """CapabilityBudgetExceeded is raised even when the session budget would pass."""
    # Session budget is large — only the capability cap is tight.
    with pytest.raises(CapabilityBudgetExceeded):
        preflight_with_estimator(
            _enforcer(),
            provider_capability=_capability(),
            request_model="claude-sonnet-4-5",
            request_messages=_MESSAGES,
            provider_id="anthropic",
            capability_max_cost_usd=0.000001,
        )


# ── Exception fields ──────────────────────────────────────────────────────────


def test_capability_budget_exceeded_attributes():
    from decimal import Decimal as D

    exc = CapabilityBudgetExceeded(
        estimated_usd=D("0.005"),
        max_usd=0.001,
        provider_id="openai",
        model="gpt-4o",
    )
    assert exc.estimated_usd == D("0.005")
    assert exc.max_usd == 0.001
    assert "openai" in str(exc)
    assert "gpt-4o" in str(exc)
    assert "0.005" in str(exc)


# ── Zero cap means zero cost only ────────────────────────────────────────────


def test_zero_cap_raises_for_any_paid_call():
    """cap=0.0 must raise for any non-trivial estimated cost."""
    with pytest.raises(CapabilityBudgetExceeded):
        preflight_with_estimator(
            _enforcer(),
            provider_capability=_capability(),
            request_model="claude-sonnet-4-5",
            request_messages=[{"role": "user", "content": "x" * 500}],
            provider_id="anthropic",
            capability_max_cost_usd=0.0,
        )
