"""Tests for v0.7 opt-in pricing feed (cloud/pricing_feed.py). 12 cases."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


from agent_runtime_cockpit.cloud.pricing_feed import (
    PricingFeedClient,
    PricingFeedConfig,
    PricingFeedRefreshed,
)
from agent_runtime_cockpit.events import get_bus, reset_bus


def _cfg(
    tmp_path: Path, pinned: str | None = None, source: str = "openrouter"
) -> PricingFeedConfig:
    return PricingFeedConfig(
        feed_url="https://openrouter.ai/api/v1/models",
        feed_source=source,
        pinned_hash=pinned,
        cache_path=tmp_path / "cache.json",
    )


def _raw(rows: int = 5) -> bytes:
    data = [
        {"id": f"m{i}", "pricing": {"prompt": "0.001", "completion": "0.002"}} for i in range(rows)
    ]
    return json.dumps({"data": data}).encode()


def _mock_url(raw: bytes):
    """Create a proper context manager mock for urllib.request.urlopen."""

    m = MagicMock()
    m.read.return_value = raw
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


# ── 1. Default-off ────────────────────────────────────────────────────────────


def test_feature_disabled_no_outbound_call(tmp_path, monkeypatch):
    monkeypatch.delenv("ARC_PRICING_FEED_ENABLED", raising=False)
    cfg = _cfg(tmp_path)
    with patch("urllib.request.urlopen") as mock_url:
        result = PricingFeedClient(cfg).refresh()
    mock_url.assert_not_called()
    assert not result.success
    assert result.error_reason == "feature_disabled"


# ── 2. Hash matches → success ─────────────────────────────────────────────────


def test_hash_matches_pinned_applies_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = _raw(10)
    cfg = _cfg(tmp_path, pinned=hashlib.sha256(raw).hexdigest())
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        result = PricingFeedClient(cfg).refresh()
    assert result.success
    assert result.rows_seen == 10
    assert not result.hash_changed


# ── 3. Hash differs → warn, keep local ───────────────────────────────────────


def test_hash_differs_from_pinned_warns_keeps_local(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = _raw(5)
    cfg = _cfg(tmp_path, pinned="badhash" * 9)
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        result = PricingFeedClient(cfg).refresh()
    assert not result.success
    assert result.hash_changed


# ── 4. Network failure → local fallback ──────────────────────────────────────


def test_network_failure_keeps_local_table(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    cfg = _cfg(tmp_path)
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        result = PricingFeedClient(cfg).refresh()
    assert not result.success
    assert "unavailable" in (result.error_reason or "")


# ── 5. Parse failure → local fallback ────────────────────────────────────────


def test_parse_failure_keeps_local_table(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = b"notjson"
    cfg = _cfg(tmp_path, pinned=hashlib.sha256(raw).hexdigest())
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        result = PricingFeedClient(cfg).refresh()
    assert not result.success
    assert result.error_reason == "parse_failure"


# ── 6. Cached feed used when offline ─────────────────────────────────────────


def test_cached_feed_used_if_present_when_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = _raw(7)
    cfg = _cfg(tmp_path, pinned=hashlib.sha256(raw).hexdigest())
    cfg.cache_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.cache_path.write_bytes(raw)
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        result = PricingFeedClient(cfg).refresh()
    assert result.success
    assert result.source == "cache"


# ── 7. Event emitted on success ───────────────────────────────────────────────


def test_refresh_emits_pricing_feed_refreshed_event(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    reset_bus()
    received = []
    get_bus().subscribe("pricing_feed_refreshed", received.append)
    raw = _raw(3)
    cfg = _cfg(tmp_path, pinned=hashlib.sha256(raw).hexdigest())
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        PricingFeedClient(cfg).refresh()
    assert len(received) == 1
    assert isinstance(received[0], PricingFeedRefreshed)
    assert received[0].rows_seen == 3


# ── 8. Feed URL not redacted in event ────────────────────────────────────────


def test_feed_url_in_event_is_not_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    reset_bus()
    received = []
    get_bus().subscribe("pricing_feed_refreshed", received.append)
    raw = _raw(2)
    cfg = _cfg(tmp_path, pinned=hashlib.sha256(raw).hexdigest())
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        PricingFeedClient(cfg).refresh()
    assert "openrouter.ai" in received[0].feed_url


# ── 9. No pinned hash → first run succeeds ───────────────────────────────────


def test_first_run_no_pinned_hash_succeeds(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = _raw(4)
    cfg = _cfg(tmp_path, pinned=None)
    with patch("urllib.request.urlopen", return_value=_mock_url(raw)):
        result = PricingFeedClient(cfg).refresh()
    assert result.success


# ── 10. No user data in request headers ──────────────────────────────────────


def test_no_telemetry_in_feed_request_only_get_url(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    raw = _raw(2)
    cfg = _cfg(tmp_path)
    captured = []

    def fake_urlopen(req, timeout=None):
        captured.append(req)
        return _mock_url(raw)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        PricingFeedClient(cfg).refresh()

    assert len(captured) == 1
    headers = {k.lower(): v for k, v in captured[0].headers.items()}
    assert "authorization" not in headers
    assert "x-session" not in headers


# ── 11. accept_new_hash logs acceptance ──────────────────────────────────────


def test_accept_new_hash_command_logs_acceptance(tmp_path, monkeypatch, caplog):
    import logging

    cfg = _cfg(tmp_path)
    with caplog.at_level(logging.INFO, logger="arc.cloud.pricing_feed"):
        PricingFeedClient(cfg).accept_new_hash("abc" * 20 + "00" * 2)
    assert "accepted" in caplog.text.lower()


# ── 12. Source switch to models-dev ──────────────────────────────────────────


def test_source_switch_openrouter_to_models_dev_falls_back(monkeypatch):
    monkeypatch.setenv("ARC_PRICING_FEED_SOURCE", "models-dev")
    monkeypatch.setenv("ARC_PRICING_FEED_ENABLED", "1")
    cfg = PricingFeedConfig.from_env()
    assert "models.dev" in cfg.feed_url
    assert cfg.feed_source == "models-dev"
