"""Tests for R-UX2 sandbox-aware shell escape (!cmd routes through sandbox.decide)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_read_only_command_allowed(tmp_path, monkeypatch):
    """A read-only command (ls) passes the sandbox gate and executes."""
    from agent_runtime_cockpit.security import trust

    # Force workspace trusted
    monkeypatch.setattr(
        "agent_runtime_cockpit.security.trust.resolve_trust",
        lambda ws: MagicMock(level=trust.TrustLevel.TRUSTED),
    )
    screen = _screen(tmp_path)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="file1\n", stderr="", returncode=0)
        screen._handle_shell_escape("!ls")
    # subprocess.run was called → command was allowed
    mock_run.assert_called_once()


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
