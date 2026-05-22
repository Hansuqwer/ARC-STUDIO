"""Tests for unified audit runner integration."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.ag_ui import AGUIEventType
from agent_runtime_cockpit.audit.runner_integration import log_agui_to_audit


@pytest.fixture
def mock_session():
    """Create a mock audit session."""
    session = Mock()
    session.log_tool_call = Mock()
    session.log_tool_result = Mock()
    return session


def test_log_tool_call_start(mock_session):
    """Test that TOOL_CALL_START events are correctly logged."""
    agui_event = {
        "type": AGUIEventType.TOOL_CALL_START.value,
        "tool_name": "search",
        "tool_id": "tool-123",
        "args": {"query": "test"},
        "trust_level": "trusted",
    }

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_call.assert_called_once_with(
        tool_name="search",
        tool_id="tool-123",
        arguments={"query": "test"},
        trust_level="trusted",
    )
    mock_session.log_tool_result.assert_not_called()


def test_log_tool_call_result(mock_session):
    """Test that TOOL_CALL_RESULT events are correctly logged."""
    agui_event = {
        "type": AGUIEventType.TOOL_CALL_RESULT.value,
        "tool_name": "search",
        "tool_id": "tool-123",
        "result": {"data": "found"},
        "trust_level": "trusted",
    }

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_result.assert_called_once_with(
        tool_name="search",
        tool_id="tool-123",
        result={"data": "found"},
        trust_level="trusted",
    )
    mock_session.log_tool_call.assert_not_called()


def test_log_tool_call_error(mock_session):
    """Test that TOOL_CALL_ERROR events are correctly logged."""
    agui_event = {
        "type": AGUIEventType.TOOL_CALL_ERROR.value,
        "tool_name": "search",
        "tool_id": "tool-123",
        "error": "Connection timeout",
        "trust_level": "untrusted",
    }

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_result.assert_called_once_with(
        tool_name="search",
        tool_id="tool-123",
        trust_level="untrusted",
        error={"code": "AGUI_TOOL_ERROR", "message": "Connection timeout"},
    )
    mock_session.log_tool_call.assert_not_called()


def test_unknown_event_type_ignored(mock_session):
    """Test that unknown event types are silently ignored."""
    agui_event = {
        "type": "unknown.event.type",
        "data": "should be ignored",
    }

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_call.assert_not_called()
    mock_session.log_tool_result.assert_not_called()


def test_missing_type_field_ignored(mock_session):
    """Test that events without 'type' field are silently ignored."""
    agui_event = {"data": "no type field"}

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_call.assert_not_called()
    mock_session.log_tool_result.assert_not_called()


def test_default_values_used_when_fields_missing(mock_session):
    """Test that default values are used when optional fields are missing."""
    agui_event = {
        "type": AGUIEventType.TOOL_CALL_START.value,
        # Missing tool_name, tool_id, args, trust_level
    }

    log_agui_to_audit(mock_session, agui_event)

    mock_session.log_tool_call.assert_called_once_with(
        tool_name="",
        tool_id="",
        arguments={},
        trust_level="untrusted",
    )
