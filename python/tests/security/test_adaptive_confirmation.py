"""B2P-08: deterministic high/critical adaptive-confirmation enforcement + audit."""

from __future__ import annotations

import json

from agent_runtime_cockpit.security.adaptive_confirmation import (
    enforce_confirmation,
    evaluate_confirmation,
)


def test_low_medium_does_not_require_confirmation() -> None:
    for level in ("low", "medium"):
        d = evaluate_confirmation(level, hitl_required=False)
        assert d.allowed is True
        assert d.requires_confirmation is False


def test_high_critical_blocked_without_approval() -> None:
    for level in ("high", "critical"):
        d = evaluate_confirmation(level, hitl_required=True)
        assert d.allowed is False
        assert d.requires_confirmation is True
        assert "explicit confirmation" in d.reason


def test_high_critical_allowed_with_explicit_approval() -> None:
    d = evaluate_confirmation("critical", hitl_required=True, approved=True)
    assert d.allowed is True
    assert d.requires_confirmation is True
    assert d.approved is True


def test_hitl_required_forces_confirmation_even_if_level_low() -> None:
    d = evaluate_confirmation("low", hitl_required=True)
    assert d.requires_confirmation is True
    assert d.allowed is False


def test_enforce_writes_audit_for_confirmation_decisions(tmp_path) -> None:
    d = enforce_confirmation(
        "critical", hitl_required=True, decision_id="dec-1", workspace_root=tmp_path
    )
    assert d.allowed is False
    log = tmp_path / ".arc" / "audit" / "adaptive_confirmation.events.jsonl"
    assert log.exists()
    entry = json.loads(log.read_text().strip().splitlines()[-1])
    assert entry["type"] == "adaptive_confirmation"
    assert entry["risk_level"] == "critical"
    assert entry["allowed"] is False
    assert entry["decision_id"] == "dec-1"


def test_enforce_does_not_audit_non_confirmation_decisions(tmp_path) -> None:
    enforce_confirmation("low", hitl_required=False, workspace_root=tmp_path)
    log = tmp_path / ".arc" / "audit" / "adaptive_confirmation.events.jsonl"
    assert not log.exists()  # nothing to confirm → nothing audited
