"""TokenWallet — read-only view over BudgetEnforcer. Fail-closed. No LLM in path."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Optional

from .schema import BudgetEnforcer, BudgetScope


@dataclass(frozen=True)
class WalletBalance:
    scope: BudgetScope
    cap_usd: Decimal
    spent_usd: Decimal
    remaining_usd: Decimal
    cache_hit_rate: float = 0.0  # from R-03 OTel; 0.0 if no data


@dataclass(frozen=True)
class WalletSnapshot:
    balances: Mapping[str, WalletBalance]  # scope.value -> balance
    first_launch: bool
    fail_closed_reason: Optional[str] = None


class TokenWallet:
    """Read-only view over BudgetEnforcer. Fail-closed. No LLM in path."""

    def __init__(self, enforcer: BudgetEnforcer) -> None:
        self._enforcer = enforcer

    def snapshot(self) -> WalletSnapshot:
        balances: dict[str, WalletBalance] = {}
        try:
            for scope in BudgetScope:
                if scope is BudgetScope.PROVIDER_DAY:
                    continue  # per-provider; not summarizable without provider_id
                cap = self._enforcer._config.effective_cap(scope, None)
                spent = self._enforcer._state.spend_for(scope, None)
                remaining = max(Decimal(0), cap - spent)
                balances[scope.value] = WalletBalance(
                    scope=scope,
                    cap_usd=cap,
                    spent_usd=spent,
                    remaining_usd=remaining,
                )
            first_launch = not self._enforcer._config.first_launch_confirmed
        except Exception as exc:
            return WalletSnapshot(
                balances={}, first_launch=False, fail_closed_reason=f"{type(exc).__name__}: {exc}"
            )
        return WalletSnapshot(balances=balances, first_launch=first_launch)
