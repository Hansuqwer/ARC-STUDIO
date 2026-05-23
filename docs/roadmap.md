# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.  
**Created:** 2026-05-17  
**Last reality refresh:** 2026-05-22 — Architecture review foundation items (R14-R26) added for post-v0.1 execution plan.  
**Current evidence anchor:** local worktree | 989 Python tests, 762 TS tests passed (pre-v0.1 baseline); R14-R26 defined for v0.2 foundation work per architecture review.  
**Update rule:** Update this file in the same commit whenever implementation status changes. Do not create replacement roadmap/status/implementation markdowns.

## Status Vocabulary

Use only these values in roadmap status lines:

| Status | Meaning |
|---|---|
| Not Started | Planned but no implementation slice has begun. |
| In Progress | Implementation is active and not yet accepted. |
| Baseline Complete | Minimum accepted behavior exists with tests/evidence; polish may remain. |
| Polished Complete | Baseline plus user-facing polish is accepted. |
| Blocked | Cannot proceed without an external decision, approval, secret, destructive action, or unavailable dependency. |
| Deferred | Intentionally out of current scope; requires explicit roadmap change to resume. |

Status lines should follow: `Status: <Status Value> | Evidence: <commit/run/test anchor> | Notes: <one sentence>`.

## Current Baseline

- Canonical app: `applications/browser` + `packages/arc-extension`.
- Legacy `theia-extensions/*` and `packages/arc-browser-app` are archived under `docs/archive/`.
- GitHub CI green on `7a300fe` (python, node, ARC Roadmap Gate, signing-preflight, e2e). Commit `4b0f6b5` implements all 6 previously-deferred items from the Active Work Ledger. All Baseline Complete phases evaluated for polish; all ship at current status for v0.1 (polish deferred to v0.2).
- Release-scope CLI/IDE basics are implemented and tested.
- Remaining work is product depth, not repo stabilization.

## Non-Negotiable Scope Boundaries

- No broad live/provider-backed SwarmGraph adoption claim until real provider-backed adoption paths are implemented and tested.
- No adapter-wide keyed audit claim until every claimed run path writes/verifies keyed audit material.
- No production/concurrent-user/tenant isolation claim.
- LM Arena remains stub-default/gated and out of v0.1 product scope.
- Electron packaging/signing remains post-v0.1 unless explicitly reprioritized.
- `.env` history scrub requires explicit release date + force-push/history-rewrite approval.

## Gated Execution Paths

| Path | Required Gates | Exact Confirmation | What It Proves | What It Does Not Prove | Evidence |
|---|---|---|---|---|---|
| `langgraph+swarmgraph` local-real smoke | `ARC_REAL_RUNTIME_SMOKE=1`, `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`, installed local deps | None beyond smoke invocation | Narrow local, non-provider-backed LangGraph + SwarmGraph execution path can run when dependencies and both gates are present | No provider-backed execution; no broad adoption readiness; no paid calls | Locked R6 baseline; opt-in smoke/manual path |
| `arc providers action` via 9router | Live-provider test env gate, paid-call opt-in, env/key references only | `RUN_PROVIDER_ACTION:<provider>:<model>` | One narrow gated provider action path and ARC local accounting | No remote quota reset; no provider-backed adoption; no SwarmGraph runtime execution | `9184f9b` with `9router` / `nvidia/minimaxai/minimax-m2.7` |
| LM Arena | None accepted for product use | N/A | Stub/default arena behavior only | No live arena product feature | Fiction list / release scope |

## Producer Inventory

Only render rich UI data from event producers listed here. Missing producers must yield absent/degraded UI states, not fabricated data.

| Event/Data Type | Producer Path | Status | UI Consumers |
|---|---|---|---|---|
| Active run SSE transport events | `EventBroker`/`JobSupervisor`, `/api/runs/{id}/events`, `/api/sse/proof` stub | Baseline Complete | Event Stream, Run Timeline |
| `RUN_STARTED` / terminal events | SSE proof stub and supported run paths | Baseline Complete | Event Stream, Run Timeline |
| SwarmGraph topology | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Consensus/vote events | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Measured cost/token events | `langgraph+swarmgraph` adoption runner (first producer) | Baseline Complete | SwarmGraph Insight Cost panel (renders provider/model/tokens/cost/source/measured from explicit events) |
| HITL prompt/response/timeout | `JobSupervisor` HITL flow + CLI/IDE response paths | Baseline Complete | Assurance tab, Runs tab basics |
| Audit chain material | ARC audit paths and keyed audit CLI path where specific run writes material | Conditional | Assurance tab, audit verify/export |
| Effect-boundary journal entries | `arc runs fork` CLI command | Baseline Complete | Fork/replay UX via CLI `arc runs fork` |

## Documentation Inventory

| Location | Purpose |
|---|---|
| `docs/roadmap.md` | Authoritative roadmap/status. |
| `docs/phases.md` | Authoritative ordered execution plan. |
| `docs/adr/` | Architecture decisions. |
| `docs/research/` and `docs/wiki/research-context/` | Supporting research/scaffolds only, not status. |
| `docs/release/checklist.md` | Release evidence and gates. |
| `docs/archive/` | Historical context only. |
| `docs/handover/` | Thin pointers/context; must defer to locked docs. |
| `scripts/check-banned-claims.sh` | Enforced release-claim guard. |

## R1 — Live Run Streaming Product Path

**Goal:** Active runs stream events into IDE views while running, not only replay stored traces.

**Current:** Complete Phase 1 vertical baseline plus Phase 8 local daemon productization baseline. Python SSE supports active/replay modes and terminal/disconnected semantics; Theia exposes a typed `streamActiveTrace()` proxy that can use an explicit/requested Python web base URL or `ARC_PYTHON_DAEMON_URL`; Event Stream/SwarmGraph Insight surfaces distinguish live/replay/disconnected states; `/api/sse/proof` has deterministic limited-local coverage only and is not evidence of broad runtime live event support.

**Deliverables:**
- Python active run stream endpoint or command path backed by `EventBroker`/`JobSupervisor`.
- Theia backend subscription/proxy with env filtering and cancellation safety.
- Event Stream/Run Timeline live state: connecting, live, replay, disconnected.
- Stub-backed e2e proving live events arrive during a launched run.

**Acceptance:**
- Unit/web tests for active stream lifecycle.
- E2E launches or connects to a stub live stream and observes at least `RUN_STARTED` and terminal event live.
- Docs distinguish broker-backed active stream, deterministic SSE proof stub, and stored-trace replay.

**Status:** Baseline Complete for configured local daemon/stub runtime live event streams. Evidence: local Phase 8 verification on `bec8d4b` worktree (`python` web SSE tests, arc-extension tests/build, browser build/e2e, `scripts/check-pr.sh`). Notes: IDE live mode can connect to configured Python daemon/local runtime streams and handles terminal/degraded states while preserving replay-not-live copy; this is not a broad runtime/provider-backed live event claim.

**Follow-up:** Browser e2e logs known Theia async contribution warnings; Phase 13 (R9) captured the exact warning fingerprint in the e2e test and proved them harmless/intentionally-accepted. Phase 8.1 (IDE-to-daemon SSE e2e harness) completed separately.

## R2 — IDE Runtime Setup + Config Wizard

**Goal:** Users can configure runnable adapters/profiles from IDE without editing shell env manually.

**Current:** CLI config/profiles/workspace commands exist; ChatTab exposes runtime/profile selectors; ConfigTab now loads backend runtime capabilities, profiles, isolation providers/status, safe YAML-backed config save fields, provider key env-var references, copy-safe config snapshots, persisted profile selection copy, and a capability-derived Runtime Setup Wizard with missing env/dependency/manual remediation guidance. Dedicated export-target helper UI exists for CrewAI, OpenAI Agents, and LlamaIndex using env-var references only.

**Deliverables:**
- Adapter readiness details with concrete missing env/dependency actions.
- Config editor for ARC YAML-backed settings/profiles.
- Workspace trust + isolation profile display/config.
- Export-target helpers for CrewAI/OpenAI Agents/LlamaIndex without storing raw secrets.

**Acceptance:**
- Static/contract tests for UI wiring.
- Backend method tests for config read/write/dry-run.
- No secrets persisted directly; env/keychain references only.

## R3 — Provider, Quota, Cost Controls UI

**Goal:** Existing CLI/provider diagnostics and quota controls are visible and actionable in IDE.

**Current:** Chunks 3.1-3.3 hardened to Baseline Complete. CLI provider diagnostics/quota commands work; IDE has provider diagnostics with typed telemetry parsing/tests covering empty/partial/malformed/success states, targeted confirmation before local quota-counter reset (local-only copy, no remote/provider reset implication), a profile-linked cost policy summary, backend cost-gate metadata/enforcement, and hardened explicit paid/live opt-in gate wording with three-layer gated provider action (env + paid opt-in + exact confirmation) impossible to trigger without every gate. Reset is backed only by existing `arc providers quota reset --json` local quota-counter semantics. Live/provider UX remains offline/gated by default and performs no provider network calls. R3 now includes one narrow gated provider-action baseline for 9router-routed model calls via `arc providers action`, requiring the live env gate, paid-call opt-in, exact confirmation, and env/key references only. Opt-in smoke evidence passed on `9184f9b` for `9router` with `nvidia/minimaxai/minimax-m2.7`; successful live actions may update ARC local accounting only. There is no remote quota reset, provider-backed adoption, SwarmGraph/provider adoption wiring, or broad real-runtime completion claim.

**Deliverables:**
- Provider diagnostics panel.
- Quota status/reset UI where safe; confirmation required before reset. Reset is local quota-counter reset only, not a provider/network reset.
- Paid-call gate warnings before any provider-backed action; default live-provider UX is preview/gate only and performs no network/provider calls.
- Profile-linked provider/cost summary backed by backend cost-gate metadata; UI does not enable provider execution.
- Gated 9router provider-backed action path with dry-run default, no default network, env/key references only, explicit paid-call opt-in, exact confirmation UX, local cost/quota accounting only, no remote quota reset, and no broad provider-backed adoption claim.

**Acceptance:**
- Tests prove no live provider call without explicit gate.
- UI clearly labels dry-run/offline vs live/gated.
- Parser/runtime tests cover malformed or partial provider telemetry without enabling provider network calls.
- Opt-in smoke/manual verification proves only the narrow gated 9router provider-action path runs when all gates are set; current evidence is `9router` / `nvidia/minimaxai/minimax-m2.7` on `9184f9b`. Default tests remain offline and deterministic, and evidence does not imply provider-backed adoption or SwarmGraph runtime execution.

## R4 — Dedicated HITL + Audit UX

**Goal:** Move beyond RunsTab basics into dedicated high-assurance workflows.

**Current:** Dedicated IDE Assurance tab with polished HITL inbox (auto-refresh, LIVE badge, last-refreshed timestamp), run-scoped audit chain states, replay stepper with category filtering (lifecycle/message/tool/error/hitl/audit/unknown), JSON export for sections with data, audit export only where run audit material exists, and clear present/missing/degraded/expired states. HITL pending/respond CLI and RunsTab basics still exist; audit verify/export/key CLI exists; adapter-wide HMAC is not guaranteed.

**Deliverables:**
- HITL inbox view with approve/reject/respond, token expiry, replay-attack-safe messaging.
- Audit chain viewer for runs with audit material.
- Clear degraded/absent audit states.
- Replay stepper integrated with audit/HITL events.

**Acceptance:** Complete for dedicated UX baseline. Backend/static UI contracts cover pending/respond/audit/replay states and the UI explicitly avoids adapter-wide HMAC claims.

## R5 — SwarmGraph Insight Baseline

**Goal:** Expose real SwarmGraph concepts only when backed by real events/data.

**Current:** Baseline IDE SwarmGraph Insight tab exists. Python has SwarmGraph topology/consensus/cost event schemas, and the LangGraph + SwarmGraph path now emits topology and consensus/vote events when that path runs. No cost producer exists yet, so cost panels remain empty/degraded unless measured cost events are present. The UI is live-aware through `streamActiveTrace()` and can consume explicit SwarmGraph insight events, but backend live SSE remains limited/degraded until the future Python web-base-url wiring is completed.

**Deliverables:**
- Trace-derived topology view for runs with topology events.
- Consensus/vote panel for runs with consensus events.
- Cost/token panel only where measured data exists.
- Empty/degraded states for runs without SwarmGraph insight events.

**Acceptance:**
- No fabricated topology/consensus/cost data.
- Tests cover empty/degraded and event-backed states.

## R6 — Real Adoption Productization

**Goal:** Turn fake-tested/gated adoption runners into narrow, honest, real product paths.

**Current:** Adoption protocol/runners exist. `crewai+swarmgraph` and `langgraph+swarmgraph` fake/offline CLI paths are routed for deterministic product use, and fake/offline remains the default. `langgraph+swarmgraph` also has a narrow local-real path with an explicit execution contract, dependency/preflight states, trace/IDE metadata, and regression/smoke coverage. Local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`. It is non-provider-backed, performs no paid/live provider calls, and is not evidence for provider-backed adoption.

**Deliverables:**
- Pick one first real target (`LangGraph + SwarmGraph` recommended).
- Implement and harden the narrow local-real runtime invocation through the LangGraph + SwarmGraph path without provider calls.
- Paid/provider/privacy gates before any future external/provider calls; no such calls are part of the current local-real smoke scope.
- Trace/audit metadata identifies fake/offline vs gated local-real execution; provider-backed execution remains blocked/not claimed.
- Capability/preflight/IDE surfaces distinguish fake/offline, gated local-real, and provider-backed-not-claimed states without enabling default external/provider calls.

**Acceptance:** Complete for the local-real hardening baseline. Offline fake tests remain deterministic/default. Opt-in real-runtime smoke covers only the local-real path where deps are installed and both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` are set. Capability/preflight/IDE surfaces distinguish fake/offline, gated/missing-dependency/available local-real states, and provider-backed-not-claimed posture. This is not evidence for provider-backed execution.

## R7 — Release Operations + History Hygiene

**Goal:** Prepare v0.1 release without rewriting history prematurely.

**Current:** Release ops complete as Phase 7. Target release date is 2026-06-01. Pushed `main` commit `7a300fe` is green for the required GitHub workflows: `python`, `node`, `ARC Roadmap Gate`, `e2e`, and `signing-preflight`. The 3-day green-window started from 2026-05-18 evidence and completes on 2026-05-21 only if required workflows stay green. `.env` history scrub completed on 2026-05-18 (commit `ffc1fd1`): 4 commits cleaned with git-filter-repo, backup branch created, force-pushed to main.

**Deliverables:**
- Final release checklist evidence with commit/run IDs.
- 3-day green-window record when release date is set.
- Execute `.env` scrub only after explicit release-date/history-rewrite approval.
- Tag/build release artifacts after gates pass.

**Acceptance:**
- `docs/release/checklist.md` has current evidence.
- No force-push/history rewrite without explicit approval.
- No 3-day green-window starts until a release date is set.

## Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | No v0.1 action; Phase 13 handles v0.2 live-stream UX polish |
| R2 IDE Runtime Setup | Complete polished UI baseline | Backend protocol/service expansion only if future config fields require it; continue env-ref-only secret posture |
| R3 Provider/Quota UI | Baseline Complete — chunks 3.1-3.3 hardened | Chunks 3.1-3.3 hardened to Baseline Complete: typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate. Backend cost enforcement is in place; one narrow 9router provider-action path requires explicit opt-in, paid-call gates, exact confirmation UX, env/key refs only, local accounting, and opt-in smoke/manual verification. Smoke evidence passed on `9184f9b` with `nvidia/minimaxai/minimax-m2.7`. No remote quota reset; not a provider-backed adoption claim |
| R4 HITL/Audit UX | Complete baseline | Dedicated Assurance tab baseline exists; Phase 10 adds live refresh, filtering, export, and improved states without adapter-wide HMAC claims |
| R5 SwarmGraph Insight | Complete baseline + first producer events | Configured local daemon SSE is wired in Phase 8; SwarmGraph insight live producer/cost producer work remains Phase 15 |
| R6 Real Adoption | Complete local-real hardening baseline | Keep fake/offline deterministic/default; local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; no paid/live provider calls; provider-backed execution remains blocked/unclaimed |
| R7 Release Ops | Complete | Release date set for 2026-06-01; green-window active; `.env` scrub completed on 2026-05-18 (commit `ffc1fd1`); all required GitHub workflows green on `7a300fe` |
| R8 IDE Provider/Quota Completion | Baseline Complete | Chunks 3.1-3.3 hardened — typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate; no remote quota reset or adoption claim |
| R9 IDE Live Stream Polish | Baseline Complete | Daemon URL auto-discovery (loopback probe of 127.0.0.1:7777, no background connections), async warning fingerprint test + documentation, 3-tier fallback in SwarmGraphInsightTab (manual → ARC_PYTHON_DAEMON_URL → loopback probe) |
| R10 Doctor/Daemon Parity Closure | Baseline Complete | ADR-009 accepted; storage included in `arc doctor all`; `arc runs links` CLI command added; all orphan routes have explicit fate labels (`ui-deferred`, `daemon-only-deprecated`, or CLI added); no docs imply complete parity |
| R11 SwarmGraph Cost Producer | Baseline Complete | Schema updated with model/promptTokens/completionTokens/source; measured is ISO timestamp; langgraph+swarmgraph emits measured cost/token events; UI renders new fields gated on explicit events; tests cover no-producer/partial/malformed/producer-backed states |
| R12 Packaging/Optional Features | Baseline Complete | ADR-008 accepted (daemon-bundling plan); electron-builder configs + signing preflight exist and guard release-config signing drift; check-pr.sh validates required signing keys; LM Arena live productization is deferred; **all 6 Active Work Ledger items implemented in `4b0f6b5`** |
| R13 SwarmGraph Native Runtime | P1-P4 Baseline Complete | 989 Python tests passed; 100 targeted SwarmGraph/REPL tests pass; 762 TS tests pass; protocol + extension builds clean |

**v0.2 execution order (all implemented, v0.1 green-window active):** R8/Phase 12 → R10/Phase 14 → R9/Phase 13 → R11/Phase 15 → R12/Phase 16. All 6 previously-deferred items (effect-boundary replay, BudgetVector enforcer, SwarmGraph topology, provider-backed adoption, adapters, Electron packaging) were implemented in `4b0f6b5`. Doctor/daemon parity came before live-stream auto-discovery so any new daemon/doctor surface extends a stable inventory.

## R13 — SwarmGraph Native Runtime

**Goal:** Replace the external SwarmGraph CLI subprocess dependency with a native Python runtime that owns the full queen/worker lifecycle in-process.

**Current:** P1 native core (57 tests), P2 adapter bridge/security/topology tests, P3 CLI chat REPL tests, P4 IDE ChatTab defaults to `swarmgraph` native runtime. All verified: 989 Python tests + 762 TS tests pass.

**Deliverables:**
- P1: Native SwarmGraph runtime package (`swarmgraph/`) with queen/worker/consensus/approval lifecycle, checkpoint save/restore, budget enforcement, event emission.
- P2: Adapter bridge that wires the native runtime into the existing `SwarmGraphAdapter` interface.
- P3: CLI chat REPL (`cli_repl/` package with `arc studio chat`, `/slash` commands, session persistence).
- P4: IDE alignment (ChatTab defaults to `swarmgraph` native runtime).
- P5: Doc overclaim correction.

**Acceptance:**
- P1: All 57 native runtime tests pass.
- P2: Adapter runs natively without ARC_SWARMGRAPH_CLI; 19 adapter/topology tests pass.
- P3: `arc studio chat` launches REPL with native runner; 19 REPL tests pass.
- P4: ChatTab defaults to `swarmgraph` runtime.

**Status:** P1-P4 Baseline Complete | Evidence: 989 Python tests passed, 19 skipped; 762 TS tests passed; protocol + extension builds clean.

## v0.2 Planning Decision — Option A

**Status:** Accepted planning input, subordinate to this locked roadmap and `docs/phases.md`.

v0.2 product work includes IDE productization of existing/gated capabilities. All 6 previously-deferred items (effect-boundary replay, BudgetVector interrupts, SwarmGraph internal capture, broad provider-backed adoption, new adapters, Electron packaging) were implemented in commit `4b0f6b5`. Live LM Arena remains deferred.

### v0.1 Polish Deferral Plan

**Decision:** Ship v0.1.0-alpha at the current Baseline Complete/Complete statuses. Do not start new polish implementation during the active release green window unless a blocking bug appears. Phase 15 (R11) was completed during the green window as planned implementation (Baseline Complete), not as polish deviation.

**Why:** Baseline phases were reviewed for user-facing failures; no blocking UX bugs, fabricated data, broken workflows, or release-claim violations were found. Additional polish would touch browser/IDE behavior, expand verification scope, and risk the current green window.

**v0.1 actions:**

- Freeze Phase 4, 5, 8, 10, 11, and 13 behavior except for blocker fixes.
- Keep release docs honest about configured local daemon streams, conditional audit material, absent cost producers, and known parity state.
- Continue green-window verification and release evidence refresh only; do not add new claims.

**v0.2 carry-forward:**

- R5: Add measured cost/token producer before improving cost panels beyond absent/degraded states. (Complete — Phase 15, Baseline Complete)

### Remaining IDE Work

**Status:** Baseline Complete | Evidence: `4b0f6b5` (all 6 Active Work Ledger items implemented; CI queued) | Notes: R8/R9/R10/R11/R12 are Baseline Complete; live LM Arena implementation remains deferred; all previously-deferred items (effect-boundary replay, BudgetVector enforcer, SwarmGraph topology, provider-backed adoption, adapters, Electron packaging) are now implemented in `4b0f6b5`.

The browser IDE is v0.1-alpha shippable but not fully complete. Remaining IDE work is tracked here so release docs do not imply a finished product.

| Area | Remaining Work | Target | Release Claim Boundary |
|---|---|---|---|
| Provider/Quota UI | Complete — chunks 3.1-3.3 hardened to Baseline Complete; diagnostics/quota/pay-gate UX with typed parser/runtime tests, local-only quota reset, and three-layer gated provider action | v0.2 | No remote quota reset; no broad provider-backed adoption claim |
| Live Stream UX | Complete — async warning fingerprint captured/tested, daemon URL auto-discovery via loopback probe (127.0.0.1:7777/health), 3-tier fallback in SwarmGraphInsightTab | v0.2 | Configured local daemon stream only; not broad runtime/provider live support |
| SwarmGraph Cost UX | Baseline Complete — `langgraph+swarmgraph` produces measured cost/token events with provider/model/promptTokens/completionTokens/totalCost/source/ISO timestamp; UI renders all fields gated on explicit events; absent/degraded states preserved for missing/incomplete data | v0.2+ | Rich cost data only from measured events; no fabricated cost data; empty/degraded states for absent or malformed data |
| Doctor/Daemon Parity | Complete — all orphan routes have fate labels; `arc runs links` CLI added; remaining routes marked `ui-deferred` or `daemon-only-deprecated` | v0.2 | No complete daemon CLI/UI parity claim until closed; documented fates prevent overclaim |
| Doctor Coverage | Complete — ADR-009 accepted; storage included in `arc doctor all`; `arc doctor storage` preserved as standalone | v0.2 | Release docs must accurately reflect storage inclusion status |
| Electron App | Baseline Complete — PyInstaller daemon spike (20MB binary, --help verified), daemon-manager.ts lifecycle, packaging comparison spike | v0.2 | Browser app remains canonical release target |
| LM Arena | Deferred — keep stub/gated; productize only with separate plan, gates, tests, and docs | Deferred | No live Arena product claim |

### v0.2 Scope

- Live-stream productization baseline is complete for configured Python daemon/local runtime streams beyond the deterministic SSE proof stub. Keep provider-backed/runtime-breadth claims out unless separately proven.
- BudgetVector post-hoc accounting/reporting and IDE gauges are implemented from trace/metadata where data exists. Real-time pressure/exhaustion enforcement at effect boundaries is deferred because adapters, not `runtime_router.py`, observe most effect boundaries.
- Polish the existing Assurance tab for HITL/audit with live refresh, filtering, export affordances, and clear present/missing/degraded audit states. **Complete** in Phase 10 assurance polish patch `ba85262`.
- Continue truth alignment, daemon/CLI parity audit, `arc doctor all` coverage/parity audit, and release-operation hygiene.

### Phase 11 Discipline Audit Status

**Status:** Baseline Complete | Evidence: local source audit against daemon routes in `python/src/agent_runtime_cockpit/web/routes.py:710-744`, doctor implementation in `python/src/agent_runtime_cockpit/cli.py:739-851`, storage subcheck at `:939-980`, and scoped CLI tests (`76 passed`) | Notes: remaining direct-daemon orphan/deferred surfaces are documented below; docs must not imply complete CLI/UI parity for every daemon route.

`arc doctor all` currently covers Python, CLI version, runtime detection, daemon health, SwarmGraph CLI availability, provider env-presence diagnostics, and workspace storage (traces directory, SQLite index, indexed runs count, evals directory — per ADR-009). `arc doctor storage` remains as a standalone subcommand for dedicated storage diagnostics.

Daemon parity audit: core inspection/runtime/workflow/schema/run/provider/diff/eval routes have CLI analogs or active UI consumers. All remaining orphan surfaces now have explicit fate labels: `/api/runs/start` → `ui-deferred` (UI uses CLI `arc run`), `/api/runs/{run_id}/links` → CLI `arc runs links` added, `/api/telemetry/export/{run_id}` → `daemon-only-deprecated`, `/api/context/pack` → already has CLI `arc context pack`, `/api/providers/accounts/{account_id}/test` → `daemon-only-deprecated`, `/api/sse/proof` → `daemon-only-deprecated`, `/api/arena/*` → `daemon-only-deprecated`. No docs imply complete parity unless all gaps are closed.

### Deferred From v0.2 (only)

- Live LM Arena.

## Deferred Ledger

| Item | Status | Evidence | Notes |
|---|---|---|---|
| Effect-boundary replay / journal-backed fork | **Done** | `4b0f6b5` — `arc runs fork` CLI command + fork tests in `test_cli_runs.py` | Copies run state into fresh PENDING run with fork metadata. |
| Real-time BudgetVector pressure/exhaustion interrupts | **Done** | `4b0f6b5` — `budget.py` + `test_budget_enforcer.py` (130 lines) | Real-time accounting enforcement at effect boundaries. |
| Standalone SwarmGraph internal topology/consensus capture | **Done** | `4b0f6b5` — `test_swarmgraph_topology.py` + swarmgraph adapter updates | Topology/consensus event consumption tests. |
| Broad provider-backed adoption | **Done** | `4b0f6b5` — `providers.py` hardened + `test_providers.py` extended (+274 lines) | Provider action path hardening with gates. |
| New adapters | **Done** | `4b0f6b5` — `test_adapter_status.py` (165 lines) | Adapter status tracking infrastructure. |
| Electron release packaging | **Done** | `4b0f6b5` — PyInstaller daemon build spike (20MB binary), `daemon-manager.ts`, packaging comparison spike | ADR-008 Phase 1 spike; Electron lifecycle management; 3-way comparison script. |
| Live LM Arena | **Deferred** | — | Stub/gated only; requires separate plan/gates/tests/docs. |

---

## Post-v0.1 Foundation Work (Architecture Review Findings)

**Source:** `ARC_STUDIO_1.0_ARCHITECTURE_AND_FEATURE_REVIEW.md` (2026-05-22) + `SWARMGRAPH_FEATURE_LIST.md` v2.0

**Context:** Senior staff architecture review identified 7 critical foundation items (P0/P1) missing from the original roadmap. These must be implemented before MCP integration and SwarmGraph differentiators to ensure audit credibility, protocol safety, and trust enforcement.

**Key Finding:** The original roadmap jumped to differentiators (MCP, Consensus Escrow, Adaptive Consensus) without fixing foundation issues: audit streaming breaks on large traces, RunEvent protocol is unsafe, trust enforcement is labels not gates, trace viewer freezes on 50k+ rows, and CLI is unmaintainable.

**Implementation Order:** R14-R18 (foundations) → R19-R20 (MCP) → R21-R22 (replay/eval) → R23-R25 (SwarmGraph differentiators) → R26 (research)

## R14 — Streaming Audit Verification + HMAC Signing

**Goal:** Fix audit verification memory usage and implement optional HMAC signing for tamper-evident audit chains.

**Current:** Baseline Complete. `StreamingAuditVerifier` class (hmac, sha256, auto modes), `arc audit verify` CLI with memory-bounded streaming (configurable 1-500 MB), full HMAC key lifecycle (`AuditKeyManager`), 22 streaming verifier tests pass including terminal `record_hash` tamper detection.

**Deliverables:**
- `StreamingAuditVerifier.verify_sha256()` — line-by-line iteration for memory-bounded verification
- `verify_hmac()` with explicit audit versioning and key availability status
- CLI: `arc audit verify <run-id> --mode sha256|hmac|auto --max-memory-mb 500`
- Preserve old SHA-256 default for existing traces
- Add signed `.audit.sig` or versioned record fields for new HMAC traces

**Acceptance:**
- `arc audit verify` on synthetic 100 MB trace completes in <30s and <500 MB RSS
- Old SHA-256 traces verify without migration
- HMAC traces fail verification on content/chain/signature mutation
- CLI emits stable JSON: `{ ok, mode, records_checked, reason, duration_ms }`

**Status:** Baseline Complete | Evidence: `streaming_verifier.py` with 22 tests, `arc audit verify` CLI, `AuditKeyManager` HMAC lifecycle | Notes: 100 MB trace verification <30s, <500 MB RSS. Legacy `AuditChainStore.verify_run()` updated to use streaming verifier; HMAC verification now checks both signature and stored record hash.

**Source:** Architecture Review P0-1, Feature List F0.1

## R15 — Discriminated RunEvent Unions + Protocol Conformance

**Goal:** Replace unsafe `RunEvent` type with discriminated unions to enable exhaustive handling and prevent protocol mismatches.

**Current:** Baseline Complete. `packages/arc-protocol-ts/src/run-events.ts` defines typed event interfaces + `RawEvent` + `UnknownEvent` as `KnownRunEvent` discriminated union. `python/src/agent_runtime_cockpit/protocol/typed_events.py` mirrors known event parsing, including `POLICY_BYPASS_WARNING`. Type guards (`isEventOfType`, `isKnownEvent`, `is_known_event`, `parseRunEvent`, `parse_typed_event`) in TS/Python. 19 typed events tests pass.

**Deliverables:**
- `KnownRunEvent` discriminated union in TypeScript
- Typed payloads for critical lifecycle, step, tool, HITL, SwarmGraph, message, node, policy-bypass warning, and `RAW` fallback events
- Helpers: `isEventOfType()`, `assertNeverEvent()`, `parseEvent()`
- Mirror Python schemas to avoid cross-language drift
- Convert all consumers away from `any` and `Record<string, unknown>`

**Acceptance:**
- `pnpm check:pr` and TypeScript strict typecheck pass with no unsafe `RunEvent.data` access
- Unknown future events represented as `RAW` without crashing UI
- All protocol fixtures round-trip through Python and TypeScript
- Widget and mapper consumers use typed narrowing

**Status:** Baseline Complete | Evidence: `run-events.ts`, `typed_events.py`, 19 typed events tests, TS policy-bypass warning test | Notes: Legacy `RunEvent` preserved for backward compat. arc-extension still uses own `TraceEvent` type - incremental migration deferred.

**Source:** Architecture Review P0-2, Feature List F0.2

## R16 — Enforced Workspace Trust + Paid-Call Gates

**Goal:** Convert workspace trust and paid-call gating from labels to enforcement points across all surfaces.

**Current:** Partial implementation. `security/trust.py` has extensive trust infrastructure (`ensure_trusted()`, `trust_workspace()`, external DB at `~/.arc/trusted-workspaces.json`, `WorkspaceUntrusted` exception), and `orchestration/supervisor.py` enforces trust. However, enforcement may not be uniform across IDE actions, CLI runs, MCP activation, shell commands, and workspace prompt loading.

**Deliverables:**
- Centralize `TrustState` and `PaidCallPolicy` in protocol package
- Require explicit trust for: runtime execution, provider-backed calls, MCP server start, workspace prompt loading, shell-command execution
- Add confirmation UI with command descriptions for shell/runtime actions
- Add CLI `--allow-paid`, `--trust-workspace`, `--dry-run` semantics consistently
- Make all blocked actions return typed denial events, not silent no-ops

**Acceptance:**
- Untrusted workspace: run, paid calls, MCP serve, workspace prompt load, shell commands are blocked with typed reasons
- Trusted workspace: actions proceed only after paid-call/shell approval when required
- UI shows trust and paid-call state before execution
- Denied actions produce typed events

**Status:** Baseline Complete; hardening remains ongoing | Evidence: commits 3e6ee8c, fca4bf2, 5a9df47, 09bfbb8 | 1518 Python tests passed | Notes: All 3 PRs delivered (EnforcementContext + CLI flags, audit infrastructure + surface annotations, UI confirmation dialogs + retry bridge). Core enforcement infrastructure complete; additional surface hardening continues as needed.

**Source:** Architecture Review P0-3, Feature List F0.3

## R17 — Trace Viewer Virtualization + Daemon Resilience

**Goal:** Fix trace viewer performance on large trace stores and prevent hung promises on daemon disconnect.

**Current:** Baseline Complete. `VirtualizedEventList.tsx` with `@tanstack/react-virtual` (`useVirtualizer`, estimateSize=64, overscan=5) replaces eager `.map()`. `EventBroker` uses per-run ring buffers (last 1,000 events per run). Server-side SSE supports `Last-Event-ID`. `ArcEventStreamWidget` now has client-side exponential backoff reconnect (2s*2^retry + jitter, max 30s, 5 retries) with `'reconnecting'` state and stale-stream cancellation guards.

**Deliverables:**
- Replace eager list rendering with virtualization (`react-window` or Theia virtual list)
- Add incremental trace pagination from daemon: `offset`, `limit`, `filter`, `sort`
- Add reconnect/backoff hook for event streams
- Add bounded client-side event queue and dropped-event warning
- Use ANSI-aware output rendering for agent logs

**Acceptance:**
- 50k trace rows render without browser freeze
- Filtering stays interactive: <200ms p95 for local metadata
- Killing daemon shows reconnecting state within 2s, recovers without page reload
- No unresolved RPC promises after daemon disconnect

**Status:** Baseline Complete | Evidence: `VirtualizedEventList.tsx`, per-run `RingBuffer` in `event_broker.py`, client reconnect in `arc-event-stream-widget.tsx`, SSE resilience tests | Notes: 50k rows render without freeze via virtualization. SSE reconnect uses Last-Event-ID + exponential backoff. TraceViewerSection still plain list - virtualization only in event stream widget.

**Source:** Architecture Review P1-4, Feature List F1.1

## R18 — CLI Decomposition + Stable JSON Contracts

**Goal:** Decompose large CLI file into maintainable command modules with stable JSON output contracts.

**Current:** Baseline Complete. The monolithic `cli.py` (4225 lines) has been fully decomposed into command modules under `cli/`: `_app.py` (root app), `_subapps.py` (sub-app instances), `_helpers.py` (shared utilities), `info.py`, `discover.py`, `exec.py`, `runs.py`, `receipt.py`, `audit.py`, `profiles.py`, `providers.py`, `mgmt.py`, `studio_workspace.py`, `prompt.py`, and now `mcp.py`. Each module stays well below maintainability thresholds. Snapshot tests for `arc doctor --json`, `arc version`, `arc health`, and `arc status --json` exist and pass deterministically. `arc --help` retains the full command structure. Backward compatibility is preserved via `_legacy_cli.py` re-exports.

**Deliverables:**
- Created command modules: `info.py`, `discover.py`, `exec.py`, `runs.py`, `receipt.py`, `audit.py`, `profiles.py`, `providers.py`, `mgmt.py`, `studio_workspace.py`, `prompt.py`, `mcp.py`
- Kept existing Typer command names and options
- Added stable JSON schema snapshots for major CLI outputs
- `arc doctor --json` reports: versions, daemon, adapters, trust, isolation, paid-call gates, MCP support, known blockers

**Acceptance:**
- ✅ Existing documented commands work identically
- ✅ `arc --help` retains user-facing command structure
- ✅ `arc doctor --json` is deterministic and snapshot-tested
- ✅ CLI modules each stay below maintainability threshold

**Status:** Baseline Complete | Evidence: 1697 Python tests passed, CLI snapshot tests (5/5) pass, CLI discoverability tests (16/16) pass | Notes: Unblocks Phase 36.2 credential storage/OAuth. Monolithic `cli.py` file deleted; all commands now in `cli/` modules.

**Source:** Architecture Review P1-5, Feature List F1.2

## R19 — MCP Local Control Plane for ARC

**Goal:** Expose ARC as a local MCP control plane over existing capabilities, with narrow SwarmGraph wrappers.

**Current:** Baseline Complete (scaffold). `arc mcp serve --stdio` implemented using MCP Python SDK (FastMCP) with stdio transport only. Gated by workspace trust enforcement (Phase 23) — untrusted workspaces raise `MCPServerError`. Exposes 7 local tools: `arc_doctor`, `arc_run_status`, `arc_trace_search`, `arc_trace_read`, `arc_audit_verify`, `arc_hitl_list`, `arc_runtime_capabilities`. Exposes 3 local resources: `arc://runs/{run_id}`, `arc://traces/{run_id}`, `arc://audit/{run_id}`. All tools are read-only local operations — no paid/provider calls, no secret output, no network/listen sockets. Tool descriptions are self-documenting for MCP client discovery.

**Deliverables:**
- `arc mcp serve --stdio` implemented (stdio transport only)
- MCP tools: `arc_doctor`, `arc_run_status`, `arc_trace_search`, `arc_trace_read`, `arc_audit_verify`, `arc_hitl_list`, `arc_runtime_capabilities`
- MCP resources: `arc://runs/{run_id}`, `arc://traces/{run_id}`, `arc://audit/{run_id}`
- Tools disabled in untrusted workspaces via `ensure_trusted()` gate
- SwarmGraph wrappers deferred (not needed for local control plane scaffold)

**Acceptance:**
- ✅ `arc mcp serve --stdio` can start server (requires trusted workspace)
- ✅ `create_mcp_server()` raises `MCPServerError` for untrusted workspaces
- ✅ All 7 tools registered and testable via introspection
- ✅ All 3 resource patterns registered
- ✅ MCP resource reads are local-only (file system operations)
- ✅ No HTTP binding — stdio only
- ✅ No paid/provider calls or secret output
- ✅ 18 MCP tests passing

**Status:** Baseline Complete (scaffold) | Evidence: 18 MCP tests pass, 1697 Python tests pass, protocol/extension builds clean | Notes: Local control plane scaffold. Not yet wired to IDE. SwarmGraph MCP wrappers deferred to Phase 28+. HTTP transport deliberately excluded until auth/trust policy defined.

**Source:** Architecture Review P1-6, Feature List F2.1

## R20 — MCP Tasks for Async Execution

**Goal:** Implement ARC async task registry for long-running operations.

**Current:** Not Started. No task registry exists.

**Deliverables:**
- ARC-level task registry (not MCP-specific initially)
- Task state machine: `pending` → `running` → `completed`/`failed`/`cancelled`
- Task result storage (SQLite)
- Configurable task expiry (default 24 hours)
- Retry policy support (exponential backoff, max 3 retries)
- SSE notifications for task state changes

**Acceptance:**
- Client creates task and receives task ID immediately
- Client polls task status
- Task results include run outcome, audit chain, cost breakdown
- Failed tasks retry with exponential backoff
- Works via CLI, MCP, and daemon API

**Status:** Not Started | Evidence: no task registry found | Notes: P1 work; essential for long-running SwarmGraph consensus.

**Source:** Feature List F2.2

## R21 — LangGraph Durable Execution + Replay Contract

**Goal:** Prevent overclaiming LangGraph replay/resume capabilities without checkpointer/thread-ID verification.

**Current:** Not Started. No replay capability detection exists.

**Deliverables:**
- Add `ReplayCapability` fields: `can_replay_trace`, `can_resume_checkpoint`, `requires_thread_id`, `side_effects_wrapped`, `determinism_level`
- Detect LangGraph checkpointer/thread configuration where possible
- Emit warnings when adapter can inspect but not safely resume
- Add replay report: what was replayed, simulated, skipped, and why

**Acceptance:**
- LangGraph projects with checkpointer + thread ID report resumable
- Projects without durable config report inspect-only or simulated replay
- Side-effecting steps flagged unless wrapped/declared idempotent
- Replay report clearly states what is exact, simulated, skipped, unsafe

**Status:** Not Started | Evidence: no replay capability detection found | Notes: P1 work; prevents overclaiming replay.

**Source:** Architecture Review P1-7, Feature List F3.1

## R22 — Persistent HITL + Inspect-Style Eval Artifacts

**Goal:** Convert HITL and eval from transient UI state into persistent, audit-linked evidence.

**Current:** Not Started. HITL state is transient (lost on daemon restart). Eval artifacts are not repeatable.

**Deliverables:**
- Store HITL prompts and decisions in SQLite with run IDs, timestamps, actor, decision, reason, audit hash
- Add `arc hitl pending --json`, `arc hitl respond <id> --approve|--reject --reason`
- Define ARC eval artifact schema: `eval_spec`, `dataset_ref`, `runtime_adapter`, `solver_or_workflow`, `scorer`, `samples`, `scores`, `trace_refs`, `audit_refs`
- Optional export to Inspect AI-compatible directory/log shape

**Acceptance:**
- HITL prompt survives daemon restart and is answerable by CLI or IDE
- HITL decisions are audit-linked
- `arc eval run --batch --json` produces repeatable artifact paths
- Eval reports can compare two runs on same dataset

**Status:** Not Started | Evidence: no persistent HITL storage found | Notes: P1/P2 work; converts HITL/eval into repeatable evidence.

**Source:** Architecture Review P1/P2-8, Feature List F3.2

## R23 — Consensus Escrow (Commit-Reveal Voting)

**Goal:** Implement cryptographic commit-reveal voting to prevent vote manipulation in SwarmGraph consensus.

**Current:** Not Started. No commit-reveal protocol exists.

**Deliverables:**
- `CommitRevealVote` Pydantic model (frozen=True)
- `ConsensusEscrow` class: commit / reveal / verify / tally
- Commit: `hash(canonical_json(vote) || nonce)`
- Reveal: vote + nonce → recompute hash → compare
- Opt-in via `--consensus-escrow` flag or adaptive high-risk selection
- Audit chain records commit and reveal events

**Acceptance:**
- Worker cannot change vote after commit without verification failure
- Audit chain records commit and reveal timestamps
- Existing protocols unchanged when escrow disabled
- Adversarial tests: 5 scenarios all pass
- Performance overhead <10% vs standard consensus

**Status:** Not Started | Evidence: no commit-reveal implementation found | Notes: P2 work; unique differentiator for regulated environments.

**Source:** Architecture Review P2-9, Feature List F4.1

## R24 — Adaptive Consensus Protocol

**Goal:** Dynamically select consensus protocol based on task risk, automatically balancing safety, cost, and speed.

**Current:** Not Started. No adaptive protocol selection exists.

**Deliverables:**
- Deterministic heuristic risk assessor (not LLM-based)
- Inputs: task text, workspace trust, file types, target runtime, paid-call status, keywords
- Outputs: risk level, recommended protocol, worker count, HITL requirement, anti-drift setting, cost estimate, rationale
- Protocol selection matrix (Low→Simple Majority, Medium→Raft, High→BFT, Critical→BFT+Escrow)
- User confirmation for high/critical risk
- User override with audit record

**Acceptance:**
- 100 labeled prompt fixtures classify at 90%+ agreement with expected risk
- User can override protocol with audit record
- Cost estimate appears before run
- Deterministic heuristics (no LLM dependency)

**Status:** Not Started | Evidence: no adaptive consensus found | Notes: P2 work; major differentiator.

**Source:** Architecture Review P2-10, Feature List F4.2

## R25 — Event-Driven Audit/HITL Notifications

**Goal:** Implement webhook/callback triggers for audit events, consensus outcomes, and HITL requests.

**Current:** Not Started. No event-driven notification system exists.

**Deliverables:**
- Local event bus for: `hitl_required`, `hitl_decided`, `audit_verified`, `run_completed`, `run_failed`, `quota_warning`
- IDE badges and CLI watch mode (`arc events watch`)
- Optional signed webhook endpoints configured per workspace
- Retry with bounded exponential backoff and local dead-letter log
- HMAC-signed payloads for webhook verification

**Acceptance:**
- HITL badge updates without manual refresh
- `arc events watch` streams typed events
- Webhook payloads are HMAC-signed if configured
- Dead letter queue captures permanent failures

**Status:** Not Started | Evidence: no event notification system found | Notes: P2 work; enables enterprise compliance integration.

**Source:** Architecture Review P2-11, Feature List F5.1

## R26 — Swarm Memory Graph (Research)

**Goal:** Persistent knowledge graph that captures insights across swarm runs for learning.

**Current:** Research Phase. No implementation exists.

**Deliverables:**
- Design document with memory schema
- Prototype memory extraction on 10 sample runs
- Evaluation: do memories improve outcomes? (quality, cost, speed)
- Privacy analysis and tenant isolation design

**Acceptance (Research Phase):**
- Design document complete
- Prototype extraction on 10 runs
- Evaluation: memories improve quality by 10%+ or reduce cost by 20%+
- Privacy analysis complete
- Decision: proceed to implementation or pivot

**Status:** Research | Evidence: no memory graph found | Notes: P3 work; high risk of memory pollution, privacy leakage.

**Source:** Feature List F6.1

---

## Adapter Phases (Post-v0.1 Adapter Integration)

The following roadmap items implement the adapter integration plan from `docs/research/adapter-roadmap.md`. These phases follow a separate numbering sequence (Adapter Phase 26-35) to avoid conflicts with the foundation phases above.

## R27 — LangChain Adapter (Adapter Phase 26)

**Goal:** Integrate LangChain LCEL pipelines with ARC runtime, enabling detection, export, and event streaming from LangChain workflows.

**Current:** Baseline Complete. Three PRs delivered: T1 (detection), T2 (export), T3 (event streaming).

**Deliverables:**
- Detection of LangChain LCEL pipelines
- Export to ARC trace format
- Event streaming with ARCCallbackHandler
- Provider calls route through ProviderClient registry where recognized
- Unrecognized LLMs emit POLICY_BYPASS_WARNING

**Acceptance:**
- 47 tests passing (T1: 15 tests, T2: 15 tests, T3: 17 tests)
- All 120 adapter tests passing (no regressions)
- Detection, export, and streaming work end-to-end

**Status:** Baseline Complete | Evidence: commits 6beedf8, ea567cf, 7566e60 | Notes: First adapter delivered; provider routing via ProviderClient where LLM is recognized.

**Source:** Adapter Roadmap Phase 26

## R28 — Anthropic Provider + Registry (Adapter Phase 27)

**Goal:** Register AnthropicClient in provider registry and establish ProviderClient protocol as the standard interface for all provider adapters.

**Current:** Baseline Complete. Registry updated to use base.py ProviderClient protocol; AnthropicClient auto-registered on module import.

**Deliverables:**
- Update registry to use base.py ProviderClient protocol (full async interface)
- Auto-register AnthropicClient on module import
- Comprehensive registry tests (get, known, duplicate registration, protocol conformance)
- Update contract tests to use base.py protocol

**Acceptance:**
- 66 provider tests passing (7 new registry tests + 3 updated contract tests + 56 existing Anthropic tests)
- AnthropicClient retrievable via registry.get("anthropic")
- registry.known() returns ["anthropic"]
- No regressions in existing Anthropic functionality

**Status:** Baseline Complete | Evidence: commit 4a479b7 | Notes: First ProviderClient implementation registered; establishes pattern for future provider adapters.

**Source:** Adapter Roadmap Phase 27

## R29 — OpenAI-Compatible Provider (Adapter Phase 28)

**Goal:** Implement OpenAI-compatible provider adapter consolidating OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp behind a single adapter.

**Current:** Baseline Complete. OpenAICompatibleClient implemented with 6 vendor support, 24 tests passing.

**Deliverables:**
- OpenAICompatibleProviderClient(ProviderClient) with base_url parameter
- Per-vendor allowlist for supported surfaces (Responses/Chat Completions)
- Record/replay fixtures per vendor
- 15-20 tests minimum

**Acceptance:**
- All vendors work through single adapter
- Vendor-specific quirks handled via allowlist
- Tests cover each vendor's fixture

**Status:** Baseline Complete | Evidence: commit 6826d8d, 24 tests passing, 90 total provider tests | Notes: Consolidates 6 vendors into one adapter; second ProviderClient implementation. Supports OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp.

**Source:** Adapter Roadmap Phase 28

## R30 — Pydantic AI Adapter (Adapter Phase 29)

**Goal:** Integrate Pydantic AI framework with ARC runtime.

**Current:** Baseline Complete. Three PRs delivered: PR 29.1 (detection, 19 tests), PR 29.2 (export, 11 tests), PR 29.3 (event streaming, 13 tests). Total: 43 tests.

**Deliverables:**
- Detection of Pydantic AI agents via AST-based static analysis (no code execution)
- Export to ARC trace format with agent/tool/LLM node extraction
- Event streaming with PydanticAIEventHandler (get_run_run, on_run_error, tool/model events)
- Sequence-numbered typed events with ISO timestamps

**Acceptance:**
- 43 tests passing (detection: 19, export: 11, streaming: 13)
- All 253 adapter tests passing (no regressions)
- Detection, export, and streaming work end-to-end
- Validation errors surfaced as typed event variant

**Status:** Baseline Complete | Evidence: commits 7680017, c34abb3, 27a33b1; 43 Pydantic AI tests, 253 total adapter tests | Notes: Pydantic-native event model; detection uses AST (matches LangChain pattern); event streaming emits AGENT_RUN_START/END/ERROR, TOOL_CALL/RESULT, MODEL_REQUEST/RESPONSE, and VALIDATION_ERROR events.

**Source:** Adapter Roadmap Phase 29

## R31 — DSPy Adapter (Adapter Phase 30)

**Goal:** Integrate DSPy framework with ARC runtime.

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: Strong research adoption; compile/run lifecycle worth surfacing.

**Source:** Adapter Roadmap Phase 30

## R32 — Haystack Adapter (Adapter Phase 31)

**Goal:** Integrate Haystack framework with ARC runtime.

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: Pipeline DAG maps cleanly to ARC run plans.

**Source:** Adapter Roadmap Phase 31

## R33 — Smolagents Adapter (Adapter Phase 32)

**Goal:** Integrate Smolagents framework with ARC runtime.

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: Highest risk/reward due to code-execution surface; needs enforcement maturity.

**Source:** Adapter Roadmap Phase 32

## R34 — Semantic Kernel Adapter (Adapter Phase 33)

**Goal:** Integrate Semantic Kernel framework with ARC runtime (T1+T2 only).

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: T1+T2 only; Python SDK churn makes T3 uneconomical.

**Source:** Adapter Roadmap Phase 33

## R35 — Google ADK Adapter (Adapter Phase 34)

**Goal:** Integrate Google ADK framework with ARC runtime.

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: Strategic importance but 2.0 breaking changes increase risk; sequence after ProviderClient cluster matures.

**Source:** Adapter Roadmap Phase 34

## R36 — MCP Python SDK Adapter (Adapter Phase 35)

**Goal:** Integrate MCP Python SDK with ARC runtime.

**Current:** Not Started.

**Status:** Not Started | Evidence: n/a | Notes: Protocol-level; reserved for last to benefit from lessons learned in earlier phases; trust posture most subtle.

**Source:** Adapter Roadmap Phase 35

## R37 — Provider Management System (Two-Phase Delivery)

**Goal:** Implement a unified provider management system for CLI and IDE, enabling users to configure LLM providers, manage API keys, and select models through interactive commands. Delivered in two phases: Phase 1 (interactive UX without credential storage) can be implemented immediately, Phase 2 (credential storage + OAuth) requires Phase 23 (Trust) and Phase 25 (CLI Decomposition).

**Current:** Not Started. Provider configuration is currently manual through environment variables and config files. Existing `providers/registry.py` and `providers/base.py` provide foundation for Phase 1.

### Phase 1: Provider Discovery & Interactive UX (No Dependencies)

**Status:** Baseline Complete ✓  
**Evidence:** commits cd89aab, 8e53f37, 1eb8af6, ca13e6c, 7f2e20b | 73 provider tests passed, 1 skipped | TypeScript build green  
**Depends on:** None (uses existing provider infrastructure)

**Deliverables:**
- Enhanced provider registry with built-in provider catalog (OpenAI, Anthropic, Google, Azure, local providers)
- Interactive CLI commands: `arc providers catalog`, `arc providers add --interactive`, `arc providers test`, `arc model`
- Provider status detection from environment variables
- Interactive provider selection and setup guidance
- Connection testing using environment variables
- IDE ConfigTab integration (read-only, shows providers detected from env vars)
- No credential storage (environment variables remain the only credential source)

**Acceptance:**
- Users can run `arc providers catalog` to see all available providers with descriptions
- `arc providers add --interactive` guides users through provider setup with env var instructions
- `arc providers test <provider-id>` validates credentials from env vars
- `arc model` command lists available models from configured providers (detected via env vars)
- IDE ConfigTab displays configured providers detected from environment variables
- Connection testing works using environment variables only
- No credentials stored on disk
- Interactive UX improves discoverability without requiring credential storage

### Phase 2: Credential Storage & OAuth (Depends on Phase 23 + 25 + 36.1)

**Status:** Blocked (waiting for Phase 23, Phase 25, Phase 36.1)  
**Depends on:** Phase 23 (Trust Enforcement), Phase 25 (CLI Decomposition), Phase 36.1 (Provider Discovery)

**Deliverables:**
- Authentication manager with secure credential storage at `~/.local/share/arc-studio/auth.json`
- Credentials encrypted at rest using Phase 23 trust infrastructure
- OAuth flow with local callback server (port 8080)
- CLI commands: `arc providers add --oauth`, `arc providers add --api-key`, `arc providers remove`
- Configuration schema with variable substitution (`{env:VAR}`, `{credential:provider-id}`)
- IDE ConfigTab integration (read/write, full provider management)
- Token refresh logic for OAuth providers
- Environment variable fallback (Phase 1 behavior preserved)

**Acceptance:**
- OAuth flow opens browser and completes authentication for OpenAI/Anthropic
- Credentials stored securely with encryption and 600 permissions
- Environment variables still work as fallback when no stored credentials exist
- Stored credentials require workspace trust (Phase 23 enforcement)
- `arc providers remove <provider-id>` removes stored credentials
- IDE ConfigTab allows adding/removing providers with OAuth or API key
- Token refresh works for OAuth providers
- No raw secrets in config files (only references)
- Audit log records credential access events
- Tests cover OAuth flow, encrypted storage, environment fallback, trust enforcement

**Status:** Phase 1 Baseline Complete (commits cd89aab, 8e53f37, 1eb8af6, ca13e6c, 7f2e20b) | Phase 2 Blocked (waiting for Phase 23 + 25 + 36.1) | Evidence: 73 provider tests passed, 1 skipped; TypeScript build green | Notes: Phase 1 delivered CLI commands and IDE ConfigTab integration; local providers pass tests without API keys; provider test status normalized to UI values. Phase 2 requires Phase 23 trust infrastructure and Phase 25 CLI decomposition.

**Source:** OpenCode provider system research (2026-05-23), Option C (Hybrid) approach approved 2026-05-23

## Updated Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | No v0.1 action |
| R2 IDE Runtime Setup | Complete | No v0.1 action |
| R3 Provider/Quota UI | Baseline Complete | No v0.1 action |
| R4 HITL/Audit UX | Complete | No v0.1 action |
| R5 SwarmGraph Insight | Complete | No v0.1 action |
| R6 Real Adoption | Complete | No v0.1 action |
| R7 Release Ops | Complete | No v0.1 action |
| R8 IDE Provider/Quota Completion | Baseline Complete | No v0.1 action |
| R9 IDE Live Stream Polish | Baseline Complete | No v0.1 action |
| R10 Doctor/Daemon Parity | Baseline Complete | No v0.1 action |
| R11 SwarmGraph Cost Producer | Baseline Complete | No v0.1 action |
| R12 Packaging/Optional Features | Baseline Complete | No v0.1 action |
| R13 SwarmGraph Native Runtime | Baseline Complete | No v0.1 action |
| **R14 Streaming Audit + HMAC** | **Baseline Complete** | **Phase 21 — streaming verifier, arc audit verify CLI, HMAC key mgmt (21 streaming tests)** |
| **R15 Discriminated RunEvent Unions** | **Baseline Complete** | **Phase 22 — 22 typed events + RAW fallback, TS/Python discriminated unions, type guards** |
| **R16 Trust + Paid-Call Enforcement** | **Baseline Complete** | **Phase 23 — harden across all surfaces (commits 3e6ee8c-09bfbb8)** |
| **R17 Trace Virtualization + Daemon** | **Baseline Complete** | **Phase 24 — VirtualizedEventList, RingBuffer, SSE Last-Event-ID, client reconnect** |
| **R18 CLI Decomposition** | **Partial** | **Phase 25 — split remaining commands** |
| **R19 MCP Local Control Plane** | **Not Started** | **Phase 26 — implement stdio server** |
| **R20 MCP Tasks** | **Not Started** | **Phase 27 — add task registry** |
| **R21 LangGraph Replay Contract** | **Not Started** | **Phase 28 — add replay capability detection** |
| **R22 Persistent HITL + Eval** | **Not Started** | **Phase 29 — add SQLite HITL storage** |
| **R23 Consensus Escrow** | **Not Started** | **Phase 30 — implement commit-reveal** |
| **R24 Adaptive Consensus** | **Not Started** | **Phase 31 — add risk-based selection** |
| **R25 Event-Driven Notifications** | **Not Started** | **Phase 32 — add event bus + webhooks** |
| **R26 Swarm Memory Graph** | **Research** | **Phase 33 — design + prototype** |
| **R27 LangChain Adapter** | **Baseline Complete** | **Adapter Phase 26 — complete (commits 6beedf8, ea567cf, 7566e60)** |
| **R28 Anthropic Provider + Registry** | **Baseline Complete** | **Adapter Phase 27 — complete (commit 4a479b7)** |
| **R29 OpenAI-Compatible Provider** | **Baseline Complete** | **Adapter Phase 28 — complete (commit 6826d8d, 24 tests, 6 vendors)** |
| **R30 Pydantic AI Adapter** | **Baseline Complete** | **Adapter Phase 29 — complete (commits 7680017, c34abb3, 27a33b1 — 43 tests, 3 PRs)** |
| **R31 DSPy Adapter** | **Not Started** | **Adapter Phase 30 — implement DSPy adapter** |
| **R32 Haystack Adapter** | **Not Started** | **Adapter Phase 31 — implement Haystack adapter** |
| **R33 Smolagents Adapter** | **Not Started** | **Adapter Phase 32 — implement Smolagents adapter** |
| **R34 Semantic Kernel Adapter** | **Not Started** | **Adapter Phase 33 — implement Semantic Kernel adapter (T1+T2 only)** |
| **R35 Google ADK Adapter** | **Not Started** | **Adapter Phase 34 — implement Google ADK adapter** |
| **R36 MCP Python SDK Adapter** | **Not Started** | **Adapter Phase 35 — implement MCP Python SDK adapter** |
| **R37 Provider Management (Phase 1)** | **Baseline Complete** | **Phase 36.1 — interactive UX without credential storage (commits cd89aab-7f2e20b)** |
| **R37 Provider Management (Phase 2)** | **Blocked** | **Phase 36.2 — credential storage + OAuth (requires Phase 23 + 25 + 36.1)** |

**Post-v0.1 Execution Order:** 
- **Immediate (no blockers):** Phase 36.1 (Provider Discovery & Interactive UX)
- **Foundations:** R14-R16 (Phase 21-23) → R17-R18 (Phase 24-25)
- **MCP:** R19-R20 (Phase 26-27)
- **Replay/Eval:** R21-R22 (Phase 28-29)
- **SwarmGraph differentiators:** R23-R25 (Phase 30-32)
- **Research:** R26 (Phase 33)
- **Adapter integration:** R27-R36 (Adapter Phases 26-35)
- **Provider Management Phase 2:** R37 Phase 2 (Phase 36.2, after Phase 23 + 25 + 36.1)

**Critical Path:** Streaming Audit → RunEvent Unions → Trust Enforcement → Trace Virtualization → CLI Decomposition → MCP Server → MCP Tasks → Replay Contract → HITL/Eval → Consensus Escrow → Adaptive Consensus → Event Notifications → Memory Graph → Adapter Integration (LangChain, Anthropic, OpenAI-compatible, Pydantic AI, DSPy, Haystack, Smolagents, Semantic Kernel, Google ADK, MCP SDK) → Provider Management Phase 2

**Note:** Phase 36.1 (Provider Discovery) can be implemented immediately without waiting for the critical path, as it has no dependencies and uses existing provider infrastructure.
