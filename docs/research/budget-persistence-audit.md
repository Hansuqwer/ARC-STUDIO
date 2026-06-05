# Budget Persistence — Retrospective Audit

> **Status:** ✅ **EXECUTED (retrospective)** — 2026-06-06.
> The design question this runbook posed ("SQLite WAL vs append-only JSONL
> ledger") was **already resolved in implementation**: `SQLiteWALStorage`
> shipped in v0.4.1 (`R-TS5 Budget Persistence`, roadmap Baseline Complete).
> This document audits what actually shipped, records verification evidence,
> and states the residual limitations honestly rather than re-deciding a
> settled design.

---

## §1 — Original question (from the brief)

`docs/spec/v0.4.1-alpha-persistence-and-pricing.md §24` asked the implementer to
pick a persistence backend for budget spend that survives process restart:

> (a) Budget persistence — pick SQLite WAL **OR** append-only JSONL ledger per
> `docs/research/budget-persistence-audit.md §4 patterns`.

SESSION + PROVIDER_DAY spend reset on every process start in v0.4.0, which made
the wallet meaningless across CLI invocations.

## §2 — What shipped (decision: SQLite WAL)

`python/src/agent_runtime_cockpit/budget/storage.py`:

| Component | Role |
|---|---|
| `BudgetStorage` (ABC) | persistence interface (`load_session`, `load_provider_day`, `save_session`, `save_provider_day`, `reset_session`) |
| `InMemoryStorage` | default for tests/back-compat; preserves v0.4.0 reset-on-exit behaviour |
| `SQLiteWALStorage` | durable; SESSION + PROVIDER_DAY survive restart; also backs the MCP handle store |
| `default_storage()` | factory → `SQLiteWALStorage` for CLI sessions |

Design choices, with rationale:

- **SQLite WAL over JSONL ledger.** A JSONL append-only ledger needs periodic
  compaction and a full re-read to compute current spend; SQLite gives O(1)
  point reads, atomic UPSERT, and crash-safe WAL without bespoke compaction.
  For a single-user local tool this is the lower-maintenance choice.
- **Scope persistence is deliberate.** SESSION and PROVIDER_DAY persist; RUN and
  WORKFLOW are intentionally in-memory (per-run/per-workflow reset is by design).
- **Fail-closed.** A corrupt DB raises on open rather than silently returning $0
  (verified — see §3).
- **Storage path** is platform-appropriate (`~/Library/Application Support/…`
  on macOS, `$XDG_DATA_HOME/…` on Linux).

## §3 — Verification evidence (2026-06-06)

`uv run pytest tests/budget/test_persistence.py -v` → **8 passed**:

| Test | Proves |
|---|---|
| `test_in_memory_parity_with_sqlite` | identical spend after identical ops on both backends |
| `test_session_survives_restart` | SESSION reloads after a simulated restart (new enforcer, same DB) |
| `test_provider_day_survives_restart` | PROVIDER_DAY persists and reloads via storage |
| `test_run_scope_resets_per_enforcer_instance` | RUN scope is NOT persisted (resets per instance) |
| `test_corrupt_db_fails_closed` | corrupt DB raises; never silently returns $0 |
| `test_factory_default_returns_sqlite` | `default_storage()` returns `SQLiteWALStorage` |
| `test_in_memory_storage_no_persistence` | baseline v0.4.0 behaviour preserved |
| `test_concurrent_accumulation` | two threads spending in parallel → no crash, no corruption |

## §4 — `database is locked` resolution

The v0.8 active-track audit flagged a P0 "SQLite `database is locked` in budget
storage (confirmed failing test)." The shipped code resolves it (documented in
the source):

1. `PRAGMA busy_timeout = 5000` is set **before** any contended statement
   (including the `journal_mode = WAL` switch), so concurrent writers wait up to
   5 s instead of failing immediately with `SQLITE_BUSY`.
2. The `_conn()` context manager **closes the connection promptly** after each
   transaction. Leaving connections open leaked WAL read/write marks and was the
   actual cause of the contention; `with conn:` only manages the transaction,
   not the connection lifetime.

`test_concurrent_accumulation` (2 threads × 10 writes) passes with no errors,
confirming the lock contention is gone for the single-user concurrency the tool
targets.

## §5 — Residual limitations (stated honestly)

- **Cross-process accumulation is last-writer-wins, not atomic
  read-modify-write.** Each `BudgetEnforcer` loads its session total on
  construction, accumulates in memory, and `save_session()` overwrites with the
  absolute value. Two enforcers with overlapping lifetimes (e.g., two `arc`
  processes spending at once) can therefore lose one another's updates — the
  later writer wins. `test_concurrent_accumulation` reflects this honestly: it
  asserts the persisted total is **≥ one thread's work**, not the sum of both.
  For a single-user local CLI this is acceptable; it is **not** safe for
  multi-process or shared-host budget enforcement. A future fix would make
  `record()` do an in-transaction `UPDATE … SET amount = amount + ?` instead of
  load-then-overwrite.
- **No schema migrations yet.** `SCHEMA_VERSION = 1`; the `_init_db()` path has a
  `# Future: run migrations` placeholder but no migration runner. A v2 schema
  change would need that wired first.
- **RUN / WORKFLOW scope intentionally non-durable** — by design, documented
  here so it is not mistaken for a persistence gap.

## §6 — Verdict

The persistence design question is **settled**: SQLite WAL shipped, survives
restart, fails closed, and the lock-contention defect is fixed — all backed by 8
passing tests. The only material caveat is the cross-process last-writer-wins
accumulation, which is acceptable for the single-user local scope ARC targets
and is now recorded as a known limitation rather than an undocumented surprise.
No further work is required for the single-user release; the atomic-increment
upgrade is a prerequisite only if multi-process budget sharing is ever in scope.

## §7 — Cross-references

- Implementation: `python/src/agent_runtime_cockpit/budget/storage.py`
- Tests: `python/tests/budget/test_persistence.py` (8 passed 2026-06-06)
- Spec that requested it: `docs/spec/v0.4.1-alpha-persistence-and-pricing.md`
- Roadmap entry: `R-TS5 Budget Persistence + Pricing Refresh` (Baseline Complete)
- Sibling persistence concern: `docs/research/QW-4-mcp-handle-design.md`
  (handle store shares this SQLite backend)
