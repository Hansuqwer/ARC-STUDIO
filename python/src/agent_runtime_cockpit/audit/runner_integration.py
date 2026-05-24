"""Unified audit integration for adapter runners.

Consolidates the AGUI-to-audit-session mapping logic that was previously
duplicated across CrewAI, LangGraph, and SwarmGraph adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_runtime_cockpit.ag_ui import AGUIEventType

if TYPE_CHECKING:
    from agent_runtime_cockpit.audit.session import AuditSession


def log_agui_to_audit(session: AuditSession, agui_event: dict[str, Any]) -> None:
    """Map AG-UI events to typed audit events.

    Runs inline alongside the existing SHA-256 audit chain. Not all AG-UI
    events have typed equivalents; unrecognized types are silently skipped.

    Args:
        session: Active audit session to log events to
        agui_event: AG-UI event dictionary with 'type' field

    Example:
        >>> async with AuditSession(run_id="abc123", store=store) as session:
        ...     for agui_event in events:
        ...         log_agui_to_audit(session, agui_event)

    """
    event_type = agui_event.get("type", "")

    if event_type == AGUIEventType.TOOL_CALL_START.value:
        session.log_tool_call(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            arguments=agui_event.get("args", {}),
            trust_level=agui_event.get("trust_level", "untrusted"),
        )
    elif event_type == AGUIEventType.TOOL_CALL_RESULT.value:
        session.log_tool_result(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            result=agui_event.get("result", {}),
            trust_level=agui_event.get("trust_level", "untrusted"),
        )
    elif event_type == AGUIEventType.TOOL_CALL_ERROR.value:
        session.log_tool_result(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            trust_level=agui_event.get("trust_level", "untrusted"),
            error={"code": "AGUI_TOOL_ERROR", "message": str(agui_event.get("error", ""))},
        )
