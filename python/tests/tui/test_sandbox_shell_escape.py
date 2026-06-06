"""Tests for R-UX2 sandbox-aware shell escape (!cmd routes through sandbox.decide)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime_cockpit.tui.data import DataStore
from agent_runtime_cockpit.tui.screen import ArcScreen


def _screen(tmp_path: Path) -> ArcScreen:
    data = DataStore()
    data.workspace = tmp_path
    screen = ArcScreen.__new__(ArcScreen)
    screen.data = data
    return screen


def _entries(screen) -> list:
    return [(e.role, e.content) for e in screen.data.entries]


@pytest.fixture(autouse=True)
def _audit_spy(monkeypatch):
    """Spy on sandbox audit persistence; keeps it out of the real ~/.arc in tests."""
    spy = MagicMock()
    monkeypatch.setattr("agent_runtime_cockpit.security.sandbox.persist_sandbox_audit_event", spy)
    return spy


def test_read_only_command_allowed(tmp_path, monkeypatch):
    """A read-only command (ls) passes the sandbox gate and executes via the provider."""
    from unittest.mock import AsyncMock

    from agent_runtime_cockpit.security import trust

    # Force workspace trusted
    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    fake_iso = MagicMock(stdout="file1\n", stderr="", exit_code=0, killed=False, kill_reason=None)
    provider = MagicMock()
    provider.execute = AsyncMock(return_value=fake_iso)
    with patch(
        "agent_runtime_cockpit.isolation.selector.build_execution_provider",
        return_value=provider,
    ) as mock_build:
        screen._handle_shell_escape("!ls")
    # provider.execute was called → command was allowed and routed to the backend
    provider.execute.assert_called_once()
    mock_build.assert_called_once()


def test_destructive_command_blocked(tmp_path, monkeypatch):
    """rm -rf is destructive → sandbox denies → subprocess never called."""
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!rm -rf /")
    mock_run.assert_not_called()
    blocked = [c for r, c in _entries(screen) if "blocked" in c.lower()]
    assert blocked, "expected a 'blocked' tool entry"


def test_untrusted_workspace_blocks_everything(tmp_path, monkeypatch):
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.UNTRUSTED),
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!ls")
    mock_run.assert_not_called()
    blocked = [c for r, c in _entries(screen) if "untrusted" in c.lower()]
    assert blocked


def test_network_command_requires_approval_or_denied(tmp_path, monkeypatch):
    """curl is a network command; under default local-safe policy it must not run silently."""
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!curl https://example.com")
    # network is denied/approval-required under local-safe default → not executed
    mock_run.assert_not_called()


def test_sandbox_evaluation_failure_fails_closed(tmp_path, monkeypatch):
    """If the sandbox decision raises, the command is BLOCKED, never executed.

    Regression for the prior ``except Exception: pass`` that fell through to an
    unsandboxed ``subprocess.run(cmd, shell=True)``.
    """
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )

    def _boom(*_a, **_k):
        raise RuntimeError("policy engine exploded")

    monkeypatch.setattr("agent_runtime_cockpit.security.sandbox.decide", _boom)
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!ls")
    mock_run.assert_not_called()
    assert [c for _r, c in _entries(screen) if "blocked" in c.lower()], (
        "fail-closed: expected a 'blocked' entry when the gate errors"
    )


def test_allowed_command_executes_argv_without_shell(tmp_path, monkeypatch, _audit_spy):
    """Allowed commands route the classified argv list to the provider, and audit."""
    from unittest.mock import AsyncMock

    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    fake_iso = MagicMock(stdout="ok\n", stderr="", exit_code=0, killed=False, kill_reason=None)
    provider = MagicMock()
    provider.execute = AsyncMock(return_value=fake_iso)
    with patch(
        "agent_runtime_cockpit.isolation.selector.build_execution_provider",
        return_value=provider,
    ):
        screen._handle_shell_escape("!ls -la")
    provider.execute.assert_called_once()
    args, _kwargs = provider.execute.call_args
    assert args[0] == ["ls", "-la"], "must pass the classified argv list, not a shell string"
    _audit_spy.assert_called()  # audit event persisted on allow


# ─── Edge-case branch coverage (R-OPEN-SANDBOX verification pass) ──────────────


def test_unparseable_command_blocked(tmp_path, monkeypatch):
    """An unbalanced quote makes shlex.split raise → fail-closed block, no execution."""
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape('!echo "unterminated')
    mock_run.assert_not_called()
    assert [c for _r, c in _entries(screen) if "cannot parse" in c.lower()], (
        "expected a parse-failure block entry"
    )


def test_empty_command_is_noop(tmp_path, monkeypatch):
    """A bang with only whitespace parses to empty argv → silent no-op, no execution."""
    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    before = len(screen.data.entries)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!   ")
    mock_run.assert_not_called()
    # Only the echoed "user" entry is added; no tool/block entry follows.
    tool_entries = [c for r, c in _entries(screen) if r == "tool"]
    assert tool_entries == [], "empty command must not produce a tool entry"
    assert len(screen.data.entries) >= before  # no crash


def test_approval_required_shows_hint_in_block(tmp_path, monkeypatch):
    """A denied command with approval_required=True shows the approval hint.

    decide() produces allowed=False + approval_required=True for network commands
    under local-safe policy. The handler must surface the approval hint so users
    know how to unblock.
    """
    from agent_runtime_cockpit.security import sandbox, trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    # Produce a real decide() decision: curl is NETWORK, local-safe denies + approval_required
    denied_with_approval = sandbox.SandboxDecision(
        allowed=False,
        classification=sandbox.CommandClassification.NETWORK,
        reason="network policy",
        policy="local-safe",
        approval_required=True,
        approved=False,
        reason_code=sandbox.SandboxReasonCode.NETWORK_DENIED,
    )
    monkeypatch.setattr(
        "agent_runtime_cockpit.security.sandbox.decide", lambda *a, **k: denied_with_approval
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        screen._handle_shell_escape("!curl https://example.com")
    mock_run.assert_not_called()
    entries = [c for _r, c in _entries(screen) if "blocked" in c.lower()]
    assert entries, "expected a blocked entry"
    assert any("approve" in c.lower() for c in entries), (
        "expected the approval hint in the blocked message"
    )


def test_timeout_surfaced_and_audited(tmp_path, monkeypatch, _audit_spy):
    """When the provider reports a timeout kill, the TUI reports it and audits."""
    from unittest.mock import AsyncMock

    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    timed_out = MagicMock(stdout="", stderr="", exit_code=None, killed=True, kill_reason="timeout")
    provider = MagicMock()
    provider.execute = AsyncMock(return_value=timed_out)
    with patch(
        "agent_runtime_cockpit.isolation.selector.build_execution_provider",
        return_value=provider,
    ):
        screen._handle_shell_escape("!ls")
    assert [c for _r, c in _entries(screen) if "timed out" in c.lower()], "expected a timeout entry"
    _audit_spy.assert_called()


def test_provider_execute_error_does_not_crash(tmp_path, monkeypatch):
    """If the isolation provider raises, the error surfaces as a tool entry, no crash."""
    from unittest.mock import AsyncMock

    from agent_runtime_cockpit.security import trust

    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    provider = MagicMock()
    provider.execute = AsyncMock(side_effect=RuntimeError("runner boom"))
    with patch(
        "agent_runtime_cockpit.isolation.selector.build_execution_provider",
        return_value=provider,
    ):
        screen._handle_shell_escape("!ls")
    assert [c for r, c in _entries(screen) if r == "tool" and "boom" in c.lower()], (
        "expected the runner error surfaced as a tool entry"
    )


def test_oversized_argv_denied_at_decide_level():
    """decide() denies an argv that exceeds the size bounds (ARGV_OVERSIZED)."""
    from agent_runtime_cockpit.security.sandbox import (
        MAX_ARGV_COUNT,
        SandboxPolicy,
        SandboxReasonCode,
        decide,
    )

    oversized = ["echo"] + ["x"] * (MAX_ARGV_COUNT + 1)
    decision = decide(oversized, SandboxPolicy())
    assert not decision.allowed
    assert decision.reason_code == SandboxReasonCode.ARGV_OVERSIZED
