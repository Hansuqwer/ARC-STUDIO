"""Legacy BudgetVector enforcement kept for pre-Phase-4 tests."""

from __future__ import annotations

from typing import Any

from agent_runtime_cockpit.protocol.schemas import BudgetVector


class BudgetExceededError(RuntimeError):
    """Raised when a legacy budget dimension has been exceeded."""

    def __init__(self, dimension: str, limit: float | int, current: float | int) -> None:
        self.dimension = dimension
        self.limit = limit
        self.current = current
        super().__init__(f"Budget dimension '{dimension}' exceeded: {current} > {limit}")


class BudgetVectorEnforcer:
    """Real-time BudgetVector enforcement at effect boundaries."""

    def __init__(self, budget: BudgetVector | None = None) -> None:
        self._budget = budget
        self._tokens_used = 0
        self._cost_used = 0.0
        self._latency_ms_used = 0

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
        if self._budget is None or self._budget.tokens is None:
            return
        projected = self._tokens_used + additional
        if projected > self._budget.tokens:
            raise BudgetExceededError("tokens", self._budget.tokens, projected)

    def check_cost(self, additional: float = 0.0) -> None:
        if self._budget is None or self._budget.cost_usd is None:
            return
        projected = self._cost_used + additional
        if projected > self._budget.cost_usd:
            raise BudgetExceededError("cost_usd", self._budget.cost_usd, projected)

    def check_latency(self, additional_ms: int = 0) -> None:
        if self._budget is None or self._budget.latency_ms is None:
            return
        projected = self._latency_ms_used + additional_ms
        if projected > self._budget.latency_ms:
            raise BudgetExceededError("latency_ms", self._budget.latency_ms, projected)

    def check_and_update(self, tokens: int = 0, cost: float = 0.0, latency_ms: int = 0) -> None:
        self.check_tokens(tokens)
        self.check_cost(cost)
        self.check_latency(latency_ms)
        self._tokens_used += tokens
        self._cost_used += cost
        self._latency_ms_used += latency_ms

    def reset(self) -> None:
        self._tokens_used = 0
        self._cost_used = 0.0
        self._latency_ms_used = 0

    def to_usage_metadata(self) -> dict[str, Any]:
        return {
            "budget_enforcer": {
                "budget": self._budget.model_dump() if self._budget else None,
                "tokens_used": self._tokens_used,
                "cost_used": self._cost_used,
                "latency_ms_used": self._latency_ms_used,
                "exhausted": self.exhausted,
            }
        }
