# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.  
**Created:** 2026-05-17  
**Last reality refresh:** 2026-05-19 against current locked phase status and release evidence.  
**Current evidence anchor:** `ec36b55` | refreshed 2026-05-19 | docs-only updates after this anchor must not widen release claims.  
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
- GitHub CI green on `ec36b55`: `python`, `node`, `ARC Roadmap Gate`, `signing-preflight`, `e2e`. All Baseline Complete phases evaluated for polish; all ship at current status for v0.1 (polish deferred to v0.2).
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
| Active run SSE transport events | `EventBroker`/`JobSupervisor`, `/api/runs/{id}/events`, `/api/sse/proof` stub | Baseline Complete | Event Stream, Run Timeline |
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

**Follow-up:** Browser e2e still logs Theia async contribution warnings while passing; treat as known harness/runtime noise until a dedicated cleanup phase proves otherwise. A separate Phase 8.1 should add a true IDE-to-daemon SSE e2e harness before claiming UI-rendered live daemon frames end-to-end.

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

**Current:** Release ops complete as Phase 7. Target release date is 2026-06-01. Pushed `main` commit `ec36b55` is green for the required GitHub workflows: `python`, `node`, `ARC Roadmap Gate`, `e2e`, and `signing-preflight`. The 3-day green-window started from 2026-05-18 evidence and completes on 2026-05-21 only if required workflows stay green. `.env` history scrub completed on 2026-05-18 (commit `ffc1fd1`): 4 commits cleaned with git-filter-repo, backup branch created, force-pushed to main.

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
| R1 Live Run Streaming | Complete | No v0.1 action; Phase 13 handles v0.2 live-stream UX polish |
| R2 IDE Runtime Setup | Complete polished UI baseline | Backend protocol/service expansion only if future config fields require it; continue env-ref-only secret posture |
| R3 Provider/Quota UI | Baseline Complete — chunks 3.1-3.3 hardened | Chunks 3.1-3.3 hardened to Baseline Complete: typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate. Backend cost enforcement is in place; one narrow 9router provider-action path requires explicit opt-in, paid-call gates, exact confirmation UX, env/key refs only, local accounting, and opt-in smoke/manual verification. Smoke evidence passed on `9184f9b` with `nvidia/minimaxai/minimax-m2.7`. No remote quota reset; not a provider-backed adoption claim |
| R4 HITL/Audit UX | Complete baseline | Dedicated Assurance tab baseline exists; Phase 10 adds live refresh, filtering, export, and improved states without adapter-wide HMAC claims |
| R5 SwarmGraph Insight | Complete baseline + first producer events | Configured local daemon SSE is wired in Phase 8; SwarmGraph insight live producer/cost producer work remains Phase 15 |
| R6 Real Adoption | Complete local-real hardening baseline | Keep fake/offline deterministic/default; local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; no paid/live provider calls; provider-backed execution remains blocked/unclaimed |
| R7 Release Ops | Complete | Release date set for 2026-06-01; green-window active; `.env` scrub completed on 2026-05-18 (commit `ffc1fd1`); all required GitHub workflows green on `ec36b55` |
| R8 IDE Provider/Quota Completion | Baseline Complete | Chunks 3.1-3.3 hardened — typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate; no remote quota reset or adoption claim |
| R9 IDE Live Stream Polish | Not Started | Resolve/accept Theia async warning noise and add daemon URL discovery/guided setup for configured local daemon streams only |
| R10 Doctor/Daemon Parity Closure | Not Started | Decide CLI/UI/deferral fate for orphan daemon routes; decide if `arc doctor storage` joins `arc doctor all` |
| R11 SwarmGraph Cost Producer | Not Started | Add measured cost/token producer before enriching IDE cost panels beyond absent/degraded states |
| R12 Packaging/Optional Features | Not Started | Re-evaluate Electron packaging/signing and live LM Arena separately after browser v0.1 stabilizes |

**Active v0.2 execution order:** R8/Phase 12 → R10/Phase 14 → R9/Phase 13 → R11/Phase 15 → R12/Phase 16. Doctor/daemon parity comes before live-stream auto-discovery so any new daemon/doctor surface extends a stable inventory.

## v0.2 Planning Decision — Option A

**Status:** Accepted planning input, subordinate to this locked roadmap and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`.

v0.2 product work is scoped to IDE productization of existing/gated capabilities, not a replay-architecture cycle. Effect-boundary deterministic replay, journal-backed fork/resume, adapter-wide real-time budget interrupts, and standalone SwarmGraph internal event capture are deferred unless explicitly reprioritized in this locked roadmap.

### v0.1 Polish Deferral Plan

**Decision:** Ship v0.1.0-alpha at the current Baseline Complete/Complete statuses. Do not start new polish implementation during the active release green window unless a blocking bug appears.

**Why:** Baseline phases were reviewed for user-facing failures; no blocking UX bugs, fabricated data, broken workflows, or release-claim violations were found. Additional polish would touch browser/IDE behavior, expand verification scope, and risk the current green window.

**v0.1 actions:**

- Freeze Phase 4, 5, 8, 10, and 11 behavior except for blocker fixes.
- Keep release docs honest about configured local daemon streams, conditional audit material, absent cost producers, and daemon/doctor parity gaps.
- Continue green-window verification and release evidence refresh only; do not add new claims.

**v0.2 carry-forward:**

- Phase 11: Merge `arc doctor storage` into `arc doctor all` if accepted, and decide CLI/UI fate for orphan daemon routes.
- Phase 8: Resolve non-blocking Theia async contribution warnings and add daemon URL auto-discovery.
- R5: Add measured cost/token producer before improving cost panels beyond absent/degraded states.

### Remaining IDE Work

**Status:** Not Started for v0.2+ unless a blocking v0.1 bug appears.

The browser IDE is v0.1-alpha shippable but not fully complete. Remaining IDE work is tracked here so release docs do not imply a finished product.

| Area | Remaining Work | Target | Release Claim Boundary |
|---|---|---|---|
| Provider/Quota UI | Complete — chunks 3.1-3.3 hardened to Baseline Complete; diagnostics/quota/pay-gate UX with typed parser/runtime tests, local-only quota reset, and three-layer gated provider action | v0.2 | No remote quota reset; no broad provider-backed adoption claim |
| Live Stream UX | Remove/quiet non-blocking Theia async contribution warnings; add daemon URL auto-discovery or guided connection setup | v0.2 after Doctor/Daemon Parity | Configured local daemon stream only; not broad runtime/provider live support |
| SwarmGraph Cost UX | Add measured cost/token producer before rendering rich cost panels | v0.2+ | Empty/degraded cost state remains correct until producer exists |
| Doctor/Daemon Parity | Decide CLI/UI fate for `/api/runs/start`, `/api/runs/{run_id}/links`, `/api/telemetry/export/{run_id}`, `/api/context/pack`, `/api/providers/accounts/{account_id}/test`, `/api/sse/proof`, `/api/arena/*` | v0.2 | No complete daemon CLI/UI parity claim until closed |
| Doctor Coverage | Decide whether `arc doctor storage` belongs in `arc doctor all`; add tests if changed | v0.2 | Release docs must state storage is separate until implemented |
| Electron App | Package/sign Electron only after browser release stabilizes | Post-v0.1 | Browser app remains canonical release target |
| LM Arena | Keep stub/gated; productize only with separate gates/tests/docs | Later | No live Arena product claim |

### v0.2 Scope

- Live-stream productization baseline is complete for configured Python daemon/local runtime streams beyond the deterministic SSE proof stub. Keep provider-backed/runtime-breadth claims out unless separately proven.
- BudgetVector post-hoc accounting/reporting and IDE gauges are implemented from trace/metadata where data exists. Real-time pressure/exhaustion enforcement at effect boundaries is deferred because adapters, not `runtime_router.py`, observe most effect boundaries.
- Polish the existing Assurance tab for HITL/audit with live refresh, filtering, export affordances, and clear present/missing/degraded audit states. **Complete** in Phase 10 assurance polish patch `ba85262`.
- Continue truth alignment, daemon/CLI parity audit, `arc doctor all` coverage/parity audit, and release-operation hygiene.

### Phase 11 Discipline Audit Status

**Status:** Baseline Complete | Evidence: local source audit against daemon routes in `python/src/agent_runtime_cockpit/web/routes.py:710-744`, doctor implementation in `python/src/agent_runtime_cockpit/cli.py:739-851`, storage subcheck at `:939-980`, and scoped CLI tests (`76 passed`) | Notes: remaining direct-daemon orphan/deferred surfaces are documented below; docs must not imply complete CLI/UI parity for every daemon route.

`arc doctor all` currently covers Python, CLI version, runtime detection, daemon health, SwarmGraph CLI availability, and provider env-presence diagnostics. Storage diagnostics are implemented as `arc doctor storage`, but current source does not show storage included in `arc doctor all`; release docs should state that gap until tests or code change prove otherwise.

Daemon parity audit: core inspection/runtime/workflow/schema/run/provider/diff/eval routes have CLI analogs or active UI consumers. Remaining deferred/orphan surfaces are `/api/runs/start` direct daemon start (current UI uses CLI `arc run`), `/api/runs/{run_id}/links` (daemon route exists while Theia expects missing CLI `arc runs links`), `/api/telemetry/export/{run_id}`, `/api/context/pack`, `/api/providers/accounts/{account_id}/test`, limited-local `/api/sse/proof`, and gated/stub `/api/arena/*` surfaces. These are not release claims.

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
