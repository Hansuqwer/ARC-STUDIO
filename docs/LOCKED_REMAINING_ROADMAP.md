# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.  
**Created:** 2026-05-17  
**Update rule:** Update this file in the same commit whenever implementation status changes. Do not create replacement roadmap/status/implementation markdowns.

## Current Baseline

- Canonical app: `applications/browser` + `packages/arc-extension`.
- Legacy `theia-extensions/*` and `packages/arc-browser-app` are archived under `docs/archive/`.
- GitHub CI green on `073238d`: `python`, `node`, `ARC Roadmap Gate`, `signing-preflight`, `e2e`.
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

**Current:** CLI config/profiles/workspace commands exist; ChatTab exposes runtime/profile selectors; no full setup wizard.

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

**Current:** CLI provider diagnostics/quota commands exist; IDE surface is thin.

**Deliverables:**
- Provider diagnostics panel.
- Quota status/reset UI where safe.
- Paid-call gate warnings before any provider-backed action.
- Profile-linked provider/cost summary.

**Acceptance:**
- Tests prove no live provider call without explicit gate.
- UI clearly labels dry-run/offline vs live/gated.

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

**Current:** Vendored SwarmGraph has queen/worker/consensus/HITL/audit; ARC adoption runners are mostly fake-tested/gated.

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

**Current:** Adoption protocol/runners exist; only `crewai+swarmgraph` fake/offline CLI path is routed for product use.

**Deliverables:**
- Pick one first real target (`LangGraph + SwarmGraph` recommended).
- Implement real runtime invocation through SwarmGraph worker/consensus path.
- Paid/provider/privacy gates if any external calls occur.
- Trace/audit metadata identifies fake/offline vs real provider-backed execution.

**Acceptance:**
- Offline fake tests remain deterministic.
- Opt-in real-runtime smoke proves the real path where deps are installed.
- Capability reports distinguish fake-tested/gated/real clearly.

## R7 — Release Operations + History Hygiene

**Goal:** Prepare v0.1 release without rewriting history prematurely.

**Current:** Release checks are green; `.env` history scrub is planned but gated.

**Deliverables:**
- Final release checklist evidence with commit/run IDs.
- 3-day green-window record when release date is set.
- Execute `.env` scrub only after explicit release-date/history-rewrite approval.
- Tag/build release artifacts after gates pass.

**Acceptance:**
- `docs/RELEASE_CHECKLIST.md` has current evidence.
- No force-push/history rewrite without explicit approval.

## Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | Phase 2 IDE Runtime Setup + Config |
| R2 IDE Runtime Setup | Not started | Config read/write backend + static UI contract |
| R3 Provider/Quota UI | Not started | Provider diagnostics panel scaffold |
| R4 HITL/Audit UX | Complete baseline | Later polish only: live refresh/filtering/export affordances |
| R5 SwarmGraph Insight | Deferred | Define event-backed empty-state contracts |
| R6 Real Adoption | Deferred | LangGraph + SwarmGraph narrow real path spike |
| R7 Release Ops | Partial | Refresh checklist evidence; `.env` scrub remains gated |
