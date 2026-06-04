"""Budget enforcement schema for provider-backed calls."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from .storage import BudgetStorage

log = logging.getLogger(__name__)


class BudgetScope(StrEnum):
    RUN = "run"
    WORKFLOW = "workflow"
    SESSION = "session"
    PROVIDER_DAY = "provider_day"


DEFAULT_CAPS: dict[BudgetScope, Decimal] = {
    BudgetScope.RUN: Decimal("5.00"),
    BudgetScope.WORKFLOW: Decimal("25.00"),
    BudgetScope.SESSION: Decimal("10.00"),
    BudgetScope.PROVIDER_DAY: Decimal("100.00"),
}
FIRST_LAUNCH_CAP = Decimal("1.00")


class BudgetCap(BaseModel):
    scope: BudgetScope
    amount_usd: Decimal = Field(gt=Decimal("0"))
    provider_id: str | None = None

    @model_validator(mode="after")
    def _provider_scope_consistency(self) -> "BudgetCap":
        if self.scope is BudgetScope.PROVIDER_DAY and not self.provider_id:
            raise ValueError("PROVIDER_DAY scope requires provider_id")
        if self.scope is not BudgetScope.PROVIDER_DAY and self.provider_id is not None:
            raise ValueError("provider_id only valid for PROVIDER_DAY scope")
        return self


class BudgetConfig(BaseModel):
    schema_version: int = 1
    caps: list[BudgetCap] = Field(default_factory=list)
    first_launch_confirmed: bool = False
    confirmation_required_above_usd: Decimal = Decimal("1.00")

    def effective_cap(self, scope: BudgetScope, provider_id: str | None = None) -> Decimal:
        cap = self._configured_cap(scope, provider_id)
        if scope is BudgetScope.SESSION and not self.first_launch_confirmed:
            return min(FIRST_LAUNCH_CAP, cap)
        return cap

    def _configured_cap(self, scope: BudgetScope, provider_id: str | None) -> Decimal:
        for cap in self.caps:
            if cap.scope is scope and cap.provider_id == provider_id:
                return cap.amount_usd
        return DEFAULT_CAPS[scope]


class ScopeSpend(BaseModel):
    scope: BudgetScope
    provider_id: str | None = None
    amount_usd: Decimal = Decimal("0")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_reset_date: date | None = None

    def add(self, amount: Decimal) -> None:
        if amount < 0:
            raise ValueError("Cannot add negative spend")
        self.amount_usd += amount


class BudgetState(BaseModel):
    schema_version: int = 1
    session: ScopeSpend = Field(default_factory=lambda: ScopeSpend(scope=BudgetScope.SESSION))
    current_run: ScopeSpend | None = None
    current_workflow: ScopeSpend | None = None
    provider_days: dict[str, ScopeSpend] = Field(default_factory=dict)

    def spend_for(self, scope: BudgetScope, provider_id: str | None = None) -> Decimal:
        if scope is BudgetScope.SESSION:
            return self.session.amount_usd
        if scope is BudgetScope.RUN:
            return self.current_run.amount_usd if self.current_run else Decimal("0")
        if scope is BudgetScope.WORKFLOW:
            return self.current_workflow.amount_usd if self.current_workflow else Decimal("0")
        if scope is BudgetScope.PROVIDER_DAY:
            if not provider_id:
                raise ValueError("PROVIDER_DAY scope requires provider_id")
            entry = self.provider_days.get(self._provider_day_key(provider_id))
            return entry.amount_usd if entry else Decimal("0")
        raise AssertionError(f"Unknown scope: {scope}")

    def record(
        self, amount_usd: Decimal, *, provider_id: str, run_active: bool, workflow_active: bool
    ) -> None:
        self.session.add(amount_usd)
        if run_active and self.current_run is not None:
            self.current_run.add(amount_usd)
        if workflow_active and self.current_workflow is not None:
            self.current_workflow.add(amount_usd)
        key = self._provider_day_key(provider_id)
        entry = self.provider_days.get(key)
        if entry is None:
            entry = ScopeSpend(
                scope=BudgetScope.PROVIDER_DAY,
                provider_id=provider_id,
                last_reset_date=datetime.now(timezone.utc).date(),
            )
            self.provider_days[key] = entry
        entry.add(amount_usd)

    def begin_run(self) -> None:
        self.current_run = ScopeSpend(scope=BudgetScope.RUN)

    def end_run(self) -> None:
        self.current_run = None

    def begin_workflow(self) -> None:
        self.current_workflow = ScopeSpend(scope=BudgetScope.WORKFLOW)

    def end_workflow(self) -> None:
        self.current_workflow = None

    @staticmethod
    def _provider_day_key(provider_id: str) -> str:
        return f"{provider_id}:{datetime.now(timezone.utc).date().isoformat()}"


class BudgetExceeded(Exception):
    def __init__(
        self,
        scope: BudgetScope,
        cap: Decimal,
        current: Decimal,
        proposed: Decimal,
        provider_id: str | None = None,
    ) -> None:
        self.scope = scope
        self.cap = cap
        self.current = current
        self.proposed = proposed
        self.provider_id = provider_id
        suffix = f" ({provider_id})" if provider_id else ""
        super().__init__(
            f"Budget exceeded for scope={scope.value}{suffix}: cap=${cap}, current=${current}, proposed=${proposed}"
        )


class ConfirmationRequired(Exception):
    def __init__(self, proposed_cost: Decimal) -> None:
        self.proposed_cost = proposed_cost
        super().__init__(
            f"First provider-backed call requires confirmation (proposed cost ${proposed_cost})"
        )


class BudgetEnforcer:
    def __init__(
        self,
        config: BudgetConfig,
        state: BudgetState,
        storage: "BudgetStorage | None" = None,
    ) -> None:
        self._config = config
        self._state = state
        self._storage = storage
        # Load durable spend into in-memory state on construction
        if storage is not None:
            self._load_from_storage(storage)

    def preflight(
        self,
        estimated_cost_usd: Decimal,
        *,
        provider_id: str,
        run_active: bool,
        workflow_active: bool,
    ) -> None:
        if (
            not self._config.first_launch_confirmed
            and estimated_cost_usd > self._config.confirmation_required_above_usd
        ):
            raise ConfirmationRequired(estimated_cost_usd)
        scopes: list[tuple[BudgetScope, str | None]] = [
            (BudgetScope.SESSION, None),
            (BudgetScope.PROVIDER_DAY, provider_id),
        ]
        if run_active:
            scopes.insert(0, (BudgetScope.RUN, None))
        if workflow_active:
            scopes.insert(1 if run_active else 0, (BudgetScope.WORKFLOW, None))
        for scope, scoped_provider_id in scopes:
            cap = self._config.effective_cap(scope, scoped_provider_id)
            current = self._state.spend_for(scope, scoped_provider_id)
            proposed = current + estimated_cost_usd
            if proposed > cap:
                raise BudgetExceeded(scope, cap, current, proposed, scoped_provider_id)

    def record(
        self,
        measured_cost_usd: Decimal,
        *,
        provider_id: str,
        run_active: bool,
        workflow_active: bool,
    ) -> None:
        self._state.record(
            measured_cost_usd,
            provider_id=provider_id,
            run_active=run_active,
            workflow_active=workflow_active,
        )
        if self._storage is not None:
            self._persist(provider_id)

    def _load_from_storage(self, storage: "BudgetStorage") -> None:
        """Load durable SESSION + PROVIDER_DAY spend into in-memory state."""
        session_usd = storage.load_session()
        self._state.session.amount_usd = session_usd

    def _persist(self, provider_id: str) -> None:
        """Write current SESSION + PROVIDER_DAY to durable storage after each record()."""
        if self._storage is None:
            return
        self._storage.save_session(self._state.session.amount_usd)
        key = self._state._provider_day_key(provider_id)
        entry = self._state.provider_days.get(key)
        if entry is not None:
            date_key = key.split(":", 1)[1] if ":" in key else key
            self._storage.save_provider_day(provider_id, date_key, entry.amount_usd)

    def check_and_warn(
        self,
        *,
        provider_id: str | None = None,
        run_active: bool = False,
        workflow_active: bool = False,
    ) -> None:
        """Check if any scope's spend is above 80% of its cap and emit QuotaWarning events."""
        from ..events import get_bus
        from ..events.types import QuotaWarning

        scopes: list[tuple[BudgetScope, str | None]] = [(BudgetScope.SESSION, None)]
        if run_active:
            scopes.insert(0, (BudgetScope.RUN, None))
        if workflow_active:
            scopes.insert(1 if run_active else 0, (BudgetScope.WORKFLOW, None))
        if provider_id is not None:
            scopes.append((BudgetScope.PROVIDER_DAY, provider_id))

        for scope, scoped_provider_id in scopes:
            cap = self._config.effective_cap(scope, scoped_provider_id)
            current = self._state.spend_for(scope, scoped_provider_id)
            if cap > 0:
                usage_pct = float(current / cap * 100)
                if usage_pct >= 80:
                    try:
                        bus = get_bus()
                        bus.publish(
                            QuotaWarning(
                                dimension=scope.value,
                                usage_pct=usage_pct,
                                limit=float(cap),
                                current=float(current),
                            )
                        )
                    except Exception:
                        log.warning(f"Failed to emit QuotaWarning for {scope.value}", exc_info=True)
