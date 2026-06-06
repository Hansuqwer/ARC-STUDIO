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
    # Both system AND tools breakpoints are added; tools are populated.
    assert len(req.cache_control) >= 1
    assert len(req.tools) >= 1


# ── Tools breakpoint (breakpoint 1 of 4) ─────────────────────────────────────


def test_tools_breakpoint_added_when_flag_and_tools(monkeypatch):
    from agent_runtime_cockpit.providers.base import CacheBreakpoint
    from agent_runtime_cockpit.tools import ToolRegistry
    from agent_runtime_cockpit.tools.builtin import GetCurrentTimeTool

    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    session = _session_with_system("s" * 2500)
    session.tools_enabled = True

    mgr = TurnManager(_Provider(), model="claude-3-5", tool_registry=registry)
    req = mgr._request_from_session(session)
    positions = [bp.position for bp in req.cache_control]
    assert "tools" in positions
    assert all(isinstance(bp, CacheBreakpoint) for bp in req.cache_control)


def test_tools_breakpoint_not_added_when_no_tools(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    session = _session_with_system("t" * 2500)
    # tools_enabled but no registry → no tools → no tools breakpoint
    req = _manager()._request_from_session(session)
    positions = [bp.position for bp in req.cache_control]
    assert "tools" not in positions


def test_both_system_and_tools_breakpoints_present(monkeypatch):
    from agent_runtime_cockpit.tools import ToolRegistry
    from agent_runtime_cockpit.tools.builtin import GetCurrentTimeTool

    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    session = _session_with_system("u" * 2500)
    session.tools_enabled = True

    mgr = TurnManager(_Provider(), model="claude-3-5", tool_registry=registry)
    req = mgr._request_from_session(session)
    positions = {bp.position for bp in req.cache_control}
    assert positions == {"system", "tools"}


# ── Wallet cache token display ────────────────────────────────────────────────


def test_store_context_metadata_accumulates_cache_tokens():
    """_store_context_metadata increments session cache_tokens on each call."""
    from unittest.mock import MagicMock
    from agent_runtime_cockpit.cli_repl.slash_commands import _store_context_metadata

    capability = MagicMock()
    capability.max_context_tokens = 100_000
    session = MagicMock()
    session.metadata = {}

    _store_context_metadata(
        session,
        capability,
        {
            "available": True,
            "input_tokens": 100,
            "cache_read_input_tokens": 50,
            "cache_creation_input_tokens": 20,
        },
    )
    assert session.metadata["cache_tokens"]["read"] == 50
    assert session.metadata["cache_tokens"]["write"] == 20

    # Second call: accumulates
    _store_context_metadata(
        session,
        capability,
        {
            "available": True,
            "input_tokens": 80,
            "cache_read_input_tokens": 30,
            "cache_creation_input_tokens": 0,
        },
    )
    assert session.metadata["cache_tokens"]["read"] == 80
    assert session.metadata["cache_tokens"]["write"] == 20


def test_wallet_shows_cache_line_when_cache_tokens_present():
    """cmd_wallet includes a cache line when session.metadata has cache_tokens."""
    from unittest.mock import MagicMock, patch
    from agent_runtime_cockpit.cli_repl.slash_commands import cmd_wallet
    from agent_runtime_cockpit.cli_repl.session import ChatSession

    session = ChatSession()
    session.metadata = {"cache_tokens": {"read": 1500, "write": 200}}

    fake_snap = MagicMock()
    fake_snap.fail_closed_reason = None
    fake_snap.first_launch = False
    fake_snap.balances = {}

    with (
        patch("agent_runtime_cockpit.cli_repl.slash_commands._session_budget_enforcer") as mock_enf,
        patch("agent_runtime_cockpit.budget.wallet.TokenWallet.snapshot", return_value=fake_snap),
    ):
        mock_wallet = MagicMock()
        mock_wallet.snapshot.return_value = fake_snap
        mock_enf.return_value = MagicMock()

        result = cmd_wallet("", session)

    assert result.state == "present"
    assert "cache" in result.output.lower()
    assert "1,500" in result.output


def test_wallet_no_cache_line_when_no_cache_tokens():
    """cmd_wallet omits cache line when no cache activity."""
    from unittest.mock import MagicMock, patch
    from agent_runtime_cockpit.cli_repl.slash_commands import cmd_wallet
    from agent_runtime_cockpit.cli_repl.session import ChatSession

    session = ChatSession()
    session.metadata = {}

    fake_snap = MagicMock()
    fake_snap.fail_closed_reason = None
    fake_snap.first_launch = False
    fake_snap.balances = {}

    with (
        patch("agent_runtime_cockpit.cli_repl.slash_commands._session_budget_enforcer") as mock_enf,
        patch("agent_runtime_cockpit.budget.wallet.TokenWallet.snapshot", return_value=fake_snap),
    ):
        mock_enf.return_value = MagicMock()
        result = cmd_wallet("", session)

    assert result.state == "present"
    assert "Cache (this session)" not in result.output


# ── Message breakpoints (bp 3+4 of 4) ────────────────────────────────────────


def _session_with_history(system: str, turns: list[tuple[str, str]]) -> ChatSession:
    s = ChatSession()
    s.add_message("system", system)
    for role, content in turns:
        s.add_message(role, content)
    return s


def test_no_message_breakpoints_with_too_few_messages(monkeypatch):
    """Fewer than 3 non-system messages → no message breakpoints."""
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    session = _session_with_history("s" * 2500, [("user", "hi")])
    req = _manager()._request_from_session(session)
    assert "messages" not in {bp.position for bp in req.cache_control}


def test_message_breakpoints_added_with_prior_exchange(monkeypatch):
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    session = _session_with_history(
        "s" * 2500,
        [
            ("user", "first"),
            ("assistant", "reply"),
            ("user", "second"),
        ],
    )
    req = _manager()._request_from_session(session)
    assert "messages" in {bp.position for bp in req.cache_control}


def test_message_breakpoints_do_not_exceed_budget(monkeypatch):
    """Total breakpoints never exceed 4 (Anthropic limit)."""
    from agent_runtime_cockpit.tools import ToolRegistry
    from agent_runtime_cockpit.tools.builtin import GetCurrentTimeTool

    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    registry = ToolRegistry()
    registry.register(GetCurrentTimeTool())
    session = _session_with_history(
        "s" * 2500,
        [
            ("user", "u1"),
            ("assistant", "a1"),
            ("user", "u2"),
            ("assistant", "a2"),
            ("user", "u3"),
        ],
    )
    session.tools_enabled = True
    mgr = TurnManager(_Provider(), model="claude-3-5", tool_registry=registry)
    req = mgr._request_from_session(session)
    assert len(req.cache_control) <= 4


def test_message_breakpoints_exclude_current_user_turn(monkeypatch):
    """The very last message (current turn) must not receive a breakpoint."""
    monkeypatch.setenv("ARC_ENABLE_PROMPT_CACHING", "1")
    session = _session_with_history(
        "s" * 2500,
        [
            ("user", "past"),
            ("assistant", "reply"),
            ("user", "current"),
        ],
    )
    msgs_list = [
        m for m in session.history if m.get("role") in {"system", "user", "assistant", "tool"}
    ]
    last_idx = len(msgs_list) - 1
    req = _manager()._request_from_session(session)
    msg_bp_indices = {bp.index for bp in req.cache_control if bp.position == "messages"}
    assert last_idx not in msg_bp_indices
