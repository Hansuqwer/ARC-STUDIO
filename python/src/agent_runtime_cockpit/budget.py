"""BudgetVector enforcement — hard runtime budget gating at effect boundaries.

Provides ``BudgetEnforcer`` that checks a ``BudgetVector`` against accumulated
usage before model/tool-call effects are executed. Raises ``BudgetExceededError``
when any dimension exceeds its configured limit.

This moves budget from post-hoc accounting (``arc runs budget``) to real-time
enforcement at adapter effect boundaries.
"""

from __future__ import annotations

from typing import Any

from .protocol.schemas import BudgetVector


class BudgetExceededError(RuntimeError):
    """Raised when a budget dimension has been exceeded at an effect boundary."""

    def __init__(self, dimension: str, limit: float | int, current: float | int) -> None:
        self.dimension = dimension
        self.limit = limit
        self.current = current
        super().__init__(f"Budget dimension '{dimension}' exceeded: {current} > {limit}")


class BudgetEnforcer:
    """Real-time budget enforcement at model/tool-call effect boundaries.

    Usage::

        enforcer = BudgetEnforcer(budget=BudgetVector(tokens=1000, cost_usd=5.0))
        enforcer.check_tokens(400)   # OK
        enforcer.check_cost(0.5)     # OK
        enforcer.check_and_update(tokens=100, cost=0.25)  # Check + accumulate
        enforcer.check_tokens(600)   # Raises BudgetExceededError
    """

    def __init__(self, budget: BudgetVector | None = None) -> None:
        self._budget = budget
        self._tokens_used: int = 0
        self._cost_used: float = 0.0
        self._latency_ms_used: int = 0

    @property
    def budget(self) -> BudgetVector | None:
        return self._budget

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    @property
    def cost_used(self) -> float:
        return self._cost_used

    @property
    def latency_ms_used(self) -> int:
        return self._latency_ms_used

    @property
    def exhausted(self) -> bool:
        """Return True if ANY budget dimension is at or past its limit."""
        if self._budget is None:
            return False
        if self._budget.tokens is not None and self._tokens_used >= self._budget.tokens:
            return True
        if self._budget.cost_usd is not None and self._cost_used >= self._budget.cost_usd:
            return True
        if self._budget.latency_ms is not None and self._latency_ms_used >= self._budget.latency_ms:
            return True
        return False

    def check_tokens(self, additional: int = 0) -> None:
        """Check that adding ``additional`` tokens does not exceed the token limit.

        Raises ``BudgetExceededError`` if the limit would be exceeded.
        """
        if self._budget is None or self._budget.tokens is None:
            return
        projected = self._tokens_used + additional
        if projected > self._budget.tokens:
            raise BudgetExceededError("tokens", self._budget.tokens, projected)

    def check_cost(self, additional: float = 0.0) -> None:
        """Check that adding ``additional`` cost does not exceed the cost limit."""
        if self._budget is None or self._budget.cost_usd is None:
            return
        projected = self._cost_used + additional
        if projected > self._budget.cost_usd:
            raise BudgetExceededError("cost_usd", self._budget.cost_usd, projected)

    def check_latency(self, additional_ms: int = 0) -> None:
        """Check that adding ``additional_ms`` does not exceed the latency limit."""
        if self._budget is None or self._budget.latency_ms is None:
            return
        projected = self._latency_ms_used + additional_ms
        if projected > self._budget.latency_ms:
            raise BudgetExceededError("latency_ms", self._budget.latency_ms, projected)

    def check_and_update(
        self,
        tokens: int = 0,
        cost: float = 0.0,
        latency_ms: int = 0,
    ) -> None:
        """Check all dimensions and update counters atomically.

        This is the primary enforcement call — use it at adapter effect boundaries
        (before each model call or tool call) to ensure budget is not exceeded.

        Raises ``BudgetExceededError`` if any dimension would be exceeded.
        """
        self.check_tokens(tokens)
        self.check_cost(cost)
        self.check_latency(latency_ms)
        self._tokens_used += tokens
        self._cost_used += cost
        self._latency_ms_used += latency_ms

    def reset(self) -> None:
        """Reset accumulated usage counters (for fork/replay scenarios)."""
        self._tokens_used = 0
        self._cost_used = 0.0
        self._latency_ms_used = 0

    def to_usage_metadata(self) -> dict[str, Any]:
        """Export current usage as metadata dict for RunRecord.metadata."""
        return {
            "budget_enforcer": {
                "budget": self._budget.model_dump() if self._budget else None,
                "tokens_used": self._tokens_used,
                "cost_used": self._cost_used,
                "latency_ms_used": self._latency_ms_used,
                "exhausted": self.exhausted,
            }
        }
