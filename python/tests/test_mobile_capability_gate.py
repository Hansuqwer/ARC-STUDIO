"""Tests for Phase 11: native capability entry-gate (default-denied, fixtures-only)."""

from __future__ import annotations

from agent_runtime_cockpit.mobile import (
    CapabilityEntryGate,
    FeatureFlags,
    FIXTURES_ROUTE,
)
from agent_runtime_cockpit.mobile.approval import clear_grants, issue_grant, revoke_grant
from agent_runtime_cockpit.mobile.signing import sign_plan
from agent_runtime_cockpit.mobile.models import MobileActionPlan

KEY = b"k" * 32
CAP = "device.camera.capture.mock"


def _signed_plan():
    return sign_plan(MobileActionPlan(plan_id="p1", steps=[]), KEY)


def _gate(flag_on: bool = True, kill: bool = False) -> CapabilityEntryGate:
    flags = FeatureFlags(kill_switch=kill)
    if flag_on:
        flags.enable(f"native.{CAP}")
    return CapabilityEntryGate(flags, KEY)


def _eligible_kwargs():
    clear_grants()
    grant = issue_grant(CAP, "execute:once", 300)
    return {"signed_plan": _signed_plan(), "grant_id": grant.grant_id, "compliance_present": True}


def test_default_denied_with_nothing() -> None:
    d = _gate(flag_on=False).evaluate(CAP)
    assert d.eligible is False
    assert "feature_flag_off_or_kill_switch_engaged" in d.missing
    assert "signed_plan_invalid" in d.missing
    assert "approval_grant_invalid" in d.missing
    assert "compliance_artifact_missing" in d.missing
    assert d.route == FIXTURES_ROUTE


def test_all_criteria_met_is_eligible_but_still_fixtures() -> None:
    d = _gate().evaluate(CAP, **_eligible_kwargs())
    assert d.eligible is True and d.missing == []
    assert d.route == FIXTURES_ROUTE  # never real device


def test_execute_never_reaches_real_device_even_when_eligible() -> None:
    out = _gate().execute(CAP, **_eligible_kwargs())
    assert out["route"] == FIXTURES_ROUTE
    assert out["executed_real_device"] is False
    assert out["eligible"] is True


def test_kill_switch_denies_even_with_flag_on() -> None:
    d = _gate(flag_on=True, kill=True).evaluate(CAP, **_eligible_kwargs())
    assert d.eligible is False
    assert "feature_flag_off_or_kill_switch_engaged" in d.missing


def test_each_missing_requirement_denies() -> None:
    gate = _gate()
    base = _eligible_kwargs()
    # bad signature
    bad_sig = base | {"signed_plan": None}
    assert "signed_plan_invalid" in gate.evaluate(CAP, **bad_sig).missing
    # missing compliance
    assert (
        "compliance_artifact_missing"
        in gate.evaluate(CAP, **(base | {"compliance_present": False})).missing
    )
    # revoked grant
    revoke_grant(base["grant_id"])
    assert "approval_grant_invalid" in gate.evaluate(CAP, **base).missing


def test_grant_for_other_capability_rejected() -> None:
    clear_grants()
    grant = issue_grant("device.location.current.mock", "execute:once", 300)
    d = _gate().evaluate(
        CAP, signed_plan=_signed_plan(), grant_id=grant.grant_id, compliance_present=True
    )
    assert "approval_grant_invalid" in d.missing
