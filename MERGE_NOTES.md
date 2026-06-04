# v0.4.1-alpha — Budget Persistence + Pricing Refresh

Discharges 2 of 4 deferrals from v0.4.0-alpha. Two remain deferred (see below).

## What shipped
1. **Budget persistence** — SQLite WAL backend (budget/storage.py, 210 LOC).
   SESSION + PROVIDER_DAY survive process restart via crash-safe WAL journal
   mode. RUN correctly resets per-enforcer-instance. Concurrent multi-process
   accumulation safe. Corrupt DB fails closed.
2. **Tier-1 pricing refresh** — 17 new model rows:
   - Anthropic: Haiku 4.5, Sonnet 4.6, Opus 4.6, Opus 4.7 (+ tokenizer
     drift flag), Haiku 3 (legacy), Opus 4.1 (legacy)
   - OpenAI: GPT-5 family + GPT-5.4 family + GPT-5.5 + GPT-4.1 family
   - **OpenAI cache discount bumped 50% → 90% for GPT-5.x current-gen.**
     Wallet now correctly shows the savings users were already getting.
     gpt-4o-mini legacy preserved at 50% (guarded by test_gpt4o_mini_legacy_50pct_cache).
     GPT-4.1 family at 75%.

## Still deferred (tracked)
- **Gemini pricing rows** — No standalone Gemini cost file; ARC doesn't
  currently route to Vertex/AI Studio directly. Gemini exists only as a
  single proxy entry (ag/gemini-3.5-flash-extra-low via agentrouter).
  Gemini 3.x rows, gemini-2.0-flash deprecation warning, and
  cache_storage_usd_per_million_per_hour field defer to whichever sprint
  adds direct Gemini/Vertex routing.
- **Anthropic inline rate consolidation** — anthropic.py has inline cost rates
  alongside anthropic_cost.py. Tracking item: consolidate to single source of
  truth in a future patch.
- **OTel underscored attribute removal** — emitting both forms; removal
  scheduled for v0.6.0-alpha per overlap policy.
- **EnforcementContext-aware wallet test** — vacuous against current wallet.

## Verification
- Python: 4937 passed / 0 failed (+15 from v0.4.0-alpha)
- 5 persistence invariant gates green (restart, RUN-reset, corrupt-fail-closed,
  concurrent-safe, in-memory parity)
- TS: unchanged
- pnpm build + typecheck + banned-claims: clean

## Commits
- b6c4beb feat(budget): SQLite WAL persistence for SESSION + PROVIDER_DAY
- edfa2b1 feat(providers): pricing snapshot 2026-Q2 refresh (Tier-1)
- df6ca9c chore(release): roadmap R-TS4/R-TS5 rows + CHANGELOG + patches
