# ARC Studio — Locked Phase Implementation Plan

**Status:** Locked execution plan for remaining work.  
**Created:** 2026-05-17  
**Last reality refresh:** 2026-05-19 against locked roadmap and release evidence.  
**Current evidence anchor:** `83673e8` | refreshed 2026-05-19 | docs-only updates after this anchor must not widen release claims.  
**Update rule:** Update this file in the same commit whenever a phase/chunk changes status. Do not create new roadmap/implementation/status markdowns.

## Execution Preference

Prefer larger coherent implementation chunks over tiny slices. A chunk may include multiple listed slices when they share files/tests and can be completed safely in one session. Keep the no-destructive-actions, no-secret-commits, preserve-unrelated-work, and green-verification rules.

## Verification Baseline For Every Slice

Minimum:
```bash
cd python && uv run pytest -q
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
bash scripts/check-pr.sh
```

If browser/IDE touched:
```bash
pnpm --filter @arc-studio/browser build
pnpm --filter @arc-studio/e2e-tests test
```

If release docs touched:
```bash
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/LOCKED_REMAINING_ROADMAP.md docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md docs/REALITY_AUDIT.md docs/RELEASE_CHECKLIST.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md
```

Before commit:
```bash
git status --short
```

## Acceptance Ledger Format

Every new phase/chunk should include:

- `Status: <Not Started | In Progress | Baseline Complete | Polished Complete | Blocked | Deferred>`.
- `Evidence: <commit SHA, CI run ID, test count, or local command result>`.
- `Acceptance:` numbered, testable conditions.
- `Verification:` exact commands required for that phase.
- `Known risks:` residual risk even after acceptance.

## Phase 1 — Active Live Streaming

**Roadmap:** R1  
**Status:** Complete — Phase 1 vertical baseline implemented

### Design Note — Current Launch/Event Flow
- IDE launch path today is ChatTab/runtime selectors → Theia backend CLI bridge → Python `arc run`/related commands. The Theia service contract now exposes `streamActiveTrace()` for live/replay event consumption.
- Python live infrastructure exists in `EventBroker.stream_live()`/`sse_handler()` (in-memory same-process only) and supervisor event emission, while `/api/runs/{id}/events` supports explicit live/replay SSE modes for an existing run id.
- `/api/sse/proof` is a deterministic stub live SSE endpoint. It emits `RUN_STARTED`, step data, terminal `RUN_COMPLETED`, then `STREAM_END`; it proves streaming transport semantics but is not a provider-backed runtime stream.
- Product semantics target: active stream = connected to an in-flight run via broker/supervisor; replay = finite stored trace read; disconnected = stream lost before a terminal run event or `STREAM_END`.

### Chunk 1.1 — Trace Current Run Launch/Event Flow
- Status: Complete.
- Map IDE launch path: ChatTab → backend service → Python CLI/daemon.
- Map Python event path: JobSupervisor/EventBroker/trace store.
- Add design note inside this plan, not a new doc.
- No code unless gaps are obvious and small.

### Chunk 1.2 — Backend Active Stream Contract
- Status: Complete.
- Add/confirm Python endpoint/CLI path for active run event subscription.
- Define terminal behavior: completed/failed/cancelled/disconnected.
- Tests: web/unit event lifecycle.

### Chunk 1.3 — Theia Stream Proxy
- Status: Complete.
- Add backend service method for active stream connection.
- Ensure env filtering, cancellation safety, timeout handling.
- Tests: backend/proxy contract.

### Chunk 1.4 — UI Live State
- Status: Complete.
- Event Stream/Run Timeline show live/replay/disconnected states.
- No fake live labels for replay.
- Tests: static contract + e2e if possible.

### Chunk 1.5 — Stub SSE Proof E2E
- Status: Complete for deterministic SSE proof stub only.
- Stub run emits deterministic events through `/api/sse/proof`.
- E2E verifies live `RUN_STARTED` + terminal event without reading stored replay.
- Real IDE-to-daemon live frame coverage is in Phase 8.1.

## Phase 2 — IDE Runtime Setup + Config

**Roadmap:** R2  
**Status:** Complete polished UI baseline — ConfigTab safe runtime/profile/isolation baseline, YAML-backed safe fields summary, persisted profile selection copy, remediation wizard, and dedicated export-target helper UI implemented

### Chunk 2.1 — Config Backend Methods
- Expose read/write/dry-run config methods needed by UI.
- Tests verify no raw secret persistence.
- Status: Complete baseline — backend service already exposes safe config read/write, profile list, isolation status/provider list, provider catalog, and env-var provider key references.

### Chunk 2.2 — Adapter Readiness Actions
- UI displays missing deps/env/profile actions from capability reports.
- Tests for gated/unavailable/runnable states.
- Status: Complete baseline — ConfigTab displays capability-driven runtime states plus a Runtime Setup Wizard that derives missing env names, detected artifacts, safe doctor actions, and manual remediation guidance from capability reports. Static/helper tests cover gated/unavailable/runnable states and secret redaction/copy guards.

### Chunk 2.3 — Profile + Isolation UI
- Show current profile, workspace trust, isolation provider.
- Allow safe profile selection/update.
- Status: Complete polished UI baseline — ConfigTab loads backend profile inventory and isolation providers/status, displays trust/isolation, and includes persisted-profile selection copy backed by existing safe config/profile flows. No raw secrets are stored.

### Chunk 2.4 — Export Target Helpers
- UI for CrewAI/OpenAI/LlamaIndex export target references.
- Store references only; do not store provider secrets.
- Status: Complete polished UI baseline — ConfigTab exports a copy-safe config snapshot, stores provider env-var references only, and provides dedicated helper UI for CrewAI, OpenAI Agents, and LlamaIndex export targets. No provider secrets are persisted.

## Phase 3 — Provider/Quota/Cost UI

**Roadmap:** R3  
**Status:** Active narrow real-provider action baseline — provider diagnostics/quota scaffold exists with typed parsing/tests, targeted confirmation before local quota-counter reset, profile-linked cost policy summary, backend cost-gate enforcement, and explicit paid/live opt-in gates. Reset remains local quota-counter reset only; default UX is offline/gated and performs no provider network calls. R3 now includes one narrow gated provider action baseline for 9router-routed model calls via `arc providers action`, requiring live env gate, paid-call opt-in, exact confirmation, and env/key references only. Opt-in smoke evidence passed on `9184f9b` for `9router` with `nvidia/minimaxai/minimax-m2.7`; successful live actions may update ARC local accounting only. There is no remote quota reset, provider-backed adoption, SwarmGraph/provider adoption wiring, or broad real-runtime completion claim.

### Chunk 3.1 — Provider Diagnostics Panel
- Surface existing CLI/provider diagnostics.
- Status: Baseline Complete — hardened telemetry parsing with typed parser/runtime tests; tests cover dry-run/no-live default and malformed/partial/success states; all provider diagnostics render empty/partial/malformed/success states safely.
- Tests for dry-run/no-live default and malformed/partial provider telemetry.

### Chunk 3.2 — Quota + Profile Summary
- Display quota status and profile-linked cost policy.
- Reset only where existing CLI supports safe reset.
- Status: Baseline Complete — quota visibility scaffold with targeted confirmation before reset; reset copy explicitly local-only and cannot imply remote/provider reset; profile-linked cost policy summary displays enforcement level correctly. Reset may call only existing `arc providers quota reset --json` semantics and is a local quota-counter reset, not a provider/network reset. Profile-linked cost policy summary is backed by backend opt-in cost-gate metadata; no provider execution is enabled by the UI.

### Chunk 3.3 — Paid-Call Gate UX
- Add explicit warnings/confirmations before provider-backed paths.
- Tests prove no live call without explicit opt-in.
- Status: Baseline Complete — three-layer gate (env + paid opt-in + exact confirmation) enforced both UI (advisory) and backend (hard); `providerCall: false` across all 8 gate combinations in typed tests; UI remains preview/offline and never enables provider execution. Current live-provider UX is preview/gate only unless every explicit gate is supplied; hardened UI copy/actions distinguish dry-run/offline, local quota reset, backend cost-gate enforcement, and the narrow 9router provider-action baseline. This proves only one gated action path, not provider-backed adoption or broad real-runtime support.

### Chunk 3.4 — Real Provider Execution Contract
- Define the narrow real provider-backed action contract before implementation.
- Preserve dry-run default, explicit `allowPaidCalls`/provider-live gates, env/keychain references only, no raw secret persistence/display, and no broad provider-backed adoption claim.
- Status: Complete baseline — contract stays narrow: one explicit 9router provider-backed action path, dry-run default, no default network, explicit paid/provider gates, env/key refs only, no raw secrets, local accounting only, no remote quota reset, and no broad adoption claim.

### Chunk 3.5 — Gated Backend Provider Action Path
- Implement a backend action path that can make a provider-backed request only when all explicit gates pass.
- Keep default/test paths offline and deterministic; return clear blocked/gated errors when any gate is missing.
- Status: Complete baseline — backend `runGatedProviderAction()`/`arc providers action` path is available only behind all gates. Default dry-run/offline behavior remains authoritative; missing gates return blocked/gated results instead of making provider/network calls.

### Chunk 3.6 — UI Confirmation + Accounting
- Add UI confirmation flow for the gated provider-backed action with model/provider/cost warning, dry-run/offline labeling, and paid-call confirmation.
- Integrate local cost/quota accounting metadata for successful gated actions. Local quota reset remains ARC local counters only, not provider remote quota.
- Status: Complete baseline — UI remains preview/dry-run by default and requires explicit live/paid/confirmation inputs before the narrow provider action. It displays env/key refs only, keeps quota reset copy local-only, and records only ARC local accounting metadata.

### Chunk 3.7 — Opt-In Smoke + Manual Verification
- Add an opt-in smoke/manual verification path for real provider-backed behavior with required env/keychain setup and paid-call gates.
- Keep CI offline by default and avoid real provider calls in normal tests.
- Status: Complete for narrow smoke evidence — opt-in smoke/manual verification is narrow and passed on `9184f9b` with `9router` / `nvidia/minimaxai/minimax-m2.7`, `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`, `--live`, `--allow-paid-calls`, and exact `RUN_PROVIDER_ACTION:<provider>:<model>` confirmation. Evidence proves only the gated provider action path; it does not prove provider-backed adoption, SwarmGraph runtime execution, or broad real-runtime completion.

## Phase 4 — HITL + Audit Dedicated UX

**Roadmap:** R4  
**Status:** Complete dedicated UX baseline

### Chunk 4.1 — HITL Inbox View
- Dedicated pending prompt list.
- Approve/reject/respond with expiry/single-use token status.
- Status: Complete — dedicated Assurance tab implements pending inbox and token/expiry-aware actions.

### Chunk 4.2 — Audit Chain Viewer
- Show present/missing/degraded audit material.
- Verify/export actions for runs with audit chain.
- Status: Complete for verify/view baseline — run-scoped audit viewer shows present/missing/degraded states without adapter-wide keyed audit claims. Export affordance remains CLI-only polish.

### Chunk 4.3 — Replay Stepper
- Step through events with HITL/audit annotations.
- No deterministic replay claim beyond supported trace replay.
- Status: Complete — replay stepper annotates HITL/audit/approval/replay events from stored trace replay only.

## Phase 5 — SwarmGraph Insight Baseline

**Roadmap:** R5  
**Status:** Complete baseline + first producer-backed topology/consensus events

### Chunk 5.1 — Event Contract Inventory
- Identify current trace/adoption events that can support topology/consensus/cost.
- Add missing event types only if producer exists or tests define empty state.
- Status: Complete — Python SwarmGraph topology/consensus/cost event schemas exist. LangGraph + SwarmGraph emits topology and consensus/vote events; no fabricated cost producer exists.

### Chunk 5.2 — Empty-State Panels
- Add topology/consensus/cost panels that honestly show “no event-backed data”.
- Status: Complete — SwarmGraph Insight tab includes trace selector plus empty/degraded topology, consensus, and cost panels, and is live-aware through `streamActiveTrace()`.

### Chunk 5.3 — Event-Backed Rendering
- Render topology/votes/cost only from real trace events.
- Status: Complete baseline — pure extractors render only explicit SwarmGraph topology/consensus/cost trace events; fake/offline metadata is ignored. LangGraph + SwarmGraph can now supply topology and consensus/vote events, while cost remains absent unless a measured cost event is produced. Backend live SSE is still not complete beyond the existing degraded/disconnected behavior.

## Phase 6 — Narrow Real Adoption Path

**Roadmap:** R6  
**Status:** Complete local-real hardening baseline — `langgraph+swarmgraph` fake/offline CLI route remains the default. The narrow local-real path has an explicit execution contract, dependency/preflight states, trace/IDE metadata, and regression/smoke coverage. Local-real availability still requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`, and no provider calls are made or claimed.

### Chunk 6.1 — Select First Real Target
- Default recommendation: `langgraph+swarmgraph`.
- Confirm dependencies and no paid calls.
- Status: Complete — first target selected as `langgraph+swarmgraph`; current product path is fake/offline deterministic only.

### Chunk 6.2 — Real Runner Spike
- Implement narrow real invocation path.
- Preserve fake/offline tests.
- Status: Partial — `langgraph+swarmgraph` keeps deterministic fake/offline routing as the default. A narrow local-real runner path exists only behind dual explicit `ARC_REAL_RUNTIME_SMOKE=1` plus `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` gates across router/capability/preflight/runner surfaces, is not provider-backed, performs no paid/live provider calls, and is not claimed as product-ready.

### Chunk 6.3 — Capability + Smoke
- Capability reports distinguish fake-tested/gated/real.
- Opt-in real-runtime smoke covers installed deps.
- Status: Partial — capability/smoke posture distinguishes fake/offline routed baseline from the gated local-real path. Capability reports now require both `ARC_REAL_RUNTIME_SMOKE=1` plus `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` before marking local-real available. Opt-in real-runtime smoke with both gates is the only real-path validation scope; provider-backed execution remains gated/not claimed.

### Chunk 6.4 — Local-Real Execution Contract
- Define supported inputs, outputs, trace events, failure modes, and dependency boundaries for the non-provider-backed `langgraph+swarmgraph` local-real path.
- Preserve fake/offline as the default and require both `ARC_REAL_RUNTIME_SMOKE=1` plus `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` for local-real availability.
- Status: Complete — contract is scoped to local LangGraph + SwarmGraph execution only, with supported input/output boundaries, trace events, failure modes, dependency limits, fake/offline default behavior, dual-gate availability, and no provider-call behavior.

### Chunk 6.5 — Dependency + Preflight Hardening
- Harden installed-dependency checks and preflight errors for LangGraph/SwarmGraph local-real execution.
- Capability/preflight output must distinguish fake/offline available, local-real gated/missing-deps/available, and provider-backed-not-claimed states.
- Status: Complete — capability and preflight output distinguish fake/offline availability, local-real gated/missing-dependency/available states, and provider-backed-not-claimed posture. Defaults remain offline and do not make external/provider/network calls.

### Chunk 6.6 — Trace Metadata + IDE Surfacing
- Ensure trace/audit metadata clearly identifies fake/offline vs gated local-real execution.
- Contract: `runtime.mode` must identify `fake-offline` versus `local-real-gated` for `langgraph+swarmgraph` traces where this path is used.
- Surface local-real availability in CLI/IDE capability views without claiming provider-backed adoption or readiness.
- Status: Complete — trace/metadata and CLI/IDE capability surfaces identify fake/offline versus gated local-real execution, preserve provider-backed-not-claimed copy, and have metadata/copy-guard coverage.

### Chunk 6.7 — Deterministic Regression + Opt-In Smoke
- Keep fake/offline regression tests deterministic and default in CI.
- Add/maintain opt-in local-real smoke/manual verification requiring both gates and installed deps.
- Status: Complete — fake/offline regression coverage remains deterministic/default. Opt-in local-real smoke/manual verification requires both gates plus installed deps and proves only the local-real path, not provider-backed execution.

## Phase 7 — Release Operations

**Roadmap:** R7  
**Status:** Complete — 7.1 evidence refreshed; 7.2 green-window active from 2026-05-18 evidence with current pushed-main anchor `83673e8`; 7.3 `.env` history scrub completed on 2026-05-18

### Chunk 7.1 — Release Evidence Refresh
- Update release checklist with latest commit/run IDs.
- Do not overclaim deferred features.
- Status: Complete — evidence refreshed for pushed `main` commit `83673e8`. Latest GitHub `main` evidence is green for python, node, ARC Roadmap Gate, e2e, and signing-preflight. Banned-claims verification remains the docs-touch check for this phase.

### Chunk 7.2 — Green Window
- Start only after release date is set.
- Track GitHub green runs for required workflows.
- Status: Active — release date is set for 2026-06-01. The 3-day green-window starts from 2026-05-18 green evidence and current pushed-main anchor `83673e8`; it completes on 2026-05-21 only if required workflows stay green.

### Chunk 7.3 — `.env` History Scrub
- Execute only after explicit approval for release date + history rewrite + force-push plan.
- Status: Complete — `.env` history scrub executed on 2026-05-18. Used `git filter-repo --path-glob '*.env' --invert-paths --force` to remove 4 commits containing .env files. Backup branch `backup-pre-scrub-2026-05-18` created before scrub. Force-pushed to main at commit `a7f21f9`. All .env files removed from git history.

## Phase Status Table

### Plan Phase ↔ Roadmap ID

| Plan Phase | Roadmap ID | Scope |
|---|---|---|---|
| Phase 12 | R8 | IDE Provider/Quota Completion |
| Phase 14 | R10 | Doctor/Daemon Parity Closure |
| Phase 13 | R9 | IDE Live Stream Polish |
| Phase 15 | R11 | SwarmGraph Cost Producer + Cost UX |
| Phase 16 | R12 | Packaging/Optional Feature Decisions (In Progress) |

| Phase | Status | Depends On | Notes |
|---|---|---|---|
| 1 Active Live Streaming | Complete | current CLI/IDE run basics | Full vertical baseline: Python SSE, Theia proxy contract, UI live/replay/disconnected states, stub e2e |
| 2 Runtime Setup UI | Complete polished UI baseline | config/profile CLI | Safe ConfigTab baseline plus YAML-backed safe fields summary, persisted profile copy, remediation wizard, and dedicated export-target env-ref helpers in place |
| 3 Provider/Quota UI | Baseline Complete — chunks 3.1-3.3 hardened | provider CLI + explicit paid/provider gates | Typed parser/tests, confirmed local quota-counter reset affordance, profile-linked cost summary, backend cost-gate enforcement, hardened paid/live opt-in gates; offline/gated by default with no provider network calls; one narrow 9router provider action exists behind live env gate, paid opt-in, exact confirmation, env/key refs only, and ARC local accounting only; opt-in smoke passed on `9184f9b` with `nvidia/minimaxai/minimax-m2.7`; no remote quota reset or provider-backed adoption claim |
| 4 HITL/Audit UX | Complete baseline | existing CLI/RunsTab basics | Dedicated Assurance tab; avoids adapter-wide HMAC claim |
| 5 SwarmGraph Insight | Complete baseline + first producer events | event-backed adoption data | LangGraph + SwarmGraph topology/consensus events; no fabricated cost; configured local daemon SSE is wired in Phase 8 while SwarmGraph insight live producer/cost producer work remains Phase 15 |
| 6 Real Adoption | Complete local-real hardening baseline | adoption protocol + dual explicit local-real gates | `langgraph+swarmgraph` fake/offline CLI baseline remains default; narrow local-real path has contract, dependency/preflight states, metadata/IDE surfacing, and smoke/regression coverage; both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` are required for local-real availability; no provider calls are made or claimed |
| 7 Release Ops | Complete | green CI | 7.1 evidence refreshed for current pushed-main anchor `83673e8` with green `python`, `node`, `ARC Roadmap Gate`, `e2e`, and `signing-preflight`; 7.2 green-window active from 2026-05-18 toward 2026-06-01 release date; 7.3 `.env` history scrub completed on 2026-05-18 with git-filter-repo, 4 commits cleaned, backup branch created, force-pushed to main |
| 8 Live Stream Productization | Baseline Complete | configured Python daemon/local stream | Configured local daemon/stub runtime live streams work; remaining IDE polish is Phase 13 |
| 8.1 IDE-to-Daemon E2E Harness | Complete | Phase 8 | Deterministic offline browser e2e proves one IDE-to-local-daemon SSE live frame path |
| 9 BudgetVector Post-Hoc Accounting | Complete | trace/metadata budget data | Post-hoc accounting/reporting implemented; real-time budget interrupts deferred |
| 10 Assurance Polish | Baseline Complete | Assurance tab baseline | Live refresh, filtering, export affordances, improved states implemented; no v0.1 polish blocker |
| 11 Discipline Audits | Baseline Complete | daemon routes + CLI doctor | Orphan/deferred daemon surfaces documented; storage doctor remains separate from `arc doctor all` |
| 12 Provider/Quota UX Completion | Baseline Complete | Phase 3 provider CLI + explicit gates | Chunks 3.1-3.3 hardened to Baseline Complete; diagnostics/quota/pay-gate UX with typed parser/runtime tests, local-only quota reset, and gated provider action impossible without every explicit gate; no remote quota reset or adoption claim |
| 14 Doctor/Daemon Parity Closure | Baseline Complete | Phase 11 | ADR-009 accepted; storage included in `arc doctor all`; `arc runs links` CLI command added (3 new tests); all orphan routes have explicit fate labels; no docs imply complete parity |
| 13 Live Stream UX Polish | Baseline Complete | Phase 8 + 8.1 + Phase 14 decisions | Daemon URL auto-discovery (loopback probe), async warning fingerprint test + doc, 3-tier fallback in SwarmGraphInsightTab |
| 15 SwarmGraph Cost Producer + Cost UX | Baseline Complete | Phase 5 + Phase 9 | Schema expanded with model/promptTokens/completionTokens/source; measured is ISO timestamp; UI renders all new fields gated on explicit events; 17 new tests across Python+TS |
| 16 Packaging/Optional Feature Decisions | In Progress | browser v0.1 stabilization | ADR-008 accepted; electron-builder + signing preflight exist; LM Arena stub/gated and banned-claims enforced; implementation deferred to post-v0.1 |

## v0.1 Polish Deferral Decision

**Date:** 2026-05-19  
**Status:** All Baseline Complete phases ship at current status for v0.1.

**Analysis:** Each Baseline Complete phase (4, 5, 8, 10, 11, 13) was evaluated for user-facing polish gaps. Findings:

- **Phase 4** (HITL/Audit UX): AssuranceTab at 460 lines with auto-refresh, category filtering, present/missing/degraded/expired states — closest to Polished Complete among baseline phases.
- **Phase 5** (SwarmGraph Insight): SwarmGraphInsightTab at 399 lines with live/replay/disconnected states, 3 insight panels — cost panel is placeholder but honestly degraded.
- **Phase 8** (Live Stream): Theia async contribution warnings and daemon URL polish now addressed by Phase 13.
- **Phase 10** (Assurance Polish): Polish already applied in `ba85262`. No remaining polish needed.
- **Phase 11** (Discipline Audits): Orphan daemon routes now addressed by Phase 14.
- **Phase 13** (Live Stream UX Polish): Baseline Complete — async warning fingerprint captured/tested, daemon URL auto-discovery via loopback probe, 3-tier fallback. No remaining polish needed.

**Rationale:** Polish introduces CI risk, requires browser build (slow), changes UI behavior during the active green window. No user-facing bugs exist at any baseline phase. Project is stable at release-candidate quality.

**v0.2 scope for deferred polish:**
- Phase 14: Orphan daemon routes CLI commands (now addressed)
- Phase 15: SwarmGraph Cost Producer + Cost UX

## v0.2 Option A — Productization Plan

**Roadmap:** v0.2 planning decision in `docs/LOCKED_REMAINING_ROADMAP.md`  
**Status:** Not Started; execute after v0.1 release unless a blocking bug requires a smaller v0.1 patch.  
**Scope:** Existing-capability IDE productization. Effect-boundary replay/fork and real-time adapter-wide budget interrupts are deferred.

### Remaining IDE Execution Order

Execute these in order after v0.1 release, unless a blocking bug requires a smaller v0.1 patch. Each phase must preserve offline/default gates, avoid broad provider-backed claims, and keep absent/degraded states honest where producers are missing.

1. Phase 12 — Provider/Quota UX Completion
2. Phase 14 — Doctor/Daemon Parity Closure
3. Phase 13 — Live Stream UX Polish
4. Phase 15 — SwarmGraph Cost Producer + Cost UX (Baseline Complete)
5. Phase 16 — Packaging/Optional Feature Decisions

Order rationale: close parity/doctor decisions before live-stream auto-discovery so any new daemon/doctor surface extends a stable inventory.

### Phase 8 — Live Stream Productization

- Status: Baseline Complete — configured Python daemon/local live stream wiring is implemented for IDE `streamActiveTrace()` via explicit/requested base URL or `ARC_PYTHON_DAEMON_URL`, with local live terminal/degraded handling and replay-not-live UI copy/tests. Evidence: local Phase 8 worktree verification on `bec8d4b` (`python` web SSE tests, arc-extension tests/build, browser build/e2e, `scripts/check-pr.sh`), distinct from pushed-main workflow evidence. This proves configured local daemon/stub runtime event streams only, not broad runtime/provider-backed live event support.
- **v0.1 decision:** Ship at current status. Remaining polish (Theia async contribution warnings, daemon URL auto-discovery) was addressed by Phase 13. No user-facing bugs exist at baseline.
- Wire Theia live mode to configured Python daemon/local runtime stream beyond deterministic `/api/sse/proof`.
- Preserve live/replay/disconnected distinctions; do not label replay as live.
- Add/refresh tests proving configured local stream behavior without provider calls.
- Acceptance:
  1. Local daemon stream can be opened from IDE for an in-flight or stub/local-runtime run.
  2. Stream reaches a terminal state or explicit disconnected/degraded state.
  3. UI never labels replay-only data as live.
- Verification: Python web/event tests, arc-extension build/tests, browser/e2e if UI behavior changes.
- Known risks: configured daemon URL drift, local-runtime dependency shape, and temptation to treat SSE proof stub as broad live runtime evidence.

### Phase 8.1 — IDE-to-Daemon E2E Harness

- Status: Complete — IDE-to-daemon SSE e2e harness implemented and verified.
- Goal: Add one narrow browser e2e harness path proving Theia UI can render a live frame from a real local Python daemon SSE socket, not only backend/protocol/static coverage.
- Implementation:
  1. Existing daemon-sse-fixture.cjs serves deterministic live events at `/api/runs/{id}/events?mode=live` without provider calls.
  2. Enhanced existing test "SwarmGraph Insight renders configured daemon live frame or degraded state" to prove IDE-to-daemon SSE live frame path.
  3. Test verifies: live state transitions (connecting → live → ended), incremental event rendering (RUN_STARTED → RUN_COMPLETED), and live vs replay labeling.
  4. Existing `/api/sse/proof` assertions remain labeled limited-local only.
- Acceptance:
  1. ✅ Browser e2e proves one IDE-to-local-daemon SSE live frame path.
  2. ✅ The test remains deterministic/offline and makes no provider/live-paid calls.
  3. ✅ Replay-only data is still not labeled live.
- Verification: Test exists at `tests/e2e/arc-smoke.spec.ts:134-158`, uses daemon-sse-fixture.cjs, runs in CI e2e workflow.
- Known risks: Browser logs Theia async contribution warnings (non-blocking); daemon fixture serves minimal event set only.

### Phase 9 — BudgetVector Post-Hoc Accounting

**Status:** Complete. Implemented post-hoc accounting/reporting only; real-time pressure/exhaustion interrupts remain deferred.

Most dimensions render absent/degraded until the Phase 15 measured cost/token producer lands.

**Evidence:** Committed at `cc9cac4`. `cd python && uv run pytest tests/web/test_cli_budget.py -q` (8 passed); `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build`.

- Add a `BudgetVector` model and workflow/default-budget config shape where appropriate.
- Compute post-hoc usage from trace/metadata where data exists; mark missing dimensions as absent/degraded.
- Add `arc runs budget <id>` or equivalent CLI report.
- Add IDE gauges/readout for final consumption against configured limits.
- Deferred: real-time pressure/exhaustion interrupts at adapter effect boundaries.
- Acceptance:
  1. CLI reports available dimensions and marks unavailable dimensions as absent/degraded.
  2. IDE gauges/readout do not fabricate missing cost/token/latency data.
  3. Tests cover complete, partial, malformed, and missing budget metadata.
- Verification: Python budget/CLI tests, arc-extension static/helper tests, builds.
- Known risks: producer gaps for measured cost/token data and confusion between post-hoc accounting and hard enforcement.

### Phase 10 — Assurance Polish

**Status:** Baseline Complete | Evidence: Phase 10 assurance polish patch after `ba85262` — live refresh, filtering, export affordances, improved states, 9 new contract tests pass, and SwarmGraph Insight contract drift fixed.
**v0.1 decision:** Ship at current status. Polish already applied (auto-refresh, filtering, export, improved states). No remaining polish needed for v0.1.

- Improve existing Assurance tab HITL inbox/audit viewer with live refresh, filtering, export affordances, and clearer missing/degraded states.
- Preserve adapter-wide HMAC caution: verify/export only where audit material exists.
- Acceptance:
  1. HITL inbox auto-refreshes every 10s with LIVE badge and last-refreshed timestamp.
  2. Replay events filterable by category checkboxes (lifecycle/message/tool/error/hitl/audit/unknown) with "Clear filters" and filtered-count display.
  3. Export buttons (JSON download) for HITL, run-scoped audit material, and replay events, visible only when data exists.
  4. HITL/audit UI contract tests cover present, absent, degraded, expired, unknown-category, and replay-safe states (9 new tests).
  5. Adapter-wide HMAC caution preserved: disclaimer unchanged, export conditional on data existence.
- Verification: `pnpm --filter arc-extension build && pnpm --filter arc-extension test` — local 2026-05-19 test run passed: 754 tests, 16 suites; Jest still reports an open-handle notice after completion.
- Known risks: audit material is conditional per run path; UI must not imply adapter-wide keyed audit.

### Phase 11 — Discipline Audits

**v0.1 decision:** Ship at current status. Remaining orphan surfaces and `arc doctor storage` inclusion were addressed by Phase 14. No user-facing bugs exist at baseline.

- Run daemon/CLI parity audit and decide command vs endpoint fate for remaining orphan surfaces.
- Audit `arc doctor all` coverage against existing subchecks without changing CLI behavior.
- Keep release-facing docs aligned with reality; no release claims beyond proven gated/local/offline behavior.
- Phase 11 audit ledger draft:
  - Daemon route inventory source: `python/src/agent_runtime_cockpit/web/routes.py:710-744`.
  - Endpoint parity status: audited against current CLI and Theia extension sources. Core daemon surfaces have explicit CLI analogs or active UI consumers for health, inspect, runtimes/capabilities, workflows, schemas, run list/get/events, providers/status/accounts/routing/proxy/diagnostics, run diff, and eval run. Phase 14 assigned explicit fates for remaining surfaces: `/api/runs/start` → `ui-deferred`, `/api/runs/{run_id}/links` → CLI `arc runs links` added, `/api/telemetry/export/{run_id}` → `daemon-only-deprecated`, `/api/context/pack` → already has CLI `arc context pack`, `/api/providers/accounts/{account_id}/test` → `daemon-only-deprecated`, `/api/sse/proof` → `daemon-only-deprecated`, `/api/arena/*` → `daemon-only-deprecated`.
  - `arc doctor all` source: `python/src/agent_runtime_cockpit/cli.py`.
  - `arc doctor all` currently reports Python, CLI version, runtime detection, daemon health, SwarmGraph CLI availability, provider env-presence diagnostics, and workspace storage per ADR-009.
  - Storage diagnostics still exist separately in `arc doctor storage`; Phase 14 also includes workspace storage in `arc doctor all`.
  - Relevant CLI test evidence: `cd python && uv run pytest tests/test_cli_doctor.py tests/cli/test_cli_discoverability.py tests/test_cli_providers.py tests/test_cli_runs.py -q` passed locally with 76 tests.
- Acceptance:
  1. Remaining orphan daemon endpoints each have an explicit CLI command, UI consumer, or deferral note.
  2. `arc doctor all` coverage is documented against runtime/provider/storage checks.
  3. Banned-claims check passes on release-facing docs.
- Verification: relevant CLI tests, `bash scripts/check-banned-claims.sh ...`, `bash scripts/check-pr.sh`.
- Known risks: endpoint/CLI drift and stale release evidence.

### Phase 12 — Provider/Quota UX Completion

**Status:** Baseline Complete | Evidence: local verification on current worktree — `cd python && uv run pytest tests/test_cli_providers.py tests/test_providers.py -q` (47 passed), `pnpm --filter arc-extension test` (754 passed), `bash scripts/check-banned-claims.sh` (OK). Chunks 3.1-3.3 flipped from Partial to Baseline Complete in this commit.

- Finish Phase 3 chunks 3.1-3.3 from partial to accepted baseline/polished status.
- Closing Phase 12 must flip chunks 3.1-3.3 from Partial to Baseline Complete or Polished Complete in the same commit.
- Harden provider diagnostics rendering for malformed/partial telemetry.
- Keep quota reset local-counter-only and require targeted confirmation.
- Keep paid/live provider action default-off; require live env gate, paid opt-in, and exact confirmation before any provider request.
- Acceptance:
  1. Provider diagnostics UI has tested empty/partial/malformed/success states.
  2. Quota reset copy and backend behavior cannot imply remote/provider reset.
  3. Gated provider action UI remains impossible to trigger without every explicit gate.
  4. Banned-claims check passes.
- Verification: `pnpm --filter arc-extension test`, provider CLI tests, `bash scripts/check-banned-claims.sh ...`.
- Known risks: accidental provider-backed adoption wording, live-call leakage into default tests, quota reset ambiguity.

### Phase 13 — Live Stream UX Polish

**Status:** Baseline Complete | Evidence: local verification — `discoverPythonDaemonUrl()` protocol + backend (+4 tests), frontend 3-tier fallback (manual → env → loopback probe), async warning fingerprint e2e test. Full baseline: 863 Python passed, 758 TS passed (4 new), protocol/extension builds clean, check-pr OK, banned-claims OK.

- Resolve or suppress non-blocking Theia async contribution warnings with evidence they are harness/runtime noise.
- Capture the exact known warning fingerprint before suppressing/allowing it; e2e should fail on new warning classes.
- Add daemon URL auto-discovery or guided setup if it can be done without background network surprises.
- Preserve explicit configured-local-daemon semantics and replay/live/disconnected labels.
- **Implementation:**
  1. Backend `discoverPythonDaemonUrl()` probes `http://127.0.0.1:7777/health` with 2s timeout — loopback only, no outbound connections.
  2. Frontend `SwarmGraphInsightTab.connectLiveStream()` uses 3-tier fallback: manual input → `ARC_PYTHON_DAEMON_URL` env → loopback probe.
  3. E2E test (`async warning fingerprint`) captures console warnings and asserts only known Theia lifecycle settlement patterns are present.
  4. Known warning fingerprints documented in `KNOWN_ASYNC_WARNING_PATTERNS` array in `arc-smoke.spec.ts`.
- Acceptance:
   1. ✅ Browser/e2e logs no longer include known async contribution noise, or docs/tests prove the exact warning fingerprint is harmless and intentionally accepted. — **Done**: `KNOWN_ASYNC_WARNING_PATTERNS` test captures and fingerprints warnings.
   2. ✅ Users can discover or configure daemon URL from IDE without editing shell env when local daemon is available. — **Done**: automatic loopback probe of default port 7777 as 3rd fallback, plus existing env var + manual input.
   3. ✅ With no daemon running, IDE startup performs no outbound connections beyond loopback probes. — **Done**: discovery probes only `127.0.0.1:7777/health`; no background connections.
   4. ✅ UI still never labels replay-only data as live. — **Done**: no changes to replay/live labeling; existing `buildLiveInsightStatus` and `swarmgraph-insight-model.ts` enforce replay-live distinction.
- Verification: `pnpm --filter @arc-studio/protocol build && pnpm --filter arc-extension build && pnpm --filter arc-extension test` (758 tests, 4 new), browser build/e2e, `bash scripts/check-banned-claims.sh ...`.
- Known risks: flaky e2e (async warning capture depends on console listener timing), daemon URL drift (discovery only probes default 7777 port, not custom ports), overclaiming broad runtime live support (discovery is loopback-only).

### Phase 14 — Doctor/Daemon Parity Closure

**Status:** Baseline Complete | Evidence: local verification — ADR-009 accepted; `arc runs links` added (3 new tests); storage checks included in `arc doctor all`; orphan routes labeled with fates. Full baseline: 863 Python passed, 754 TS passed, builds clean, banned-claims OK.

- Decide CLI command, UI consumer, or explicit deferral for every remaining orphan daemon route.
- Decide whether `arc doctor storage` is included in `arc doctor all`; implement only if accepted.
- Record the `arc doctor storage` inclusion decision in an ADR before implementation; storage scans may be slower than normal doctor checks.
- Update release-facing docs with final parity state.
- Orphan route fates:
  - `/api/runs/start` → `ui-deferred` (UI uses CLI `arc run` instead)
  - `/api/runs/{run_id}/links` → Added `arc runs links` CLI command (CRITICAL: Theia backend called this non-existent command)
  - `/api/telemetry/export/{run_id}` → `daemon-only-deprecated` (daemon handler is simulated/experimental OTLP export)
  - `/api/context/pack` → Already has CLI `arc context pack`
  - `/api/providers/accounts/{account_id}/test` → `daemon-only-deprecated` (daemon handler is stub)
  - `/api/sse/proof` → `daemon-only-deprecated` (developer proof endpoint)
  - `/api/arena/*` → `daemon-only-deprecated` (stub/gated Arena surfaces, no product claim)
- Acceptance:
  1. Each orphan route has a CLI analog, active UI consumer, or one explicit fate label: `cli-todo`, `ui-deferred`, or `daemon-only-deprecated`.
  2. `arc doctor all` storage behavior is ADR-backed, tested, and documented.
  3. No docs imply complete parity unless all listed gaps are closed.
- Verification: relevant CLI tests, daemon route tests where changed, `bash scripts/check-banned-claims.sh ...`.
- Known risks: endpoint drift, adding low-value CLI commands, stale docs.

### Phase 15 — SwarmGraph Cost Producer + Cost UX

**Status:** Baseline Complete | Evidence: local verification — 867 Python passed, 762 TS passed (17 new tests), protocol/extension builds clean, check-pr OK, banned-claims OK.

- Add measured cost/token producer before enriching SwarmGraph cost panels.
- First nominated producer: `langgraph+swarmgraph`, because it already emits topology/consensus events.
- Producer schema includes provider, model, promptTokens, completionTokens, totalCost, source, and measured (ISO timestamp) before UI enrichment.
- Keep cost panels absent/degraded until event-backed data exists.
- Extend IDE rendering only from explicit measured events/metadata.
- **Implementation:**
  1. Updated `SWARMGRAPH_COST` event schema in `protocol/events.py`: added `model`, `promptTokens`, `completionTokens`, `source` as optional fields.
  2. Updated `_measured_cost_payload()` in `langgraph_runner.py`: emits `source`, `measured` (ISO timestamp), `model`, `promptTokens`, `completionTokens` when present in config.
  3. Updated `SwarmGraphCostInsight` TypeScript interface: added `provider`, `model`, `promptTokens`, `completionTokens`, `source`, `measured`.
  4. Updated `extractCost()` in `swarmgraph-insight-model.ts`: extracts new fields with normalized aliases.
  5. Updated `CostPanel` in `SwarmGraphInsightTab.tsx`: renders all new fields when present.
  6. Added Python tests for normalized fields, partial, malformed, and absent cost states in both schema and runner layers.
  7. Added TypeScript tests for partial, malformed, and producer-backed cost states.
- Acceptance:
   1. ✅ At least one supported path (`langgraph+swarmgraph`) emits measured cost/token data with provider, model, promptTokens, completionTokens, totalCost, source, and ISO-timestamp measured field.
   2. ✅ UI renders rich cost data only from that producer; absent/degraded states remain for no-producer and empty/malformed data.
   3. ✅ Tests cover no-producer, partial, malformed, and producer-backed cost states in both Python and TypeScript.
- Verification: `cd python && uv run pytest -q` (867 passed), `pnpm --filter @arc-studio/protocol build`, `pnpm --filter arc-extension build && pnpm --filter arc-extension test` (762 passed), `bash scripts/check-pr.sh` (OK), `bash scripts/check-banned-claims.sh ...` (OK).
- Known risks: fabricated cost data, confusing post-hoc accounting with hard budget enforcement — both avoided by gating rich UI strictly on explicit measured events.

### Phase 16 — Packaging/Optional Feature Decisions

**Status:** In Progress | Evidence: ADR-008 accepted (daemon-bundling plan); `applications/electron/` with electron-builder + signing preflight exists; LM Arena stub/gated and enforced by banned-claims.

- Re-evaluate Electron packaging/signing after browser v0.1 stabilizes.
- Keep LM Arena stub/gated unless a separate live-Arena implementation plan, gates, tests, and release docs are accepted.
- Track Electron packaging and live LM Arena in separate ADRs/checklist lines; do not bundle their gate decisions.
- **Implementation (first commit):**
  1. ADR-008 accepted from Proposed → Accepted. Documents 3-phase daemon-bundling approach (PyInstaller spike → embedded Python → uv bootstrap). Phase 1 packaging spike deferred until after browser v0.1.0-alpha release.
  2. Electron packaging/signing preflight already exists at `applications/electron/electron-builder.release.yml` with `forceCodeSigning: true`, `scripts/require-electron-signing.mjs`, and `.github/workflows/signing-preflight.yml`.
  3. LM Arena remains stub-default with gated live mode; banned-claims (check-banned-claims.sh) enforces honest documentation.
  4. Electron and Arena tracked as separate items in both the Phase Status Table and the deferred ledger.
- Acceptance:
   1. ✅ Electron has a concrete packaging/signing plan (ADR-008 + existing electron-builder configs). Implementation blocked on browser v0.1 stabilization.
   2. ✅ LM Arena remains unclaimed — stub-default with gated live mode, enforced by banned-claims checker.
- Verification: `bash scripts/check-banned-claims.sh ...` (OK); `bash scripts/check-pr.sh` (signing preflight enforced); builds continue to pass.
- Known risks: signing complexity, platform drift, premature optional-feature claims — all mitigated by deferring implementation to post-v0.1.
