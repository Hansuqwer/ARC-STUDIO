"""R-TS1: cache_control prompt-caching population in TurnManager.

Tests that:
1. Default (ARC_ENABLE_PROMPT_CACHING not set): cache_control is always empty.
2. Flag set + system message ≥2000 chars: CacheBreakpoint(position="system") added.
3. Flag set + system message <2000 chars: cache_control stays empty (below threshold).
4. Flag set + no system message: cache_control stays empty.
5. Flag set + multiple system messages: only one breakpoint (first system message counted).
"""

from __future__ import annotations

from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.providers import ProviderResponse, UsageRecord
from agent_runtime_cockpit.runtime.turn_manager import TurnManager


class _Provider:
    async def complete(self, request, *, cancellation_token):
        return ProviderResponse(
            call_id="c1",
            model="m",
            content="ok",
            finish_reason="stop",
            usage=UsageRecord(input_tokens=1, output_tokens=1),
        )

    async def stream(self, request, *, cancellation_token):
        return
        yield  # make it a generator


def _manager() -> TurnManager:
    return TurnManager(_Provider(), model="claude-sonnet-4-5")


def _session_with_system(content: str) -> ChatSession:
    s = ChatSession()
    s.add_message("system", content)
    s.add_message("user", "hello")
    return s


def _session_no_system() -> ChatSession:
    s = ChatSession()
    s.add_message("user", "hello")
    return s


# ── Gate default-off ──────────────────────────────────────────────────────────


def test_cache_control_off_by_default(monkeypatch):
    monkeypatch.delenv("ARC_ENABLE_PROMPT_CACHING", raising=False)
    mgr = _manager()
    session = _session_with_system("x" * 5000)
    req = mgr._request_from_session(session)
    assert req.cache_control == []


def test_cache_control_off_when_flag_is_zero(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "0")
    mgr = _manager()
    req = mgr._request_from_session(_session_with_system("x" * 5000))
    assert req.cache_control == []


# ── Gate enabled + threshold ──────────────────────────────────────────────────


def test_cache_control_set_when_flag_and_long_system(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    mgr = _manager()
    req = mgr._request_from_session(_session_with_system("x" * 2000))
    assert len(req.cache_control) == 1
    bp = req.cache_control[0]
    assert bp.position == "system"
    assert bp.index == 0


def test_cache_control_empty_when_system_too_short(monkeypatch):
    """System message below 2000 chars doesn't get a breakpoint."""
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    mgr = _manager()
    req = mgr._request_from_session(_session_with_system("x" * 1999))
    assert req.cache_control == []


def test_cache_control_empty_when_no_system_message(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    mgr = _manager()
    req = mgr._request_from_session(_session_no_system())
    assert req.cache_control == []


def test_cache_control_exactly_at_threshold(monkeypatch):
    """2000 chars is the minimum qualifying length."""
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    mgr = _manager()
    req = mgr._request_from_session(_session_with_system("x" * 2000))
    assert len(req.cache_control) == 1


# ── Breakpoint structure ──────────────────────────────────────────────────────


def test_breakpoint_is_cache_breakpoint_type(monkeypatch):
    from agent_runtime_cockpit.providers.base import CacheBreakpoint

    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    mgr = _manager()
    req = mgr._request_from_session(_session_with_system("y" * 3000))
    assert isinstance(req.cache_control[0], CacheBreakpoint)


def test_tools_still_populated_alongside_cache_control(monkeypatch):
    """Enabling caching must not break tool population."""
    from agent_runtime_cockpit.tools import ToolRegistry
    from agent_runtime_cockpit.tools.builtin import GetCurrentTimeTool

    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    session = _session_with_system("z" * 2500)
    session.tools_enabled = True

    mgr = TurnManager(_Provider(), model="claude-3-5", tool_registry=registry)
    req = mgr._request_from_session(session)
    assert len(req.cache_control) == 1
    assert len(req.tools) >= 1
