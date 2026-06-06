"""Tests for /budget slash command logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_screen():
    from agent_runtime_cockpit.tui.data import DataStore
    from agent_runtime_cockpit.tui.screen import ArcScreen

    data = DataStore(workspace=Path("/tmp"))
    screen = ArcScreen.__new__(ArcScreen)
    screen.data = data
    screen._session = None
    return screen


def test_slash_budget_command_invokes_cli(monkeypatch):
    """When _handle_budget_command(run-id) is called, it calls arc runs budget CLI."""
    screen = _make_screen()

    def mock_run(*args, **kwargs):
        r = MagicMock()
        r.stdout = "Budget: $0.01"
        r.stderr = ""
        return r

    monkeypatch.setattr("subprocess.run", mock_run)
    screen._handle_budget_command("run-abc123")
    entries = screen.data.entries
    assert any("Budget" in e.content for e in entries)


def test_slash_budget_no_runid_shows_wallet(monkeypatch):
    """When _handle_budget_command('') is called, it shows wallet summary."""
    screen = _make_screen()

    mock_result = MagicMock()
    mock_result.output = "[wallet] Budget: $5.00"

    def mock_result_text(r):
        return getattr(r, "output", "")

    with patch("agent_runtime_cockpit.tui.screen.SlashCommandHandler", create=True) as _M:
        with patch("agent_runtime_cockpit.tui.screen._result_text", mock_result_text, create=True):
            # Call directly — it will import and call SlashCommandHandler internally
            # Use a monkeypatch on the module import
            import agent_runtime_cockpit.cli_repl.slash_commands as sc_mod

            orig_handler_cls = getattr(sc_mod, "SlashCommandHandler", None)  # noqa: F841
            handler_mock = MagicMock()
            handler_mock.handle.return_value = mock_result
            monkeypatch.setattr(sc_mod, "SlashCommandHandler", lambda: handler_mock)
            monkeypatch.setattr(sc_mod, "_result_text", mock_result_text)

            screen._handle_budget_command("")

    entries = screen.data.entries
    assert any(
        "wallet" in e.content.lower() or "budget" in e.content.lower() or "5.00" in e.content
        for e in entries
    )
