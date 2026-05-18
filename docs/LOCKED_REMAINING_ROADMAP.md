# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.  
**Created:** 2026-05-17  
**Last reality refresh:** 2026-05-18 against current locked phase status and release evidence.  
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
- GitHub CI green on `6d3f559`: `python`, `node`, `ARC Roadmap Gate`, `signing-preflight`, `e2e`.
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
|---|---|---|---|
| Active run SSE transport events | `EventBroker`/`JobSupervisor`, `/api/runs/{id}/events`, `/api/sse-proof` stub | Baseline Complete | Event Stream, Run Timeline |
| `RUN_STARTED` / terminal events | SSE proof stub and supported run paths | Baseline Complete | Event Stream, Run Timeline |
| SwarmGraph topology | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Consensus/vote events | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Measured cost/token events | None broadly wired | Not Started | Budget/Cost panels show absent/degraded |
| HITL prompt/response/timeout | `JobSupervisor` HITL flow + CLI/IDE response paths | Baseline Complete | Assurance tab, Runs tab basics |
| Audit chain material | ARC audit paths and keyed audit CLI path where specific run writes material | Conditional | Assurance tab, audit verify/export |
| Effect-boundary journal entries | None | Deferred | Future replay/fork UX |

## Documentation Inventory

| Location | Purpose |
|---|---|
| `docs/LOCKED_REMAINING_ROADMAP.md` | Authoritative roadmap/status. |
| `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` | Authoritative ordered execution plan. |
| `docs/adr/` | Architecture decisions. |
| `docs/research/` and `docs/wiki/research-context/` | Supporting research/scaffolds only, not status. |
| `docs/RELEASE_CHECKLIST.md` | Release evidence and gates. |
| `docs/archive/` | Historical context only. |
| `docs/handover/` | Thin pointers/context; must defer to locked docs. |
| `scripts/check-banned-claims.sh` | Enforced release-claim guard. |

## R1 — Live Run Streaming Product Path

**Goal:** Active runs stream events into IDE views while running, not only replay stored traces.

**Current:** Complete Phase 1 vertical baseline plus Phase 8 local daemon productization baseline. Python SSE supports active/replay modes and terminal/disconnected semantics; Theia exposes a typed `streamActiveTrace()` proxy that can use an explicit/requested Python web base URL or `ARC_PYTHON_DAEMON_URL`; Event Stream/SwarmGraph Insight surfaces distinguish live/replay/disconnected states; `/api/sse-proof` has deterministic limited-local coverage only and is not evidence of broad runtime live streaming.

**Deliverables:**
- Python active run stream endpoint or command path backed by `EventBroker`/`JobSupervisor`.
- Theia backend subscription/proxy with env filtering and cancellation safety.
- Event Stream/Run Timeline live state: connecting, live, replay, disconnected.
- Stub-backed e2e proving live events arrive during a launched run.

**Acceptance:**
- Unit/web tests for active stream lifecycle.
- E2E launches or connects to a stub live stream and observes at least `RUN_STARTED` and terminal event live.
- Docs distinguish broker-backed active stream, deterministic SSE proof stub, and stored-trace replay.

**Status:** Baseline Complete for configured local daemon/stub runtime live streaming. Evidence: local Phase 8 verification on `bec8d4b` worktree (`python` web SSE tests, arc-extension tests/build, browser build/e2e, `scripts/check-pr.sh`). Notes: IDE live mode can connect to configured Python daemon/local runtime streams and handles terminal/degraded states while preserving replay-not-live copy; this is not a broad runtime/provider-backed live-streaming claim.

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

**Current:** CLI provider diagnostics/quota commands exist; IDE has a provider diagnostics/quota scaffold with typed telemetry parsing/tests, targeted confirmation before local quota-counter reset, a profile-linked cost policy summary, backend cost-gate metadata/enforcement, and hardened explicit paid/live opt-in gate wording. Reset is backed only by existing `arc providers quota reset --json` local quota-counter semantics. Live/provider UX remains offline/gated by default and performs no provider network calls. R3 now includes one narrow gated provider-action baseline for 9router-routed model calls via `arc providers action`, requiring the live env gate, paid-call opt-in, exact confirmation, and env/key references only. Opt-in smoke evidence passed on `9184f9b` for `9router` with `nvidia/minimaxai/minimax-m2.7`; successful live actions may update ARC local accounting only. There is no remote quota reset, provider-backed adoption, SwarmGraph/provider adoption wiring, or broad real-runtime completion claim.

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

**Current:** Dedicated IDE Assurance tab exists with HITL inbox, run-scoped audit chain states, and replay stepper annotations. HITL pending/respond CLI and RunsTab basics still exist; audit verify/export/key CLI exists; adapter-wide HMAC is not guaranteed.

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

**Current:** Release ops evidence is improved but not release-ready. Target release date is 2026-06-01. Pushed `main` commit `6d3f559` is green for the required-ish GitHub workflows checked on 2026-05-18: `python` (`26031641317`), `node` (`26031641320`), `ARC Roadmap Gate` (`26031641345`), `e2e` (`26031641289`), and `signing-preflight` (`26031641260`). The 3-day green-window starts from this 2026-05-18 green evidence and completes on 2026-05-21 only if required workflows stay green. `.env` history scrub remains blocked until explicit history-rewrite/force-push approval. The scrub plan includes a non-destructive preparation checklist and destructive approval packet only; no scrub/rewrite/force-push was performed.

**Deliverables:**
- Final release checklist evidence with commit/run IDs.
- 3-day green-window record when release date is set.
- Execute `.env` scrub only after explicit release-date/history-rewrite approval.
- Tag/build release artifacts after gates pass.

**Acceptance:**
- `docs/RELEASE_CHECKLIST.md` has current evidence.
- No force-push/history rewrite without explicit approval.
- No 3-day green-window starts until a release date is set.

## Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | Phase 2 IDE Runtime Setup + Config |
| R2 IDE Runtime Setup | Complete polished UI baseline | Backend protocol/service expansion only if future config fields require it; continue env-ref-only secret posture |
| R3 Provider/Quota UI | Active narrow real-provider action baseline | Keep provider calls offline/gated by default; backend cost enforcement is in place; one narrow 9router provider-action path requires explicit opt-in, paid-call gates, exact confirmation UX, env/key refs only, local accounting, and opt-in smoke/manual verification. Smoke evidence passed on `9184f9b` with `nvidia/minimaxai/minimax-m2.7`. No remote quota reset; not a provider-backed adoption claim |
| R4 HITL/Audit UX | Complete baseline | Later polish only: live refresh/filtering/export affordances |
| R5 SwarmGraph Insight | Complete baseline + first producer events | Add measured cost producer and complete backend live SSE wiring before live-runtime claims |
| R6 Real Adoption | Complete local-real hardening baseline | Keep fake/offline deterministic/default; local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; no paid/live provider calls; provider-backed execution remains blocked/unclaimed |
| R7 Release Ops | Partial | Release date set for 2026-06-01; green-window started from 2026-05-18 `6d3f559` green evidence; `.env` scrub still blocked pending explicit destructive-action approval |

## v0.2 Planning Decision — Option A

**Status:** Accepted planning input, subordinate to this locked roadmap and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`.

v0.2 product work is scoped to IDE productization of existing/gated capabilities, not a replay-architecture cycle. Effect-boundary deterministic replay, journal-backed fork/resume, adapter-wide real-time budget interrupts, and standalone SwarmGraph internal event capture are deferred unless explicitly reprioritized in this locked roadmap.

### v0.2 Scope

- Live-stream productization baseline is complete for configured Python daemon/local runtime streams beyond the deterministic SSE proof stub. Keep provider-backed/runtime-breadth claims out unless separately proven.
- Add BudgetVector post-hoc accounting/reporting and IDE gauges from trace/metadata where data exists. Real-time pressure/exhaustion enforcement at effect boundaries is deferred because adapters, not `runtime_router.py`, observe most effect boundaries.
- Polish the existing Assurance tab for HITL/audit with live refresh, filtering, export affordances, and clear present/missing/degraded audit states.
- Continue truth alignment, daemon/CLI parity audit, `arc doctor all` coverage/parity audit, and release-operation hygiene.

### Deferred From v0.2

- Effect-boundary replay and `arc runs fork` over journaled adapter responses.
- Adapter-wide BudgetVector interrupts and hard enforcement at model/tool-call boundaries.
- New adapters or adapter status upgrades without corresponding IDE views.
- Live LM Arena and Electron release packaging.

## Deferred Ledger

| Item | Deferred Until | Unblock Gate |
|---|---|---|
| Effect-boundary replay / journal-backed fork | v0.3+ | Adapter/effect instrumentation is explicitly in scope. |
| Real-time BudgetVector pressure/exhaustion interrupts | v0.3+ | Effect-boundary data is observable for the target runtime path. |
| Standalone SwarmGraph internal topology/consensus capture | Later productization | ARC can consume real emitted events from standalone SwarmGraph, not fabricated summaries. |
| Broad provider-backed adoption | Later productization | Provider gates, privacy gates, tests, and IDE views are all present. |
| New adapters | Later roadmap | IDE views and support burden are explicitly accepted. |
| Electron release packaging | Post-browser release | Browser release gates are stable and packaging/signing is reprioritized. |
