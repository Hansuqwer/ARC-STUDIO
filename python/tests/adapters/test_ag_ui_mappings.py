"""Tests for AG-UI mapper registration for letta, strands, pydantic_ai adapters."""

from __future__ import annotations

import agent_runtime_cockpit.adapters.letta  # noqa: F401 — triggers registration
import agent_runtime_cockpit.adapters.strands  # noqa: F401
import agent_runtime_cockpit.adapters.pydantic_ai_adapter  # noqa: F401

from agent_runtime_cockpit.ag_ui import MappingContext, map_event, AGUIEventType


def _ctx(run_id: str = "r1") -> MappingContext:
    return MappingContext(thread_id="t1", run_id=run_id, runtime="test")


# ─── letta ────────────────────────────────────────────────────────────────────


def test_letta_run_started():
    events = map_event("letta", {"type": "LETTA_RUN_START", "data": {}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_STARTED.value for e in events)


def test_letta_run_finished():
    events = map_event("letta", {"type": "LETTA_RUN_END", "data": {"output": "hi"}}, _ctx())
    types = [e["type"] for e in events]
    assert AGUIEventType.RUN_FINISHED.value in types
    assert AGUIEventType.TEXT_MESSAGE_CONTENT.value in types


def test_letta_run_error():
    events = map_event("letta", {"type": "LETTA_RUN_ERROR", "data": {"error": "boom"}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_ERROR.value for e in events)


# ─── strands ──────────────────────────────────────────────────────────────────


def test_strands_run_started():
    events = map_event("strands", {"type": "STRANDS_RUN_START", "data": {}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_STARTED.value for e in events)


def test_strands_run_finished():
    events = map_event("strands", {"type": "STRANDS_RUN_END", "data": {"output": "answer"}}, _ctx())
    types = [e["type"] for e in events]
    assert AGUIEventType.RUN_FINISHED.value in types
    assert AGUIEventType.TEXT_MESSAGE_CONTENT.value in types


def test_strands_run_error():
    events = map_event("strands", {"type": "STRANDS_RUN_ERROR", "data": {"error": "fail"}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_ERROR.value for e in events)


# ─── pydantic-ai ──────────────────────────────────────────────────────────────


def test_pydantic_ai_run_started():
    events = map_event("pydantic-ai", {"type": "AGENT_RUN_START", "data": {}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_STARTED.value for e in events)


def test_pydantic_ai_run_finished():
    events = map_event("pydantic-ai", {"type": "AGENT_RUN_END", "data": {"result": "ok"}}, _ctx())
    types = [e["type"] for e in events]
    assert AGUIEventType.RUN_FINISHED.value in types


def test_pydantic_ai_run_error():
    events = map_event("pydantic-ai", {"type": "AGENT_RUN_ERROR", "data": {"error": "err"}}, _ctx())
    assert any(e["type"] == AGUIEventType.RUN_ERROR.value for e in events)


def test_pydantic_ai_tool_call():
    events = map_event(
        "pydantic-ai", {"type": "TOOL_CALL", "data": {"tool_name": "search"}}, _ctx()
    )
    assert any(e["type"] == AGUIEventType.TOOL_CALL_START.value for e in events)
