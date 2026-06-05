"""v0.7-alpha: Visible indicators for active opt-in cloud features.

Surfaces in /wallet ("Active opt-ins" section) and status bar (cloud: chip).
Reads config from env; never makes network calls.
"""

from __future__ import annotations

from .budget_broker import BrokerConfig
from .observability_bridge import BridgeConfig
from .pricing_feed import PricingFeedConfig


def active_optins() -> list[str]:
    """Return human-readable lines for each active opt-in feature. Empty = all off."""
    lines: list[str] = []

    feed = PricingFeedConfig.from_env()
    if feed.enabled:
        lines.append(f"Pricing feed:   {feed.feed_url} (source: {feed.feed_source})")

    broker = BrokerConfig.from_env()
    if broker.enabled:
        lines.append(f"Team broker:    {broker.broker_url} (team: {broker.team_id})")

    bridge = BridgeConfig.from_env()
    if bridge.enabled:
        lines.append(f"Observability:  {bridge.destination_url} (consent: {bridge.consent_mode})")

    return lines


def any_cloud_feature_active() -> bool:
    """True if any opt-in cloud feature is enabled — drives status bar chip."""
    return bool(active_optins())
