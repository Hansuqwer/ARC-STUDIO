"""Tests for Phase 20: MCP dev-bridge guard (default-off, loopback+token+TTL, fail-closed)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent_runtime_cockpit.mobile import MobileMcpDevBridge

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_default_off_denies() -> None:
    bridge = MobileMcpDevBridge()
    d = bridge.check_connection("127.0.0.1", "anything", now=T0)
    assert d.allowed is False and "default-off" in d.reason


def test_enabled_loopback_valid_token_admits() -> None:
    bridge = MobileMcpDevBridge()
    token = MobileMcpDevBridge.issue_token()
    bridge.enable(token, ttl_seconds=300, now=T0)
    d = bridge.check_connection("127.0.0.1", token, now=T0 + timedelta(seconds=10))
    assert d.allowed is True


def test_non_loopback_refused() -> None:
    bridge = MobileMcpDevBridge()
    token = MobileMcpDevBridge.issue_token()
    bridge.enable(token, ttl_seconds=300, now=T0)
    d = bridge.check_connection("10.0.0.5", token, now=T0)
    assert d.allowed is False and "non-loopback" in d.reason


def test_bad_or_missing_token_denied() -> None:
    bridge = MobileMcpDevBridge()
    bridge.enable("real-token", ttl_seconds=300, now=T0)
    assert bridge.check_connection("127.0.0.1", "wrong", now=T0).allowed is False
    assert bridge.check_connection("127.0.0.1", None, now=T0).allowed is False


def test_ttl_expiry_denies() -> None:
    bridge = MobileMcpDevBridge()
    token = MobileMcpDevBridge.issue_token()
    bridge.enable(token, ttl_seconds=60, now=T0)
    d = bridge.check_connection("127.0.0.1", token, now=T0 + timedelta(seconds=120))
    assert d.allowed is False and "TTL expired" in d.reason


def test_disable_returns_to_default_off() -> None:
    bridge = MobileMcpDevBridge()
    token = MobileMcpDevBridge.issue_token()
    bridge.enable(token, ttl_seconds=300, now=T0)
    bridge.disable()
    assert bridge.check_connection("127.0.0.1", token, now=T0).allowed is False


def test_enable_validation() -> None:
    bridge = MobileMcpDevBridge()
    with pytest.raises(ValueError):
        bridge.enable("", 300)
    with pytest.raises(ValueError):
        bridge.enable("t", 0)
