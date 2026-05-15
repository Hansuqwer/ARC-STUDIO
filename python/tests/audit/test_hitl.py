"""Tests for HITL decision records (ADR-005 audit scaffold)."""
import pytest
from agent_runtime_cockpit.audit.hitl import (
    HitlPrompt,
    HitlResponse,
    HitlDecision,
)


def test_hitl_prompt_defaults():
    prompt = HitlPrompt(
        hitl_id="hitl-001",
        run_id="run-001",
        step_id="step-1",
        prompt_text="Approve this tool call?",
    )
    assert prompt.timeout_seconds == 300
    assert prompt.options == ["approve", "reject", "modify", "skip"]


def test_hitl_response_to_audit_event():
    response = HitlResponse(
        hitl_id="hitl-001",
        run_id="run-001",
        decision=HitlDecision.APPROVE,
        operator_id="user-1",
    )
    event = response.to_audit_event()
    assert event["type"] == "hitl_decision"
    assert event["decision"] == "approve"
    assert event["operator_id"] == "user-1"
