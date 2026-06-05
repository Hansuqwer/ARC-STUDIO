"""Tests for v0.7 observability bridge (cloud/observability_bridge.py). 10 cases."""

from __future__ import annotations

from unittest.mock import patch

from agent_runtime_cockpit.cloud.observability_bridge import (
    BridgeConfig,
    ObservabilityBridge,
    ObservabilityExportStarted,
    sanitize_attributes,
)
from agent_runtime_cockpit.events import get_bus, reset_bus


def _cfg(consent_mode="per_session", url="https://otlp.example") -> BridgeConfig:
    return BridgeConfig(destination_url=url, consent_mode=consent_mode)


# 1. disabled when no URL
def test_disabled_without_url():
    assert not BridgeConfig().enabled
    bridge = ObservabilityBridge(BridgeConfig(), session_consent=True)
    assert bridge.export_metrics({"tokens": 100}) is False


# 2. no export without consent (per_session, consent=False)
def test_no_export_without_consent():
    bridge = ObservabilityBridge(_cfg("per_session"), session_consent=False)
    assert bridge.export_metrics({"tokens": 100}) is False


# 3. export with per-session consent
def test_export_with_session_consent():
    bridge = ObservabilityBridge(_cfg("per_session"), session_consent=True)
    with patch.object(bridge, "_send"):
        assert bridge.export_metrics({"cost_usd": 0.05}) is True


# 4. always-consent mode exports without session flag
def test_always_consent_mode():
    bridge = ObservabilityBridge(_cfg("always"), session_consent=False)
    with patch.object(bridge, "_send"):
        assert bridge.export_metrics({"cost_usd": 0.05}) is True


# 5. env_only consent honored
def test_env_only_consent(monkeypatch):
    monkeypatch.setenv("ARC_OBSERVABILITY_BRIDGE_CONSENT", "yes")
    bridge = ObservabilityBridge(_cfg("env_only"), session_consent=False)
    with patch.object(bridge, "_send"):
        assert bridge.export_metrics({"cost_usd": 0.05}) is True


# 6. env_only without env → no export
def test_env_only_without_env(monkeypatch):
    monkeypatch.delenv("ARC_OBSERVABILITY_BRIDGE_CONSENT", raising=False)
    bridge = ObservabilityBridge(_cfg("env_only"), session_consent=False)
    assert bridge.export_metrics({"cost_usd": 0.05}) is False


# 7. sanitize strips forbidden keys
def test_sanitize_strips_prompt_and_code():
    dirty = {
        "tokens": 100,
        "cost_usd": 0.05,
        "prompt": "secret",
        "messages": [...],
        "code": "def x()",
        "system_prompt": "you are",
        "tool_output": "data",
    }
    clean = sanitize_attributes(dirty)
    assert "tokens" in clean
    assert "cost_usd" in clean
    assert "prompt" not in clean
    assert "messages" not in clean
    assert "code" not in clean
    assert "system_prompt" not in clean
    assert "tool_output" not in clean


# 8. exported payload is sanitized
def test_exported_payload_sanitized():
    bridge = ObservabilityBridge(_cfg("always"))
    captured = {}
    with patch.object(bridge, "_send", side_effect=lambda attrs: captured.update(attrs)):
        bridge.export_metrics({"tokens": 100, "prompt": "leak me"})
    assert "tokens" in captured
    assert "prompt" not in captured


# 9. ObservabilityExportStarted event emitted
def test_export_event_emitted():
    reset_bus()
    received = []
    get_bus().subscribe("observability_export_started", received.append)
    bridge = ObservabilityBridge(_cfg("always"))
    with patch.object(bridge, "_send"):
        bridge.export_metrics({"cost_usd": 0.05}, span_count=3)
    assert len(received) == 1
    assert isinstance(received[0], ObservabilityExportStarted)
    assert received[0].span_count == 3


# 10. missing otel extra → graceful no-op (no crash)
def test_missing_otel_extra_graceful():
    bridge = ObservabilityBridge(_cfg("always"))
    # _send raises ImportError when otel not installed → export_metrics returns False
    with patch.object(bridge, "_send", side_effect=ImportError("no otel")):
        assert bridge.export_metrics({"cost_usd": 0.05}) is False
