"""Tests for T5 (Phase 8): EgressGuard — deterministic budget-bound egress control."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.mobile import EgressGuard, MobileDataSensitivity


def test_under_budget_allowed_and_recorded() -> None:
    g = EgressGuard(budget_bytes=1000)
    d = g.record(400, MobileDataSensitivity.LOW)
    assert d.allowed and d.byte_cost == 400 and d.remaining_bytes == 600
    assert g.usage()["used_total"] == 400


def test_over_budget_denied_deterministically() -> None:
    g = EgressGuard(budget_bytes=1000)
    assert g.record(800, "low").allowed
    d = g.record(500, "low")
    assert d.allowed is False and "over overall egress budget" in d.reason
    assert d.deterministic is True
    assert g.usage()["used_total"] == 800  # denied egress not counted


def test_per_class_limit_enforced() -> None:
    g = EgressGuard(budget_bytes=10_000, per_class_limits={"medium": 100})
    assert g.record(100, "medium").allowed
    d = g.record(1, "medium")
    assert d.allowed is False and "per-class budget" in d.reason


def test_critical_classification_blocked_by_default() -> None:
    g = EgressGuard(budget_bytes=10_000)
    d = g.record(1, MobileDataSensitivity.CRITICAL)
    assert d.allowed is False and "blocked from egress" in d.reason
    assert g.usage()["used_total"] == 0


def test_negative_cost_denied() -> None:
    g = EgressGuard(budget_bytes=1000)
    assert g.record(-5, "low").allowed is False


def test_check_is_pure_no_mutation() -> None:
    g = EgressGuard(budget_bytes=1000)
    g.check(500, "low")
    g.check(500, "low")
    assert g.usage()["used_total"] == 0  # check never mutates


def test_budget_validation() -> None:
    with pytest.raises(ValueError):
        EgressGuard(budget_bytes=-1)
