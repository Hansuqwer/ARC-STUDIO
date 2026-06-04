"""TokenWallet — read-only view over BudgetEnforcer. Fail-closed. No LLM in path."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional

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


def model_display_notes(model_id: str, rates: Any) -> list[str]:
    """Wallet annotation lines for a model's CostRates metadata. Never raises."""
    from datetime import date

    notes: list[str] = []
    try:
        if rates.is_free_tier:
            notes.append(
                f"  {model_id}: FREE TIER (via OpenRouter free tier; rate-limited) — budget tracking skipped"
            )
            return notes

        if rates.pricing_valid_until:
            try:
                until = date.fromisoformat(rates.pricing_valid_until)
                status = (
                    "EXPIRED" if until < date.today() else f"expires {rates.pricing_valid_until}"
                )
                notes.append(
                    f"  ⚠ {model_id}: pricing stale ({status})"
                    + (f" — use {rates.auto_route_to}" if rates.auto_route_to else "")
                )
            except ValueError:
                pass

        if rates.auto_route_to and not rates.pricing_valid_until:
            notes.append(f"  {model_id}: (routed to {rates.auto_route_to})")

        if rates.tokenizer_family not in (None, "cl100k_base"):
            notes.append(
                f"  {model_id}: ≈ cost (tokenizer_family={rates.tokenizer_family}; heuristic accuracy unverified)"
            )
    except Exception:
        pass
    return notes
