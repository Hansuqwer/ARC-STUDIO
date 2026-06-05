"""Tests for v0.7 budget broker (cloud/budget_broker.py). 12 cases."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from agent_runtime_cockpit.cloud.budget_broker import (
    BrokerConfig,
    BudgetBrokerClient,
    BudgetBrokerSync,
)
from agent_runtime_cockpit.events import get_bus, reset_bus


def _enabled_cfg(fallback: bool = True) -> BrokerConfig:
    return BrokerConfig(
        broker_url="https://broker.example/team",
        auth_token="tok-123",
        team_id="acme",
        fallback_to_local=fallback,
    )


def _mock_resp(payload: dict):
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode()
    m.__enter__.return_value = m
    m.__exit__.return_value = False
    return m


# 1. disabled when no config
def test_disabled_without_full_config():
    assert not BrokerConfig().enabled
    assert not BrokerConfig(broker_url="x").enabled
    assert not BrokerConfig(broker_url="x", auth_token="y").enabled


# 2. enabled with full config
def test_enabled_with_full_config():
    assert _enabled_cfg().enabled


# 3. disabled broker approves locally
def test_disabled_broker_approves_local():
    r = BudgetBrokerClient(BrokerConfig()).remote_preflight("SESSION", Decimal("1.0"))
    assert r.approved
    assert r.fell_back
    assert r.reason == "broker_disabled"


# 4. remote approves
def test_remote_approves():
    with patch(
        "urllib.request.urlopen", return_value=_mock_resp({"approved": True, "remaining": "50.0"})
    ):
        r = BudgetBrokerClient(_enabled_cfg()).remote_preflight("SESSION", Decimal("1.0"))
    assert r.approved
    assert not r.fell_back
    assert r.remote_remaining == Decimal("50.0")


# 5. remote denies
def test_remote_denies():
    with patch(
        "urllib.request.urlopen", return_value=_mock_resp({"approved": False, "remaining": "0"})
    ):
        r = BudgetBrokerClient(_enabled_cfg()).remote_preflight("SESSION", Decimal("100.0"))
    assert not r.approved


# 6. unreachable + fallback=True → approve
def test_unreachable_with_fallback_approves():
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        r = BudgetBrokerClient(_enabled_cfg(fallback=True)).remote_preflight(
            "SESSION", Decimal("1.0")
        )
    assert r.approved
    assert r.fell_back


# 7. unreachable + fallback=False → DENY (fail-closed)
def test_unreachable_no_fallback_denies():
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        r = BudgetBrokerClient(_enabled_cfg(fallback=False)).remote_preflight(
            "SESSION", Decimal("1.0")
        )
    assert not r.approved
    assert r.reason == "broker_unreachable_no_fallback"


# 8. BudgetBrokerSync event emitted on success
def test_sync_event_emitted():
    reset_bus()
    received = []
    get_bus().subscribe("budget_broker_sync", received.append)
    with patch(
        "urllib.request.urlopen", return_value=_mock_resp({"approved": True, "remaining": "10"})
    ):
        BudgetBrokerClient(_enabled_cfg()).remote_preflight("RUN", Decimal("2.5"))
    assert len(received) == 1
    assert isinstance(received[0], BudgetBrokerSync)
    assert received[0].scope == "RUN"


# 9. event emitted on fallback too
def test_sync_event_on_fallback():
    reset_bus()
    received = []
    get_bus().subscribe("budget_broker_sync", received.append)
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        BudgetBrokerClient(_enabled_cfg(fallback=True)).remote_preflight("SESSION", Decimal("1.0"))
    assert len(received) == 1
    assert received[0].fell_back


# 10. no event when fail-closed deny
def test_no_event_on_failclosed_deny():
    reset_bus()
    received = []
    get_bus().subscribe("budget_broker_sync", received.append)
    with patch("urllib.request.urlopen", side_effect=OSError("down")):
        BudgetBrokerClient(_enabled_cfg(fallback=False)).remote_preflight("SESSION", Decimal("1.0"))
    assert received == []


# 11. request carries no prompt/code data
def test_request_carries_only_scope_and_amount():
    captured = []

    def fake(req, timeout=None):
        captured.append(json.loads(req.data))
        return _mock_resp({"approved": True, "remaining": "5"})

    with patch("urllib.request.urlopen", side_effect=fake):
        BudgetBrokerClient(_enabled_cfg()).remote_preflight("SESSION", Decimal("1.0"))
    body = captured[0]
    assert set(body.keys()) == {"team_id", "scope", "amount"}
    assert "prompt" not in body
    assert "messages" not in body


# 12. from_env wiring
def test_from_env(monkeypatch):
    monkeypatch.setenv("ARC_BUDGET_BROKER_URL", "https://b.example")
    monkeypatch.setenv("ARC_BUDGET_BROKER_TOKEN", "tok")
    monkeypatch.setenv("ARC_BUDGET_TEAM_ID", "team1")
    cfg = BrokerConfig.from_env()
    assert cfg.enabled
    assert cfg.team_id == "team1"
