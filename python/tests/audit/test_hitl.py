"""Tests for HITL decision records (ADR-005 audit scaffold)."""

from agent_runtime_cockpit.audit.hitl import (
    HitlDecision,
    HitlPrompt,
    HitlResponse,
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
    from agent_runtime_cockpit.audit.hitl_store import get_token, list_prompts, respond, save_prompt

    prompt = HitlPrompt(
        hitl_id="hitl-store-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt)

    pending = list_prompts(tmp_path)
    assert [item.hitl_id for item in pending] == ["hitl-store-1"]

    token = get_token(tmp_path, "hitl-store-1")
    assert token is not None
    assert len(token) == 32

    response = respond(tmp_path, "hitl-store-1", HitlDecision.APPROVE, token=token, notes="ok")
    assert response is not None
    assert response.decision == HitlDecision.APPROVE
    assert list_prompts(tmp_path) == []


def test_hitl_single_use_token(tmp_path):
    """HITL response rejects reused tokens."""
    from agent_runtime_cockpit.audit.hitl_store import get_token, respond, save_prompt

    prompt = HitlPrompt(
        hitl_id="hitl-single-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt)
    token = get_token(tmp_path, "hitl-single-1")

    response = respond(tmp_path, "hitl-single-1", HitlDecision.APPROVE, token=token)
    assert response is not None

    response2 = respond(tmp_path, "hitl-single-1", HitlDecision.APPROVE, token=token)
    assert response2 is None


def test_hitl_wrong_token_rejected(tmp_path):
    """HITL response rejects wrong token."""
    from agent_runtime_cockpit.audit.hitl_store import respond, save_prompt

    prompt = HitlPrompt(
        hitl_id="hitl-wrong-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt)

    response = respond(tmp_path, "hitl-wrong-1", HitlDecision.APPROVE, token="wrongtoken")
    assert response is None


def test_hitl_expiry(tmp_path):
    """HITL prompts expire after TTL."""
    import time

    from agent_runtime_cockpit.audit.hitl_store import get_token, list_prompts, save_prompt

    prompt = HitlPrompt(
        hitl_id="hitl-expiry-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt, expiry_seconds=0)
    time.sleep(0.01)

    assert list_prompts(tmp_path) == []
    assert get_token(tmp_path, "hitl-expiry-1") is None


def test_hitl_expiry_include_expired(tmp_path):
    """list_prompts(include_expired=True) shows expired prompts."""
    import time

    from agent_runtime_cockpit.audit.hitl_store import list_prompts, save_prompt

    prompt = HitlPrompt(
        hitl_id="hitl-expiry-2",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    )
    save_prompt(tmp_path, prompt, expiry_seconds=0)
    time.sleep(0.01)

    assert list_prompts(tmp_path) == []
    expired = list_prompts(tmp_path, include_expired=True)
    assert len(expired) == 1
    assert expired[0].hitl_id == "hitl-expiry-2"


def test_hitl_prune_expired(tmp_path):
    """prune_expired removes expired prompts."""
    import time

    from agent_runtime_cockpit.audit.hitl_store import prune_expired, save_prompt

    prompt1 = HitlPrompt(hitl_id="hitl-prune-1", run_id="run-1", step_id="step-1", prompt_text="A")
    prompt2 = HitlPrompt(hitl_id="hitl-prune-2", run_id="run-1", step_id="step-1", prompt_text="B")
    save_prompt(tmp_path, prompt1, expiry_seconds=0)
    save_prompt(tmp_path, prompt2, expiry_seconds=3600)
    time.sleep(0.01)

    pruned = prune_expired(tmp_path)
    assert pruned == 1
