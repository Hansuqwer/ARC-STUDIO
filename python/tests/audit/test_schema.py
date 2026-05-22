"""Tests for audit event schema (ADR-021)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.audit.schema import (
    AuditEventType,
    BudgetDecisionEvent,
    LlmRequestEvent,
    LlmResponseEvent,
    RunCancelledEvent,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    RuntimeMode,
    StopReason,
    ToolCallEvent,
    ToolResultEvent,
    TrustLevel,
    event_from_dict,
)


class TestEventTypes:
    def test_llm_request_event(self):
        event = LlmRequestEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            temperature=0.7,
        )
        assert event.event_type == AuditEventType.llm_request
        d = event.to_audit_event()
        assert d["type"] == "llm_request"
        assert d["provider"] == "anthropic"
        assert d["model"] == "claude-3-5-sonnet-20241022"
        assert d["max_tokens"] == 4096
        assert d["temperature"] == 0.7

    def test_llm_response_event_with_cost(self):
        event = LlmResponseEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
            response_id="msg_123",
            stop_reason=StopReason.end_turn,
            usage={"input_tokens": 100, "output_tokens": 50},
            total_cost=Decimal("0.00123"),
            measured=True,
        )
        assert event.event_type == AuditEventType.llm_response
        d = event.to_audit_event()
        assert d["type"] == "llm_response"
        assert d["stop_reason"] == "end_turn"
        assert d["cost"]["total_cost"] == "0.00123"
        assert d["cost"]["measured"] is True

    def test_llm_response_event_without_cost(self):
        event = LlmResponseEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
        )
        d = event.to_audit_event()
        assert d["cost"] is None

    def test_tool_call_event(self):
        event = ToolCallEvent(
            run_id="run_abc",
            tool_name="read_file",
            tool_id="toolu_123",
            arguments={"path": "/tmp/test.txt"},
            trust_level=TrustLevel.untrusted,
        )
        assert event.event_type == AuditEventType.tool_call
        d = event.to_audit_event()
        assert d["type"] == "tool_call"
        assert d["tool_name"] == "read_file"
        assert d["trust_level"] == "untrusted"

    def test_tool_result_event_success(self):
        event = ToolResultEvent(
            run_id="run_abc",
            tool_name="read_file",
            tool_id="toolu_123",
            result={"content": "file contents"},
            trust_level=TrustLevel.untrusted,
        )
        d = event.to_audit_event()
        assert d["type"] == "tool_result"
        assert d["error"] is None

    def test_tool_result_event_error(self):
        event = ToolResultEvent(
            run_id="run_abc",
            tool_name="read_file",
            tool_id="toolu_123",
            trust_level=TrustLevel.trusted,
            error={"code": "NOT_FOUND", "message": "File not found"},
        )
        d = event.to_audit_event()
        assert d["error"]["code"] == "NOT_FOUND"

    def test_budget_decision_allowed(self):
        event = BudgetDecisionEvent(
            run_id="run_abc",
            decision="allowed",
            reason="within budget",
            budget_state={"run_budget_remaining": "1.50"},
        )
        d = event.to_audit_event()
        assert d["decision"] == "allowed"
        assert d["reason"] == "within budget"

    def test_budget_decision_blocked(self):
        event = BudgetDecisionEvent(
            run_id="run_abc", decision="blocked", reason="budget exhausted"
        )
        d = event.to_audit_event()
        assert d["decision"] == "blocked"

    def test_run_started_event(self):
        event = RunStartedEvent(
            run_id="run_abc",
            runtime="swarmgraph",
            mode=RuntimeMode.provider_backed,
            profile="default",
            isolation="subprocess",
        )
        d = event.to_audit_event()
        assert d["type"] == "run_started"
        assert d["mode"] == "provider_backed"

    def test_run_completed_event(self):
        event = RunCompletedEvent(run_id="run_abc", runtime="swarmgraph")
        d = event.to_audit_event()
        assert d["type"] == "run_completed"

    def test_run_failed_event(self):
        event = RunFailedEvent(
            run_id="run_abc", runtime="swarmgraph", reason="provider error"
        )
        d = event.to_audit_event()
        assert d["type"] == "run_failed"
        assert d["reason"] == "provider error"

    def test_run_cancelled_event(self):
        event = RunCancelledEvent(
            run_id="run_abc", runtime="swarmgraph", reason="user cancelled"
        )
        d = event.to_audit_event()
        assert d["type"] == "run_cancelled"
        assert d["reason"] == "user cancelled"


class TestEventFromDict:
    def test_roundtrip_llm_request(self):
        original = LlmRequestEvent(
            run_id="run_abc",
            provider="anthropic",
            model="claude-3-5-sonnet-20241022",
        )
        d = original.to_audit_event()
        reconstructed = event_from_dict(d)
        assert isinstance(reconstructed, LlmRequestEvent)
        assert reconstructed.run_id == "run_abc"
        assert reconstructed.provider == "anthropic"

    def test_roundtrip_tool_result(self):
        original = ToolResultEvent(
            run_id="run_abc",
            tool_name="read_file",
            error={"code": "NOT_FOUND", "message": "File not found"},
        )
        d = original.to_audit_event()
        reconstructed = event_from_dict(d)
        assert isinstance(reconstructed, ToolResultEvent)
        assert reconstructed.error["code"] == "NOT_FOUND"

    def test_unknown_event_type_raises(self):
        with pytest.raises(ValueError, match="Unknown audit event type"):
            event_from_dict({"type": "nonexistent", "run_id": "run_abc"})

    def test_missing_type_raises(self):
        with pytest.raises(ValueError, match="missing 'type' field"):
            event_from_dict({"run_id": "run_abc"})


class TestEventTimestamps:
    def test_default_timestamp_is_iso_format(self):
        event = LlmRequestEvent(run_id="run_abc", provider="test", model="test")
        assert "T" in event.timestamp
        assert event.timestamp.endswith("Z") or "+" in event.timestamp

    def test_custom_timestamp(self):
        event = LlmRequestEvent(
            run_id="run_abc",
            provider="test",
            model="test",
            timestamp="2026-05-21T23:30:00.000Z",
        )
        assert event.timestamp == "2026-05-21T23:30:00.000Z"
