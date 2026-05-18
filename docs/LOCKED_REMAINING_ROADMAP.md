# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.  
**Created:** 2026-05-17  
**Update rule:** Update this file in the same commit whenever implementation status changes. Do not create replacement roadmap/status/implementation markdowns.

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

## R1 — Live Run Streaming Product Path

**Goal:** Active runs stream events into IDE views while running, not only replay stored traces.

**Current:** Complete Phase 1 vertical baseline. Python SSE supports active/replay modes and terminal/disconnected semantics; Theia exposes a typed `streamActiveTrace()` proxy; Event Stream and Run Timeline distinguish live/replay/disconnected states; `/api/sse-proof` has deterministic e2e coverage for live stub `RUN_STARTED` + terminal delivery.

**Deliverables:**
- Python active run stream endpoint or command path backed by `EventBroker`/`JobSupervisor`.
- Theia backend subscription/proxy with env filtering and cancellation safety.
- Event Stream/Run Timeline live state: connecting, live, replay, disconnected.
- Stub-backed e2e proving live events arrive during a launched run.

**Acceptance:**
- Unit/web tests for active stream lifecycle.
- E2E launches or connects to a stub live stream and observes at least `RUN_STARTED` and terminal event live.
- Docs distinguish broker-backed active stream, deterministic SSE proof stub, and stored-trace replay.

**Status:** Complete for the v0.1 vertical baseline. Remaining enhancements belong to later runtime/productization work, especially wiring Theia live mode to a configured Python web base URL for real in-flight runtime streams beyond the deterministic stub path.

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

**Current:** CLI provider diagnostics/quota commands exist; IDE has a provider diagnostics/quota scaffold with typed telemetry parsing/tests, targeted confirmation before local quota-counter reset, a profile-linked cost policy summary, backend cost-gate metadata/enforcement, and hardened explicit paid/live opt-in gate wording. Reset is backed only by existing `arc providers quota reset --json` local quota-counter semantics. Live/provider UX remains offline/gated by default and performs no provider network calls without explicit opt-in. R3 now includes a narrow gated provider-action track, but this is contract/scaffold status only unless all gates, confirmation, local accounting, and opt-in smoke/manual evidence are present; it is not a broad provider-backed adoption or real-runtime completion claim.

**Deliverables:**
- Provider diagnostics panel.
- Quota status/reset UI where safe; confirmation required before reset. Reset is local quota-counter reset only, not a provider/network reset.
- Paid-call gate warnings before any provider-backed action; current live-provider UX is preview/gate only and performs no network/provider calls.
- Profile-linked provider/cost summary backed by backend cost-gate metadata; UI does not enable provider execution.
- Gated provider-backed action path with dry-run default, no default network, env/keychain references only, explicit paid-call opt-in, confirmation UX, local cost/quota accounting, and no broad provider-backed adoption claim until tested end-to-end.

**Acceptance:**
- Tests prove no live provider call without explicit gate.
- UI clearly labels dry-run/offline vs live/gated.
- Parser/runtime tests cover malformed or partial provider telemetry without enabling provider network calls.
- Opt-in smoke/manual verification proves only the narrow gated provider-action path runs when all gates are set; default tests remain offline and deterministic, and evidence does not imply provider-backed adoption or SwarmGraph runtime execution.

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
| R3 Provider/Quota UI | Active narrow real-provider scaffold | Keep provider calls offline/gated by default; backend cost enforcement is in place; narrow gated provider-action track requires explicit opt-in, paid-call gates, confirmation UX, env/keychain refs only, local accounting, and opt-in smoke/manual verification. Contract/scaffold only unless those gates/evidence are present; not a provider-backed adoption claim |
| R4 HITL/Audit UX | Complete baseline | Later polish only: live refresh/filtering/export affordances |
| R5 SwarmGraph Insight | Complete baseline + first producer events | Add measured cost producer and complete backend live SSE wiring before live-runtime claims |
| R6 Real Adoption | Complete local-real hardening baseline | Keep fake/offline deterministic/default; local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; no paid/live provider calls; provider-backed execution remains blocked/unclaimed |
| R7 Release Ops | Partial | Release date set for 2026-06-01; green-window started from 2026-05-18 `6d3f559` green evidence; `.env` scrub still blocked pending explicit destructive-action approval |
