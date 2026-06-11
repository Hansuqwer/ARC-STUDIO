# ARC v2 — Tranche-2 Fixtures (69/69) + CI Gate Wiring

Date: 2026-06-11 · Branch: `arc-v2/sprint-1-protocol-bridge`

## 1. Fixture coverage closed: 38/69 → **69/69**

`scripts/generate-tranche2-fixtures.py` (same hard guards as tranche 1: canonical
registry validator + Pydantic model must accept every fixture before write;
refuses overwrite; purely additive) authored the remaining 31 kinds:

| Family | Kinds | Panel relevance |
|---|---|---|
| NODE_* (3) | NODE_STARTED / UPDATE / FAILED | SwarmGraph DAG (Sprint 8) |
| CONTRACT_* (3) + EVIDENCE_REF_CREATED + POLICY_BYPASS_WARNING | contract lifecycle, evidence refs, policy bypass warnings | consensus evidence cards (Sprint 8) |
| CONSENSUS_* (3) | differentiator, eval, eval-run | consensus cards (Sprint 8) |
| BATTLE_* (7) | full battle lifecycle | deferred surface — fixtures exist for decode safety, not panel work |
| Deterministic gate decisions (2) | CAPABILITY_CARD_DECISION, MCP_CALL_DECISION | MCP workbench risk gate UI (Sprint 9) |
| EVAL_POLICY_* (2) | recommended / applied | settings/policy panels (Sprint 9) |
| Escape hatches (2) | RAW, CUSTOM | KnownRunEvent::Unknown path exercised with *registered* kinds |
| Budget/context/ops (8) | QUOTA_WARNING, CONTEXT_COMPACTED, TOOL_OUTPUT_VIRTUALIZED, MODEL_CHANGED, PRICING_FEED_REFRESHED, BUDGET_BROKER_SYNC, OBSERVABILITY_EXPORT_STARTED | status rail / ops dashboard (Sprint 7) |

Evidence: Rust conformance 7/7 green, coverage report regenerated (**69/69,
0 uncovered**); JSON-Schema leg **87/87** (69 per-instance + 18 scenario);
v1 `tests/protocol` + `tests/web` **220 passed** (includes the repo's own
fixture↔EVENT_TYPES parity guard).

Scope note: panel *dispositions* are unchanged — BATTLE_* stays a deferred
surface per the ledger; having fixtures ≠ having panels. This closes the
decode-safety dimension only.

## 2. CI gate: `.github/workflows/arc-v2-rust.yml` (additive, path-filtered)

Enforces in CI exactly what the sprint exit gates enforce locally:

1. `scripts/check-arc-ui-facade.sh` (facade boundary)
2. main `Cargo.lock` framework-free (`gpui|gpui-ce|floem|masonry|xilem` ban)
3. `cargo fmt --all --check` (both workspaces brought to canonical fmt in this
   commit — 55 mechanical diffs applied, all tests re-verified green after)
4. `cargo clippy --workspace --all-targets -- -D warnings` (main + spikes;
   `unwrap_used = deny` rides along via workspace lints)
5. `cargo test --workspace` (fixture conformance, ordered-replay oracle, shell
   model) + spike-harness tests
6. **Coverage-report freshness**: if `reports/fixture-coverage.md` doesn't match
   what the tests regenerate, the build fails — fixtures can't drift past CI
   silently.

Path-filtered to `rust/**`, `protocol/fixtures/**`, the facade script, and
itself; touches no existing workflow; rollback = delete one file.

## 3. Sandbox-verified before commit

| Check | Result |
|---|---|
| cargo fmt --check (rust/ and rust/spikes/) | clean after apply |
| clippy -D warnings equivalent (both workspaces) | 0 warnings |
| Main workspace tests | all green (4 non-empty suites) |
| spike-harness tests | 17 green |
| Facade gate | OK |
| Coverage 69/69 + fresh report | verified |
| Schema validation | 87/87 |
| v1 regression | 220 passed |

## Rollback

Delete: 31 tranche-2 fixture files, `scripts/generate-tranche2-fixtures.py`,
`.github/workflows/arc-v2-rust.yml`, this report. The fmt commit is cosmetic
and reverts with the branch.

## State of the branch after this commit

Sandbox-executable runway is now **exhausted**. Remaining critical path:
1. Owner verdict on ADR-0002 addendum (ARC2-13) — draft has sign-off block.
2. Sprint-3 spike on desktop hardware — runbook ready, harness tested,
   workloads deterministic, decision matrix templated.
3. TS round-trip leg: closed locally 2026-06-11 after jest env sync.
   Evidence: `pnpm --filter @arc-studio/protocol test` passed (14 suites / 185
   tests), `pnpm --filter @arc-studio/protocol build` passed, and v1 regression
   `PYTHONPATH=src uv run pytest tests/protocol tests/web -q` passed (220 tests).
