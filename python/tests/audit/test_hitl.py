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


def test_hitl_store_pending_and_response(tmp_path):
    from agent_runtime_cockpit.audit.hitl_store import save_prompt, list_prompts, respond

    prompt = HitlPrompt(
        hitl_id="hitl-store-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt)

    pending = list_prompts(tmp_path)
    assert [item.hitl_id for item in pending] == ["hitl-store-1"]

    response = respond(tmp_path, "hitl-store-1", HitlDecision.APPROVE, notes="ok")
    assert response is not None
    assert response.decision == HitlDecision.APPROVE
    assert list_prompts(tmp_path) == []
