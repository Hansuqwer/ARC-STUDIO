# v0.4.0-alpha — R-01 TokenWallet + /wallet + /budget + QuotaWarning Consumer

Closes the visibility/action loop opened by v0.3.0-alpha:
- v0.3.0-alpha P0-4 showed token *usage* in the status bar
- v0.3.0-alpha R-03 made cache hits *measurable* via OTel
- v0.4.0-alpha R-01 makes budget *actionable* — TokenWallet view, /wallet
  + /budget commands, QuotaWarning consumer in TUI

## What shipped
1. `TokenWallet` (budget/wallet.py) — read-only frozen snapshot over
   BudgetEnforcer. Per-scope spent/cap/remaining/cache-hit-rate. Fail-closed
   on unknown scope. PROVIDER_DAY gracefully skipped when provider_id=None.
2. `/wallet` slash command — renders the snapshot. Honors first-launch cap.
   NO_COLOR fallback.
3. `/budget` slash command (QW-3 bonus) — preflight estimate via
   providers/budget_preflight.preflight_with_estimator().
4. `QuotaWarning` event consumer in status bar — amber WARN, latched red
   CRITICAL until any keypress. Wires events/types.py:70 into the TUI.
5. `QuotaWarning` typed event registered in protocol (3 Python sites + 1 TS).
6. OTel cache attribute spec alignment — emits both dotted form
   (gen_ai.usage.cache_read.input_tokens, spec) and underscored R-03 form
   (gen_ai.usage.cache_read_input_tokens, backward compat).

## Invariants verified
- No EnforcementContext mutation
- No LLM imports in budget/wallet.py (enforced by import-guard test)
- Fail-closed on unknown budget scope
- Additive protocol only (extra='ignore' forward-compat)
- BudgetEnforcer in budget/schema.py is authoritative; legacy budget.py untouched

## Verification
- Python: 4922 passed / 0 failed (+29 from v0.3.0-alpha baseline)
- TS: 143 passed (+2 QuotaWarning cases on top of v0.3.1-alpha)
- pnpm build + typecheck clean
- banned-claims clean
- 4 patches in patches/r01/v0.4.0-alpha/ (832 lines)

## Deferred to v0.4.1-alpha (tracked)
- **Budget persistence**: BudgetState is in-memory; SESSION + PROVIDER_DAY
  reset on every CLI launch. Wallet display is honest about live state — no
  silent corruption. Audit: docs/research/budget-persistence-audit.md.
  Fix path: SQLite WAL or append-only JSONL ledger per audit §4.
- **Pricing table refresh**: providers/*_cost.py not updated for OpenAI cache
  50%→90% / Vertex cache 75%→90%+storage / new model rows. Wallet under-shows
  savings on OpenAI/Vertex. Source: docs/research/pricing-snapshot-2026Q2.md.
- **OTel underscored attribute removal**: dotted+underscored both emitted now.
  Underscored deprecated; remove in v0.6.0-alpha.
- **EnforcementContext-aware wallet test**: spec called for it; current
  TokenWallet has no enforcement-context-derived state, so the test would be
  vacuous. Reintroduce when/if wallet reads ContextVar state.

## Commits
- a4996ef feat(budget): TokenWallet read-only view (R-01 1/5)
- 71eb9f2 feat(tui): /wallet + /budget slash commands (R-01 2/5)
- c98fccd feat(tui): QuotaWarning event consumer (R-01 3/5)
- c15f422 feat(protocol+ts): QUOTA_WARNING typed event mirror (R-01 4/5)
- 5eb0256 chore(release): OTel spec alias + test backfills + 4 patches + CHANGELOG (R-01 5/5)
