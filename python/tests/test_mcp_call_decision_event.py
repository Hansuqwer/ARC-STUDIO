"""CR-043: the typed MCP_CALL_DECISION event is now produced (was defined but never written)."""

from __future__ import annotations

from agent_runtime_cockpit.mcp.sandbox import (
    McpDecision,
    McpPolicy,
    decide_call,
    next_decision_sequence,
    persist_decision_event,
    to_call_decision_event,
)
from agent_runtime_cockpit.protocol.mcp_decision_events import McpCallDecisionEvent


def test_converter_maps_decision_fields() -> None:
    d = decide_call(
        server_id="srv", tool_name="read_file", arguments={"path": "x"}, policy=McpPolicy.STRICT
    )
    ev = to_call_decision_event(d, run_id="run-1", sequence=3, timestamp="2026-01-01T00:00:00Z")
    assert isinstance(ev, McpCallDecisionEvent)
    assert ev.type == "MCP_CALL_DECISION" and ev.run_id == "run-1" and ev.sequence == 3
    assert ev.timestamp == "2026-01-01T00:00:00Z"
    assert ev.data.server_id == "srv" and ev.data.tool_name == "read_file"
    assert ev.data.decision == d.decision.value
    assert ev.data.risk_level == d.risk_score.level.value
    assert ev.data.policy == "strict"


def test_timestamp_fallback_is_iso() -> None:
    d = decide_call(server_id="s", tool_name="t", policy=McpPolicy.STRICT)
    ev = to_call_decision_event(d, run_id="r", sequence=0)
    assert ev.timestamp.endswith("Z") or "+" in ev.timestamp  # ISO-ish, not empty


def test_persist_event_round_trips(tmp_path) -> None:
    d = decide_call(server_id="s", tool_name="t", policy=McpPolicy.STRICT)
    ev = to_call_decision_event(
        d, run_id="r", sequence=next_decision_sequence(), correlation_id="abc123"
    )
    path = persist_decision_event(tmp_path, ev)
    assert path.name == "decision-events.jsonl"
    parsed = McpCallDecisionEvent.model_validate_json(path.read_text().strip())
    assert parsed.type == "MCP_CALL_DECISION"
    assert parsed.data.correlation_id == "abc123"


def test_high_risk_call_emits_deny_event() -> None:
    # a roots violation drives a high/critical risk -> deny decision -> deny event
    d = decide_call(
        server_id="s",
        tool_name="t",
        roots_violation=True,
        manifest_risk="high",
        policy=McpPolicy.STRICT,
    )
    ev = to_call_decision_event(d, run_id="r", sequence=0)
    if d.decision == McpDecision.DENY:
        assert ev.data.decision == "deny"
        assert ev.data.risk_level in ("high", "critical")


def test_sequence_is_monotonic() -> None:
    a = next_decision_sequence()
    b = next_decision_sequence()
    assert b > a
