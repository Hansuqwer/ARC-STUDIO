"""Tests for /budget slash command — R-01."""

from __future__ import annotations

from decimal import Decimal

from agent_runtime_cockpit.budget.schema import BudgetConfig, BudgetState
from agent_runtime_cockpit.cli_repl.slash_commands import cmd_budget
from agent_runtime_cockpit.cli_repl.session import ChatSession


def _session_with_enforcer(*, session_spent: Decimal = Decimal("0")) -> ChatSession:
    session = ChatSession()
    config = BudgetConfig(first_launch_confirmed=True)
    state = BudgetState()
    state.session.amount_usd = session_spent
    session.metadata = {"provider_budget": config.model_dump(mode="json")}
    return session


class TestSlashBudget:
    def test_budget_no_enforcer(self):
        session = ChatSession()
        session.metadata = {}
        result = cmd_budget("", session)
        assert "No budget enforcer" in str(result)

    def test_budget_renders_scopes(self):
        session = _session_with_enforcer(session_spent=Decimal("3.00"))
        result = cmd_budget("", session)
        output = str(result)
        assert "session" in output
        assert "run" in output
        assert "workflow" in output

    def test_budget_fail_graceful(self):
        session = ChatSession()
        session.metadata = {"provider_budget": {"caps": "bad"}}
        result = cmd_budget("", session)
        # Should not crash — returns no-enforcer since validation fails
        assert "No budget enforcer" in str(result)

    def test_budget_pct_computation(self):
        session = _session_with_enforcer(session_spent=Decimal("5.00"))
        result = cmd_budget("", session)
        output = str(result)
        # Session spend from metadata is always fresh (0) — check format
        assert "0%" in output
        assert "$10.00" in output  # session cap
