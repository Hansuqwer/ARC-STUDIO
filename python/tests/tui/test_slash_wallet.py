"""Tests for /wallet slash command — R-01."""

from __future__ import annotations

from decimal import Decimal

from agent_runtime_cockpit.budget.schema import BudgetConfig, BudgetState
from agent_runtime_cockpit.cli_repl.slash_commands import cmd_wallet
from agent_runtime_cockpit.cli_repl.session import ChatSession


def _session_with_enforcer(
    *, first_launch_confirmed: bool = True, session_spent: Decimal = Decimal("0")
) -> ChatSession:
    session = ChatSession()
    config = BudgetConfig(first_launch_confirmed=first_launch_confirmed)
    state = BudgetState()
    state.session.amount_usd = session_spent
    session.metadata = {"provider_budget": config.model_dump(mode="json")}
    return session


class TestSlashWallet:
    def test_wallet_no_enforcer_returns_message(self):
        session = ChatSession()
        session.metadata = {}
        result = cmd_wallet("", session)
        assert "No budget enforcer" in str(result)

    def test_wallet_renders_scopes(self):
        session = _session_with_enforcer(session_spent=Decimal("1.50"))
        result = cmd_wallet("", session)
        output = str(result)
        assert "session" in output
        assert "run" in output
        assert "workflow" in output
        assert "SCOPE" in output

    def test_wallet_shows_first_launch_banner(self):
        session = _session_with_enforcer(first_launch_confirmed=False)
        result = cmd_wallet("", session)
        output = str(result)
        assert "First-launch cap" in output
        assert "$1.00" in output

    def test_wallet_fail_closed_returns_error_not_crash(self):
        session = ChatSession()
        # Put invalid data that will cause BudgetConfig to fail
        session.metadata = {"provider_budget": {"caps": "invalid"}}
        result = cmd_wallet("", session)
        # Should not crash — returns no-enforcer message since validation fails
        assert "No budget enforcer" in str(result)

    def test_wallet_no_color_no_markup(self):
        session = _session_with_enforcer(session_spent=Decimal("2.00"))
        result = cmd_wallet("", session)
        output = str(result)
        # No Rich markup in output
        assert "[bold" not in output
        assert "[yellow" not in output
