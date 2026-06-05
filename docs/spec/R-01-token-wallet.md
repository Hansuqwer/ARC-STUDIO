# v0.4.0-alpha — R-01 TokenWallet + `/wallet` + QuotaWarning Consumer

> **Feature release.** Closes the visibility/action loop opened by v0.3.0-alpha:
> P0-4 status bar showed *usage*. R-03 made cache hits *measurable*. R-01 makes
> budget state *actionable* — surfaces caps, warns before `BudgetExceeded`,
> exposes a `/wallet` slash command, and routes `QuotaWarning` typed events
> into the TUI.
>
> Per `TOKEN_SAVING_PLAN-2.md` §15 — R-01 is the next highest-leverage item
> after R-03 + R-04 ship.

---

## 0. Execution prompt (paste into your CLI session)

```text
v0.3.1-alpha is tagged and clean. Time to ship R-01 (TokenWallet) as v0.4.0-alpha.

Scope (per docs/spec/R-01-token-wallet.md):
  1. New python/src/agent_runtime_cockpit/budget/wallet.py — TokenWallet class
     wrapping BudgetEnforcer (budget/schema.py:160-246). Read-only view of
     scope balances + remaining budget. Fail-closed on unknown scope.
  2. New tui/slash/wallet.py + register in slash registry — `/wallet` command
     prints per-scope (RUN/WORKFLOW/SESSION/PROVIDER_DAY) USD spent / cap /
     remaining + cache hit rate from OTel attrs (uses R-03 surface).
  3. QuotaWarning consumer (events/types.py:70) wired into tui/widgets/status_bar.py
     — flashes the status bar amber/red on warning, latches until acknowledged.
  4. Bonus QW-3 if budget allows: `/budget` slash command (sister to /wallet,
     scope-focused).

Constraints (carry over):
  - Local-first, single-user. No public HTTP, no telemetry leaving the box.
  - **No LLM in budget decisions** (CoSAI). All thresholds deterministic.
  - **EnforcementContext is @dataclass(frozen=True)** — never mutate; new
    state goes through ContextVar (precedent: _enforcement_context in
    security/context.py).
  - Fail-closed on cost: unknown / exhausted budget → deny.
  - Additive protocol only. New typed event QuotaWarning is already in
    events/types.py:70 — do NOT redefine. Add a TS mirror in
    packages/arc-protocol-ts/src/run-events.ts.
  - **Use BudgetEnforcer in budget/schema.py:160-246, NOT legacy budget.py.**
  - Don't edit theia-extensions/*.
  - One commit per logical change. Each commit ships its own tests + CHANGELOG.
  - Honesty over polish — run `uv run pytest -q` before claiming green.
  - Do NOT tag or push v0.4.0-alpha without explicit user go-ahead.

Branch: spec/r01-token-wallet off origin/main HEAD (whatever v0.3.1-alpha tags).

Workflow:
  1. Task 0 — gap audit (5 min): confirm BudgetEnforcer scope set, QuotaWarning
     event shape, slash registry pattern.
  2. Task 1 — TokenWallet (~3 hrs): wallet.py + 10 tests.
  3. Task 2 — /wallet slash command (~2 hrs): TUI integration + 6 tests.
  4. Task 3 — QuotaWarning consumer (~2 hrs): status_bar wiring + 5 tests.
  5. Task 4 — TS mirror of QuotaWarning (~30 min): run-events.ts + 2 tests.
  6. Task 5 — QW-3 /budget command (~1 hr, optional bonus): 4 tests.
  7. Task 6 — verify, patch, CHANGELOG, commit per logical change.
  8. Task 7 — report back; await user go.

Report back template (paste filled-in):
  [ ] Task 0 audit (3 lines)
  [ ] Tests: baseline N → new N (delta)
  [ ] TokenWallet commit SHA + LOC
  [ ] /wallet commit SHA + LOC
  [ ] QuotaWarning consumer commit SHA + LOC
  [ ] TS mirror commit SHA + LOC
  [ ] /budget (QW-3) commit SHA or "skipped, reason"
  [ ] Patches in patches/r01/v0.4.0-alpha/ (count + LOC)
  [ ] All gates green (pytest + jest + build + typecheck + banned-claims + GH Actions)
  Do NOT tag yet. Wait for my go.
```

---

## 1. Branch + base commit

| | |
|---|---|
| **Branch** | `spec/r01-token-wallet` |
| **Base** | `origin/main` @ whatever `v0.3.1-alpha` tags (expected `~898ee26 + 3 ci-debt commits`) |
| **Target tag** | `v0.4.0-alpha` (after green-light) |
| **Expected commit count** | 4–5 (TokenWallet, /wallet, QuotaWarning consumer, TS mirror, optional /budget) |
| **Expected duration** | 2–3 days |

---

## 2. Repo facts to verify in Task 0

| Claim | File:line | Why it matters |
|---|---|---|
| `BudgetEnforcer` is the **authoritative** enforcer | `python/src/agent_runtime_cockpit/budget/schema.py:160-246` | TokenWallet wraps this, NOT legacy `budget.py:33` |
| Scopes: `RUN | WORKFLOW | SESSION | PROVIDER_DAY` | `budget/schema.py` (BudgetScope enum) | Wallet view must enumerate all four |
| First-launch cap | `budget/schema.py:FIRST_LAUNCH_CAP = Decimal("1.00")` | Wallet must respect first-launch override |
| Default caps | `budget/schema.py:DEFAULT_CAPS = {RUN: $5, WORKFLOW: $25, SESSION: $10, PROVIDER_DAY: $100}` | Wallet shows these when no override |
| Exceptions | `budget/schema.py: BudgetExceeded, ConfirmationRequired` | Wallet must catch/surface, never re-raise |
| Preflight wire | `python/src/agent_runtime_cockpit/providers/budget_preflight.py:19-60` | `preflight_with_estimator()` — already wired but no callers; TokenWallet exposes the estimate |
| `QuotaWarning` typed event | `python/src/agent_runtime_cockpit/events/types.py:70` | Already exists; TUI consumer is the gap |
| Typed event extension sites (Python) | `protocol/typed_events.py` — `KnownRunEvent` union + `is_known_event` set + `parse_typed_event` type_map | 3 sites per project rule |
| Typed event extension sites (TS) | `packages/arc-protocol-ts/src/run-events.ts` — `KnownRunEvent` + `KNOWN_RUN_EVENT_TYPES` | 1 site (already covered by R-TS3 test backfill template) |
| Status bar | `python/src/agent_runtime_cockpit/tui/widgets/status_bar.py` | P0-4 added `tok N/M (P%)`; this sprint adds amber/red flash on QuotaWarning |
| Slash registry | `python/src/agent_runtime_cockpit/tui/slash/` (look for existing slash commands' registration pattern) | `/wallet` and `/budget` plug in here |
| EnforcementContext mutation rule | `python/src/agent_runtime_cockpit/security/context.py:_enforcement_context` (ContextVar precedent) | NEVER mutate EnforcementContext frozen dataclass |
| `BackendMode` gating | `python/src/agent_runtime_cockpit/gating.py: STUB | LOCAL | GATEWAY` + `require_dual_gate` | `/wallet` must respect gating |

**Task 0 commands:**

```bash
cd python

# Confirm BudgetEnforcer authoritative + scope enum
grep -n "class BudgetEnforcer\|class BudgetScope\|FIRST_LAUNCH_CAP\|DEFAULT_CAPS" \
  src/agent_runtime_cockpit/budget/schema.py

# Confirm QuotaWarning exists, no TUI consumer yet
grep -n "QuotaWarning" src/agent_runtime_cockpit/events/types.py
grep -rn "QuotaWarning" src/agent_runtime_cockpit/tui/ | head -5
# expect: 0 hits in tui/

# Confirm slash registry pattern
ls src/agent_runtime_cockpit/tui/slash/
cat src/agent_runtime_cockpit/tui/slash/__init__.py 2>/dev/null | head -30

# Confirm preflight wire has no current callers
grep -rn "preflight_with_estimator" src/ | grep -v providers/budget_preflight.py
# expect: 0-1 hits outside the definition file (R-01 will add one)

# Confirm status_bar reads total_tokens but no QuotaWarning yet
grep -n "QuotaWarning\|total_tokens\|context_limit" \
  src/agent_runtime_cockpit/tui/widgets/status_bar.py
```

**STOP if** `BudgetEnforcer` is not at `budget/schema.py:160-246`, or `QuotaWarning` already has TUI consumers, or slash registry pattern is unclear. Report findings before coding.

---

## 3. Files this release will touch

### Created

| Path | Purpose | Est LOC |
|---|---|---|
| `python/src/agent_runtime_cockpit/budget/wallet.py` | `TokenWallet` class wrapping `BudgetEnforcer` | ~140 |
| `python/src/agent_runtime_cockpit/tui/slash/wallet.py` | `/wallet` slash command implementation | ~70 |
| `python/src/agent_runtime_cockpit/tui/slash/budget.py` *(optional QW-3)* | `/budget` slash command | ~60 |
| `python/tests/budget/test_token_wallet.py` | 10 cases for TokenWallet | ~200 |
| `python/tests/tui/test_slash_wallet.py` | 6 cases for /wallet | ~150 |
| `python/tests/tui/test_slash_budget.py` *(optional)* | 4 cases for /budget | ~100 |
| `python/tests/tui/test_status_bar_quota_warning.py` | 5 cases for QuotaWarning consumer | ~140 |
| `python/tests/events/test_quota_warning_typed_event_roundtrip.py` | 3 cases for protocol round-trip | ~80 |
| `packages/arc-protocol-ts/src/run-events.test.ts` *(extend, not create — already exists from R-TS3)* | +2 cases for QuotaWarning TS parity | ~40 |
| `patches/r01/v0.4.0-alpha/001_token_wallet.patch` | Exported | ~250 |
| `patches/r01/v0.4.0-alpha/002_slash_wallet.patch` | Exported | ~120 |
| `patches/r01/v0.4.0-alpha/003_quota_warning_consumer.patch` | Exported | ~180 |
| `patches/r01/v0.4.0-alpha/004_ts_mirror_quota_warning.patch` | Exported | ~70 |
| `patches/r01/v0.4.0-alpha/005_slash_budget.patch` *(optional)* | Exported | ~100 |
| `MERGE_NOTES.md` (overwrite) | Release notes for v0.4.0-alpha | ~80 |

### Modified

| Path | Change | Est LOC |
|---|---|---|
| `python/src/agent_runtime_cockpit/budget/__init__.py` | Export `TokenWallet` | 2 |
| `python/src/agent_runtime_cockpit/tui/slash/__init__.py` (or registry file) | Register `/wallet` and optionally `/budget` | 4–6 |
| `python/src/agent_runtime_cockpit/tui/widgets/status_bar.py` | Subscribe to `QuotaWarning` events; flash amber/red | ~30 |
| `python/src/agent_runtime_cockpit/tui/data.py` | Add `quota_warnings: list[QuotaWarning] = field(default_factory=list)` for status bar to read | ~3 |
| `python/src/agent_runtime_cockpit/protocol/typed_events.py` | Add `QuotaWarning` to `KnownRunEvent` union + `is_known_event` set + `parse_typed_event` type_map (3 sites) | ~6 |
| `packages/arc-protocol-ts/src/run-events.ts` | Add `QuotaWarning` to TS `KnownRunEvent` + `KNOWN_RUN_EVENT_TYPES` | ~10 |
| `docs/roadmap.md` | Add R-TS4 row (R-01 complete) | ~5 |
| `CHANGELOG.md` (under `[Unreleased]` → `### Added`) | 4 bullets (one per task) | ~8 |

### Not touched (out of scope, deliberately)

- `python/src/agent_runtime_cockpit/budget.py` — legacy, do NOT extend
- `python/src/agent_runtime_cockpit/protocol/schemas.py:147` (`BudgetVector`) — legacy only
- `theia-extensions/*` — archived per project rules
- `providers/anthropic.py` — already shipped R-04, do NOT touch
- `observability/otel_mapping.py` — already shipped R-03, do NOT touch

---

## 4. Task-by-task

### Task 1 — TokenWallet (~3 hrs)

**Design (deterministic, read-only-by-default):**

```python
# python/src/agent_runtime_cockpit/budget/wallet.py
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from .schema import BudgetEnforcer, BudgetScope, BudgetExceeded, DEFAULT_CAPS


@dataclass(frozen=True)
class WalletBalance:
    scope: BudgetScope
    cap_usd: Decimal           # active cap (first-launch override applied)
    spent_usd: Decimal         # cumulative actual spend
    remaining_usd: Decimal     # cap - spent, clamped ≥0
    warn_at_pct: int = 80      # default warning threshold
    cache_hit_rate: float = 0.0  # populated from OTel cache_read / (cache_read + input)


@dataclass(frozen=True)
class WalletSnapshot:
    balances: Mapping[BudgetScope, WalletBalance]
    first_launch: bool         # True if first-launch cap applied
    fail_closed_reason: str | None = None  # set if any scope unreadable


class TokenWallet:
    """
    Read-only view over BudgetEnforcer. Fail-closed on unknown scope.

    Never mutates EnforcementContext. Never makes pricing decisions
    independent of BudgetEnforcer. No LLM in path (CoSAI).
    """

    def __init__(self, enforcer: BudgetEnforcer):
        self._enforcer = enforcer

    def snapshot(self) -> WalletSnapshot:
        """Read all scope balances atomically. Fail-closed on any scope error."""
        balances = {}
        try:
            for scope in BudgetScope:
                cap = self._enforcer.cap_for(scope)
                spent = self._enforcer.spent_for(scope)
                balances[scope] = WalletBalance(
                    scope=scope,
                    cap_usd=cap,
                    spent_usd=spent,
                    remaining_usd=max(Decimal(0), cap - spent),
                    cache_hit_rate=self._cache_hit_rate(scope),
                )
        except Exception as exc:
            # fail-closed: surface, do not silently degrade
            return WalletSnapshot(
                balances={},
                first_launch=False,
                fail_closed_reason=f"wallet read failed: {type(exc).__name__}",
            )
        return WalletSnapshot(
            balances=balances,
            first_launch=self._enforcer.is_first_launch(),
        )

    def _cache_hit_rate(self, scope: BudgetScope) -> float:
        """Compute from OTel cache_read_input_tokens / total_input_tokens (R-03)."""
        # Read from enforcer's accumulated span attrs; 0.0 if no data yet.
        ...
```

**Tests (`python/tests/budget/test_token_wallet.py`):**

| # | Case | Asserts |
|---|---|---|
| 1 | `test_snapshot_with_no_spend_returns_full_caps` | All 4 scopes balanced at cap, remaining == cap |
| 2 | `test_snapshot_after_partial_spend_subtracts` | `remaining == cap - spent`, clamped ≥ 0 |
| 3 | `test_snapshot_first_launch_applies_dollar_cap` | RUN scope cap == `FIRST_LAUNCH_CAP` ($1.00) |
| 4 | `test_snapshot_unknown_scope_fail_closed` | `fail_closed_reason` set; balances == {} |
| 5 | `test_snapshot_read_does_not_mutate_enforcer` | Enforcer state unchanged after N snapshots |
| 6 | `test_cache_hit_rate_zero_when_no_otel_data` | `cache_hit_rate == 0.0` |
| 7 | `test_cache_hit_rate_computed_from_otel_attrs` | Given cache_read=420, input=1000 → 0.42 |
| 8 | `test_wallet_never_calls_llm` | Mock LLM client; assert 0 calls during snapshot |
| 9 | `test_wallet_respects_enforcement_context` | ContextVar override visible in snapshot |
| 10 | `test_snapshot_concurrent_calls_thread_safe` | 10 threads call snapshot; no races |

### Task 2 — `/wallet` slash command (~2 hrs)

**Behavior:**

```
> /wallet

Token Wallet (first-launch: yes)
─────────────────────────────────────────────────────────
SCOPE          SPENT       CAP        REMAINING   CACHE
RUN            $0.12       $1.00      $0.88       42.0%
WORKFLOW       $0.00       $25.00     $25.00      —
SESSION        $0.30       $10.00     $9.70       38.5%
PROVIDER_DAY   $1.20       $100.00    $98.80      40.1%
─────────────────────────────────────────────────────────
First-launch cap active. Cap restored to $5/run after first run completes.
```

**Tests (`python/tests/tui/test_slash_wallet.py`):**

| # | Case |
|---|---|
| 1 | `test_wallet_command_renders_all_four_scopes` |
| 2 | `test_wallet_command_shows_first_launch_banner_when_active` |
| 3 | `test_wallet_command_omits_first_launch_banner_when_inactive` |
| 4 | `test_wallet_command_shows_dash_for_cache_when_no_data` |
| 5 | `test_wallet_command_fail_closed_renders_error_not_crash` |
| 6 | `test_wallet_command_respects_NO_COLOR` (text tags fallback) |

### Task 3 — QuotaWarning consumer (~2 hrs)

**Status bar flash logic (deterministic, no LLM):**

- `WARN` severity → status bar amber for 3 seconds, then latches with `⚠` glyph
- `CRITICAL` severity → status bar red, latches with `🛑` glyph until acked
- Acknowledgement: any keypress in TUI clears the latch (single-user assumption)
- `NO_COLOR=1` → text tags `[WARN]` / `[CRITICAL]` instead of color

**Wiring:**

1. `events/types.py:QuotaWarning` already exists — verify shape
2. Add subscriber in `tui/widgets/status_bar.py` (or wherever runtime event bus consumed)
3. Add `quota_warnings: list[QuotaWarning]` to `tui/data.py` for read access
4. Register `QuotaWarning` in `protocol/typed_events.py` (3 sites) if not already

**Tests (`python/tests/tui/test_status_bar_quota_warning.py`):**

| # | Case |
|---|---|
| 1 | `test_warn_event_renders_amber_chip` |
| 2 | `test_critical_event_renders_red_chip_latched` |
| 3 | `test_no_color_renders_text_tags` |
| 4 | `test_keypress_clears_latch` |
| 5 | `test_concurrent_warnings_all_observed` |

### Task 4 — TS mirror (~30 min)

**`packages/arc-protocol-ts/src/run-events.ts`:**

```ts
export interface QuotaWarningEventData {
  scope: 'RUN' | 'WORKFLOW' | 'SESSION' | 'PROVIDER_DAY';
  severity: 'WARN' | 'CRITICAL';
  spent_usd: number;
  cap_usd: number;
  message: string;
}

export interface QuotaWarningEvent {
  type: 'quota_warning';
  data: QuotaWarningEventData;
}

// Add to KnownRunEvent union + KNOWN_RUN_EVENT_TYPES set
```

**Tests** added to existing `packages/arc-protocol-ts/src/run-events.test.ts` (created in v0.3.1-alpha R-TS3):

| # | Case |
|---|---|
| 1 | `parseRunEvent recognizes quota_warning` |
| 2 | `isKnownEvent("quota_warning") === true` |

### Task 5 (optional) — QW-3 `/budget` command (~1 hr)

Sister to `/wallet`, scope-focused. Shows `BudgetEnforcer.preflight()` output for a proposed action:

```
> /budget --scope RUN --estimate "Run a 10k-token completion"

Preflight (scope=RUN):
  Estimated tokens: 10000
  Estimated USD:    $0.03 (claude-3-5-sonnet @ $3/1M input)
  Cap remaining:    $0.88
  Decision:         APPROVE
```

Skip if Task 1–4 take longer than expected; can ship in v0.4.1-alpha.

### Task 6 — Verify, patch, CHANGELOG, commit (one per logical change)

```bash
cd python
uv run pytest -q --ignore=tests/e2e --ignore=tests/integration 2>&1 | tail -5
# expect: 4893 + ~26 new = ~4919 passed; 0 failures

uv run ruff check src/agent_runtime_cockpit/budget \
                  src/agent_runtime_cockpit/tui \
                  tests/budget tests/tui tests/events 2>&1 | tail -3

cd ..
pnpm --filter arc-protocol-ts test 2>&1 | tail -3
pnpm build && pnpm typecheck 2>&1 | tail -3
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md \
                                    docs/phases.md docs/release/checklist.md

# Export patches
mkdir -p patches/r01/v0.4.0-alpha

git diff main -- python/src/agent_runtime_cockpit/budget/wallet.py \
                 python/src/agent_runtime_cockpit/budget/__init__.py \
                 python/tests/budget/test_token_wallet.py \
                 > patches/r01/v0.4.0-alpha/001_token_wallet.patch

git diff main -- python/src/agent_runtime_cockpit/tui/slash/wallet.py \
                 python/src/agent_runtime_cockpit/tui/slash/__init__.py \
                 python/tests/tui/test_slash_wallet.py \
                 > patches/r01/v0.4.0-alpha/002_slash_wallet.patch

git diff main -- python/src/agent_runtime_cockpit/tui/widgets/status_bar.py \
                 python/src/agent_runtime_cockpit/tui/data.py \
                 python/src/agent_runtime_cockpit/protocol/typed_events.py \
                 python/tests/tui/test_status_bar_quota_warning.py \
                 python/tests/events/test_quota_warning_typed_event_roundtrip.py \
                 > patches/r01/v0.4.0-alpha/003_quota_warning_consumer.patch

git diff main -- packages/arc-protocol-ts/src/run-events.ts \
                 packages/arc-protocol-ts/src/run-events.test.ts \
                 > patches/r01/v0.4.0-alpha/004_ts_mirror_quota_warning.patch

# Optional Task 5
git diff main -- python/src/agent_runtime_cockpit/tui/slash/budget.py \
                 python/tests/tui/test_slash_budget.py \
                 > patches/r01/v0.4.0-alpha/005_slash_budget.patch
```

**Commit sequence (one per logical change, conventional-commits):**

```bash
git add python/src/agent_runtime_cockpit/budget/wallet.py \
        python/src/agent_runtime_cockpit/budget/__init__.py \
        python/tests/budget/test_token_wallet.py \
        patches/r01/v0.4.0-alpha/001_token_wallet.patch \
        CHANGELOG.md
git commit -m "feat(budget): TokenWallet read-only view over BudgetEnforcer (R-01 1/4)

Adds TokenWallet wrapping budget/schema.py:BudgetEnforcer with a frozen
WalletSnapshot per scope (RUN/WORKFLOW/SESSION/PROVIDER_DAY). Fail-closed
on unknown scope. Never mutates EnforcementContext. No LLM in path (CoSAI).

Cache hit rate computed from R-03 OTel attrs (cache_read_input_tokens /
total_input_tokens). 0.0 when no data.

Tests: 10 cases."

git add python/src/agent_runtime_cockpit/tui/slash/wallet.py \
        python/src/agent_runtime_cockpit/tui/slash/__init__.py \
        python/tests/tui/test_slash_wallet.py \
        patches/r01/v0.4.0-alpha/002_slash_wallet.patch \
        CHANGELOG.md
git commit -m "feat(tui): /wallet slash command surfaces TokenWallet snapshot (R-01 2/4)

Renders per-scope spent/cap/remaining/cache-hit-rate. Honors first-launch cap.
NO_COLOR text-tag fallback. Fail-closed render does not crash TUI.

Tests: 6 cases."

git add python/src/agent_runtime_cockpit/tui/widgets/status_bar.py \
        python/src/agent_runtime_cockpit/tui/data.py \
        python/src/agent_runtime_cockpit/protocol/typed_events.py \
        python/tests/tui/test_status_bar_quota_warning.py \
        python/tests/events/test_quota_warning_typed_event_roundtrip.py \
        patches/r01/v0.4.0-alpha/003_quota_warning_consumer.patch \
        CHANGELOG.md
git commit -m "feat(tui): QuotaWarning event consumer flashes status bar (R-01 3/4)

Subscribes status_bar.py to events/types.py:QuotaWarning. WARN → amber 3s
then latched ⚠. CRITICAL → red latched 🛑 until any keypress. NO_COLOR
fallback to [WARN]/[CRITICAL] text tags.

Registers QuotaWarning in typed_events.py KnownRunEvent + is_known_event
+ parse_typed_event type_map (3 Python sites per project rule).

Tests: 5 TUI + 3 protocol round-trip = 8 cases."

git add packages/arc-protocol-ts/src/run-events.ts \
        packages/arc-protocol-ts/src/run-events.test.ts \
        patches/r01/v0.4.0-alpha/004_ts_mirror_quota_warning.patch
git commit -m "feat(arc-protocol-ts): mirror QuotaWarning typed event (R-01 4/4)

Adds QuotaWarningEvent / QuotaWarningEventData interfaces. Extends
KnownRunEvent union + KNOWN_RUN_EVENT_TYPES set (1 TS site per project rule).

Tests: 2 cases added to run-events.test.ts (from R-TS3 backfill)."

# Optional Task 5
git add python/src/agent_runtime_cockpit/tui/slash/budget.py \
        python/tests/tui/test_slash_budget.py \
        patches/r01/v0.4.0-alpha/005_slash_budget.patch \
        CHANGELOG.md
git commit -m "feat(tui): /budget preflight slash command (QW-3)

Sister to /wallet — runs providers/budget_preflight.py:preflight_with_estimator()
for a proposed action and shows estimated USD / cap remaining / decision.

Tests: 4 cases."
```

### CHANGELOG.md entries (append under `[Unreleased]`)

```md
### Added
- **Budget**: `TokenWallet` read-only view over `BudgetEnforcer` with frozen
  `WalletSnapshot` per scope (RUN/WORKFLOW/SESSION/PROVIDER_DAY). Cache hit
  rate populated from R-03 OTel attrs. Fail-closed on unknown scope. (R-01)
- **TUI**: `/wallet` slash command renders per-scope spent/cap/remaining/
  cache-hit-rate. Honors first-launch cap. NO_COLOR fallback. (R-01)
- **TUI**: `QuotaWarning` event consumer — status bar flashes amber on WARN,
  latches red on CRITICAL until any keypress. (R-01)
- **Protocol**: `QuotaWarning` typed event registered in
  `protocol/typed_events.py` (3 Python sites) and
  `packages/arc-protocol-ts/src/run-events.ts` (1 TS site). (R-01)
- **TUI** *(optional)*: `/budget` slash command exposes
  `providers/budget_preflight.py:preflight_with_estimator()` for ad-hoc
  preflight estimation. (QW-3)
```

---

## 5. Verification gates (all must pass before tagging)

| Gate | Command | Expected |
|---|---|---|
| Python suite | `cd python && uv run pytest -q --ignore=tests/e2e --ignore=tests/integration` | 4893 + ~26 = ~4919 passed / 0 failed |
| Python ruff | `uv run ruff check src/agent_runtime_cockpit/{budget,tui} tests/{budget,tui,events}` | clean |
| TS unit + coverage | `pnpm --filter arc-protocol-ts test --coverage` | green, ≥ R-TS3 thresholds |
| Workspace build | `pnpm build` | clean |
| Workspace typecheck | `pnpm typecheck` | clean |
| Banned claims | `bash scripts/check-banned-claims.sh ...` | clean |
| GitHub Actions on push | `node`, `python`, `ARC Roadmap Gate`, `signing-preflight`, `e2e` | all ✅ |
| **Invariant 1: No EnforcementContext mutation** | `grep -rn "_enforcement_context\.[a-z_]* =" src/` | 0 hits outside `security/context.py` |
| **Invariant 2: No LLM in budget path** | Inspect new files; assert no provider imports in `budget/wallet.py` | by review |
| **Invariant 3: Fail-closed on unknown budget** | `test_snapshot_unknown_scope_fail_closed` | passes |
| **Invariant 4: Additive protocol only** | `git diff main -- protocol/typed_events.py packages/arc-protocol-ts/src/run-events.ts` | only additions, no removals |

**Pre-existing acceptable failures (only these allowed):**
- `tests/auth/test_auth_manager.py::test_provider_statuses_fallback_to_stored_creds`
- `tests/tasks/test_task_executor.py::test_concurrent_task_execution`

Any other red on this branch → **STOP and report**, do not `@pytest.mark.skip`.

---

## 6. Report-back template

```text
v0.4.0-alpha R-01 readiness report:

[ ] Task 0 audit (3 lines confirming BudgetEnforcer location + QuotaWarning shape + slash registry)
[ ] Tests: 4893 baseline → N (delta +M)
[ ] Task 1 TokenWallet commit SHA + LOC (~140 src + ~200 tests)
[ ] Task 2 /wallet commit SHA + LOC (~70 src + ~150 tests)
[ ] Task 3 QuotaWarning consumer commit SHA + LOC (~60 src + ~220 tests)
[ ] Task 4 TS mirror commit SHA + LOC (~10 src + ~40 tests)
[ ] Task 5 /budget (QW-3) commit SHA OR "skipped, reason: ..."
[ ] Patches in patches/r01/v0.4.0-alpha/ (4 or 5 files; total LOC)
[ ] 11 of 11 verification gates green
[ ] Pre-existing-acceptable failures only (≤2)
[ ] No EnforcementContext mutation outside security/context.py
[ ] No LLM imports in budget/wallet.py
[ ] CHANGELOG [Unreleased] updated with 4–5 Added bullets
[ ] Roadmap R-TS4 row added pointing at this tag

Branch spec/r01-token-wallet ready to merge.
Do NOT tag yet. Awaiting your go.
```

---

## 7. Merge + tag sequence (after user green-light only)

```bash
# Author MERGE_NOTES.md
cat > MERGE_NOTES.md <<'EOF'
# v0.4.0-alpha — R-01 TokenWallet + /wallet + QuotaWarning Consumer

Closes the visibility/action loop opened by v0.3.0-alpha:
- v0.3.0-alpha P0-4 showed token *usage* in status bar
- v0.3.0-alpha R-03 made cache hits *measurable* via OTel
- v0.4.0-alpha R-01 makes budget *actionable* — TokenWallet view, /wallet
  command, QuotaWarning consumer

## What's new
1. `TokenWallet` (budget/wallet.py) — read-only frozen snapshot over
   `BudgetEnforcer`. Per-scope spent/cap/remaining/cache-hit-rate. Fail-closed.
2. `/wallet` slash command — renders the snapshot. Honors first-launch cap.
   NO_COLOR fallback. (~150 LOC)
3. `QuotaWarning` event consumer in status bar — amber WARN, latched red
   CRITICAL until any keypress. Wires events/types.py:QuotaWarning into TUI.
4. `QuotaWarning` typed event registered in protocol (3 Python sites + 1 TS).
5. (Optional) `/budget` slash command — preflight estimate via
   providers/budget_preflight.py.

## What's NOT in this tag
- R-02 (compaction triage) — queued for v0.5.0-alpha
- QW-4 (MCP output handle virtualization) — queued for v0.5.0-alpha or later
- Wallet persistence across CLI invocations — out of scope (single-session
  read view only; persistence handled by BudgetEnforcer storage)

## Invariants verified
- No EnforcementContext mutation (frozen dataclass + ContextVar pattern)
- No LLM in any decision path (CoSAI compliance)
- Fail-closed on unknown budget
- Additive protocol only (extra='ignore' forward-compat)
- BudgetEnforcer in budget/schema.py is authoritative; legacy budget.py untouched

## Verification
- Python: 4919 passed / 0 failed (+26 from v0.3.1-alpha)
- TS: green, coverage ≥ v0.3.1-alpha (R-TS3) thresholds
- pnpm build + typecheck clean
- banned-claims clean
- GitHub Actions: 5/5 green on spec branch
- All 11 verification gates green

## Commits
- <SHA> feat(budget): TokenWallet read-only view (R-01 1/4)
- <SHA> feat(tui): /wallet slash command (R-01 2/4)
- <SHA> feat(tui): QuotaWarning event consumer (R-01 3/4)
- <SHA> feat(arc-protocol-ts): mirror QuotaWarning typed event (R-01 4/4)
- <SHA> feat(tui): /budget preflight slash command (QW-3)  [optional]
EOF

# Merge
git checkout main && git pull --ff-only
git merge --no-ff spec/r01-token-wallet -m "$(cat MERGE_NOTES.md)"

# Tag
git tag -a v0.4.0-alpha -m "R-01 TokenWallet + /wallet + QuotaWarning consumer.
Closes the visibility/action loop opened by v0.3.0-alpha (P0-4 usage display)
and v0.3.0-alpha (R-03 cache measurability). Per TOKEN_SAVING_PLAN-2.md §15.
See MERGE_NOTES.md for full delta."

# Push
git push origin main v0.4.0-alpha
```

---

## 8. What lands AFTER v0.4.0-alpha

### v0.5.0-alpha candidates (pick one for the sprint after this)

**Option A — R-02 (compaction triage)**
- *Highest behavior-change leverage.* Deterministic heuristics for context
  window approach (no LLM in decision per CoSAI).
- Triggers on `context_used / context_limit >= 0.85` (threshold from R-TS-config).
- Actions: oldest-first eviction, attachment-handle virtualization, system
  prompt deduplication.
- Estimated 1 week including spec write-up.

**Option B — QW-4 (MCP output handle virtualization)**
- *Highest token-saving leverage for tool-heavy workloads.* Per
  TOKEN_SAVING_PLAN-2.md, the headroom data shows 40–80% savings on
  tool-heavy traces.
- Large MCP tool outputs stored as handles in `data.py`; expand on demand
  via `/expand <handle>`.
- Estimated 3–4 days.

**Option C — both, with R-02 leading**
- Pair them: R-02 evicts to handles created by QW-4. Cohesive but ~10 days.

User decides at the v0.4.0-alpha release review.

---

## 9. Cross-references

- Master plan: `TOKEN_SAVING_PLAN-2.md` (1419 lines, authoritative)
- Sibling spec: `docs/spec/v0.3.1-alpha-ci-debt.md` (the prereq tag)
- Roadmap: `docs/roadmap.md` — R-TS1 (research) / R-TS2 (P0) / R-TS3 (TS coverage) / R-TS4 (this)
- Project rules: `AGENTS.md`
- CoSAI rule: no LLM in budget/security decisions (in-repo doc reference)
