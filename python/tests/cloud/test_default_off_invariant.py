"""v0.7 default-off invariant + indicator tests.

The single most important test in the sprint: with no env vars, zero
outbound calls and zero active opt-ins.
"""

from __future__ import annotations

from unittest.mock import patch

from agent_runtime_cockpit.cloud.indicators import active_optins, any_cloud_feature_active
from agent_runtime_cockpit.cloud.budget_broker import BudgetBrokerClient, BrokerConfig
from agent_runtime_cockpit.cloud.observability_bridge import BridgeConfig, ObservabilityBridge
from agent_runtime_cockpit.cloud.pricing_feed import PricingFeedClient, PricingFeedConfig


def _clear_env(monkeypatch):
    for var in [
        "ARC_PRICING_FEED_ENABLED",
        "ARC_PRICING_FEED_URL",
        "ARC_PRICING_FEED_SOURCE",
        "ARC_BUDGET_BROKER_URL",
        "ARC_BUDGET_BROKER_TOKEN",
        "ARC_BUDGET_TEAM_ID",
        "ARC_OBSERVABILITY_BRIDGE_URL",
    ]:
        monkeypatch.delenv(var, raising=False)


# ── The core invariant ────────────────────────────────────────────────────


def test_no_active_optins_by_default(monkeypatch):
    _clear_env(monkeypatch)
    assert active_optins() == []
    assert any_cloud_feature_active() is False


def test_no_outbound_calls_when_all_disabled(monkeypatch):
    _clear_env(monkeypatch)
    with patch("urllib.request.urlopen") as mock_url:
        # All three clients, default config — none should call out
        PricingFeedClient(PricingFeedConfig.from_env()).refresh()
        BudgetBrokerClient(BrokerConfig.from_env()).remote_preflight(
            "SESSION", __import__("decimal").Decimal("1")
        )
        ObservabilityBridge(BridgeConfig.from_env()).export_metrics({"tokens": 1})
    mock_url.assert_not_called()


# ── Indicators reflect active features ─────────────────────────────────────


def test_pricing_feed_shows_in_optins(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    lines = active_optins()
    assert any("Pricing feed" in line for line in lines)
    assert any_cloud_feature_active()


def test_broker_shows_in_optins(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ARC_BUDGET_BROKER_URL", "https://b.example")
    monkeypatch.setenv("ARC_BUDGET_BROKER_TOKEN", "tok")
    monkeypatch.setenv("ARC_BUDGET_TEAM_ID", "team1")
    lines = active_optins()
    assert any("Team broker" in line for line in lines)


def test_observability_shows_in_optins(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ARC_OBSERVABILITY_BRIDGE_URL", "https://otlp.example")
    lines = active_optins()
    assert any("Observability" in line for line in lines)


def test_broker_token_not_in_optin_output(monkeypatch):
    """Indicator must not leak the bearer token."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ARC_BUDGET_BROKER_URL", "https://b.example")
    monkeypatch.setenv("ARC_BUDGET_BROKER_TOKEN", "super-secret-token")
    monkeypatch.setenv("ARC_BUDGET_TEAM_ID", "team1")
    lines = active_optins()
    assert all("super-secret-token" not in line for line in lines)
