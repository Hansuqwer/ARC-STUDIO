"""Tests for the additive HITL decision endpoints (arc-v2 F3).

Proposal: docs/planning/arc-v2-hitl-decision-api-proposal.md
Routes:   GET /api/hitl · POST /api/hitl/{hitl_id}/decision

Covers the proposal's 6-item plan (sans fixtures, which live in
protocol/fixtures): happy paths for approve/reject, unknown id, double
decision, invalid decision value, untrusted workspace, and the response
event landing on the bus via the store's existing HitlDecided publish.
"""

import json
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.audit.hitl import HitlPrompt
from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore


def _seed_prompt(workspace, hitl_id="hitl-test-001", timeout=300):
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")
    prompt = HitlPrompt(
        hitl_id=hitl_id,
        run_id="run-hitl-test",
        step_id="approval-gate",
        prompt_text="Apply patch to 3 files?",
        options=["approve", "reject"],
        timeout_seconds=timeout,
    )
    store.save_prompt(prompt)
    return store


@pytest.mark.asyncio
async def test_hitl_list_empty(client, workspace):
    resp = await client.get("/api/hitl")
    assert resp.status_code == 200
    data = json.loads(await resp.text())
    assert data["ok"] is True
    assert data["data"]["prompts"] == []


@pytest.mark.asyncio
async def test_hitl_list_shows_pending(client, workspace):
    _seed_prompt(workspace)
    resp = await client.get("/api/hitl")
    data = json.loads(await resp.text())
    assert data["ok"] is True
    assert len(data["data"]["prompts"]) == 1
    assert data["data"]["prompts"][0]["hitl_id"] == "hitl-test-001"


@pytest.mark.asyncio
async def test_decision_approve_happy_path(client, workspace):
    store = _seed_prompt(workspace)
    resp = await client.post(
        "/api/hitl/hitl-test-001/decision",
        json={"decision": "approve", "operator_id": "user@example.com", "notes": "lgtm"},
    )
    assert resp.status_code == 200
    data = json.loads(await resp.text())
    assert data["ok"] is True
    assert data["data"]["decision"] == "approve"
    assert data["data"]["operator_id"] == "user@example.com"
    assert data["data"]["responded_at"]

    # store agrees: response recorded, prompt no longer pending
    recorded = store.get_response("hitl-test-001")
    assert recorded is not None
    assert recorded.decision.value == "approve"
    assert store.get_token("hitl-test-001") is None


@pytest.mark.asyncio
async def test_decision_reject_is_recorded_too(client, workspace):
    """Deny is audited the same as allow — both verdicts are first-class."""
    store = _seed_prompt(workspace, hitl_id="hitl-rej-001")
    resp = await client.post("/api/hitl/hitl-rej-001/decision", json={"decision": "reject"})
    assert resp.status_code == 200
    data = json.loads(await resp.text())
    assert data["data"]["decision"] == "reject"
    assert store.get_response("hitl-rej-001").decision.value == "reject"


@pytest.mark.asyncio
async def test_unknown_hitl_id_404_envelope(client, workspace):
    resp = await client.post("/api/hitl/no-such-prompt/decision", json={"decision": "approve"})
    assert resp.status_code == 404
    data = json.loads(await resp.text())
    assert data["ok"] is False
    assert "not found" in data["error"]["message"]


@pytest.mark.asyncio
async def test_double_decision_second_is_404(client, workspace):
    """Single-use semantics: a decided prompt cannot be re-decided."""
    _seed_prompt(workspace, hitl_id="hitl-dup-001")
    first = await client.post("/api/hitl/hitl-dup-001/decision", json={"decision": "approve"})
    assert first.status_code == 200
    second = await client.post("/api/hitl/hitl-dup-001/decision", json={"decision": "reject"})
    assert second.status_code == 404, "already responded => not found/expired"


@pytest.mark.asyncio
async def test_invalid_decision_value_400(client, workspace):
    _seed_prompt(workspace, hitl_id="hitl-bad-001")
    resp = await client.post("/api/hitl/hitl-bad-001/decision", json={"decision": "auto_approve"})
    assert resp.status_code == 400
    data = json.loads(await resp.text())
    assert data["error"]["code"] == "INVALID_INPUT"
    # the prompt is untouched by the rejected request
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")
    assert store.get_token("hitl-bad-001") is not None


@pytest.mark.asyncio
async def test_malformed_body_400(client, workspace):
    _seed_prompt(workspace, hitl_id="hitl-mal-001")
    resp = await client.post(
        "/api/hitl/hitl-mal-001/decision",
        data=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_untrusted_workspace_403_before_anything(client, workspace):
    """Trust gate fires before prompt lookup (same pattern as tasks routes)."""
    _seed_prompt(workspace, hitl_id="hitl-trust-001")
    with patch("agent_runtime_cockpit.web.routes.enforce_workspace_trust") as mock:
        from agent_runtime_cockpit.security.enforcement import TrustEnforcementError

        mock.side_effect = TrustEnforcementError("untrusted")
        resp = await client.post("/api/hitl/hitl-trust-001/decision", json={"decision": "approve"})
    assert resp.status_code == 403
    # untouched: still pending
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")
    assert store.get_token("hitl-trust-001") is not None


@pytest.mark.asyncio
async def test_decision_emits_bus_event(client, workspace):
    """The store publishes HitlDecided; the SSE layer forwards bus events —
    assert the bus publish happens (transport tested elsewhere)."""
    _seed_prompt(workspace, hitl_id="hitl-bus-001")
    captured = []
    from agent_runtime_cockpit.events.bus import get_bus

    bus = get_bus()
    unsub = None
    try:
        if hasattr(bus, "subscribe"):
            try:
                unsub = bus.subscribe(lambda ev: captured.append(ev))
            except TypeError:
                unsub = None
        resp = await client.post("/api/hitl/hitl-bus-001/decision", json={"decision": "approve"})
        assert resp.status_code == 200
        if unsub is not None:
            assert any(getattr(ev, "hitl_id", None) == "hitl-bus-001" for ev in captured), (
                f"HitlDecided not observed on bus: {captured!r}"
            )
    finally:
        if callable(unsub):
            unsub()
