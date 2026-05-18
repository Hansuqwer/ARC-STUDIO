# ARC Studio — Locked Phase Implementation Plan

**Status:** Locked execution plan for remaining work.  
**Created:** 2026-05-17  
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

## Phase 1 — Active Live Streaming

**Roadmap:** R1  
**Status:** Complete — Phase 1 vertical baseline implemented

### Design Note — Current Launch/Event Flow
- IDE launch path today is ChatTab/runtime selectors → Theia backend CLI bridge → Python `arc run`/related commands. The Theia service contract now exposes `streamActiveTrace()` for live/replay event consumption.
- Python live infrastructure exists in `EventBroker.stream_live()`/`sse_handler()` and supervisor event emission, while `/api/runs/{id}/events` supports explicit live/replay SSE modes for an existing run id.
- `/api/sse-proof` is a deterministic stub live SSE endpoint. It emits `RUN_STARTED`, step data, terminal `RUN_COMPLETED`, then `STREAM_END`; it proves streaming transport semantics but is not a provider-backed runtime stream.
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

### Chunk 1.5 — Stub E2E Live Run
- Status: Complete for deterministic SSE proof stub only.
- Stub run emits deterministic events through `/api/sse-proof`.
- E2E verifies live `RUN_STARTED` + terminal event without reading stored replay.

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
**Status:** Partial — provider diagnostics/quota scaffold exists with typed parsing/tests, targeted confirmation before local quota-counter reset, profile-linked cost policy summary, backend cost-gate enforcement, and explicit paid/live opt-in gates. Reset remains local quota-counter reset only; live/provider UX performs no network/provider calls by default, and real provider execution is still not implemented.

### Chunk 3.1 — Provider Diagnostics Panel
- Surface existing CLI/provider diagnostics.
- Status: Partial — IDE exposes provider diagnostics scaffold; harden telemetry parsing with typed parser/runtime tests while preserving dry-run/offline defaults.
- Tests for dry-run/no-live default and malformed/partial provider telemetry.

### Chunk 3.2 — Quota + Profile Summary
- Display quota status and profile-linked cost policy.
- Reset only where existing CLI supports safe reset.
- Status: Partial — quota visibility scaffold exists with targeted confirmation before reset. Reset may call only existing `arc providers quota reset --json` semantics and is a local quota-counter reset, not a provider/network reset. Profile-linked cost policy summary is backed by backend opt-in cost-gate metadata; no provider execution is enabled by the UI.

### Chunk 3.3 — Paid-Call Gate UX
- Add explicit warnings/confirmations before provider-backed paths.
- Tests prove no live call without explicit opt-in.
- Status: Partial — provider-backed/live actions remain gated/offline by default. Current live-provider UX is preview/gate only and performs no network/provider calls; hardened UI copy/actions distinguish dry-run/offline, local quota reset, backend cost-gate enforcement, and any future live/provider path. Real provider execution remains future work behind explicit opt-in.

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
**Status:** Partial — `langgraph+swarmgraph` fake/offline CLI route baseline remains default; narrow local-real path now requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`, and performs no provider calls

### Chunk 6.1 — Select First Real Target
- Default recommendation: `langgraph+swarmgraph`.
- Confirm dependencies and no paid calls.
- Status: Complete — first target selected as `langgraph+swarmgraph`; current product path is fake/offline deterministic only.

### Chunk 6.2 — Real Runner Spike
- Implement narrow real invocation path.
- Preserve fake/offline tests.
- Status: Partial — `langgraph+swarmgraph` keeps deterministic fake/offline routing as the default. A narrow local-real runner path exists only behind dual explicit `ARC_REAL_RUNTIME_SMOKE=1` plus `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` gates, is not provider-backed, performs no paid/live provider calls, and is not claimed as product-ready.

### Chunk 6.3 — Capability + Smoke
- Capability reports distinguish fake-tested/gated/real.
- Opt-in real-runtime smoke covers installed deps.
- Status: Partial — capability/smoke posture distinguishes fake/offline routed baseline from the gated local-real path. Opt-in real-runtime smoke sets `ARC_REAL_RUNTIME_SMOKE=1` plus `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` and is the only real-path validation scope; provider-backed execution remains gated/not claimed.

## Phase 7 — Release Operations

**Roadmap:** R7  
**Status:** Partial — 7.1 evidence refreshed against local `main` commit `b68663b` and latest/last-green GitHub `main` run IDs; 7.2 deferred because no release date is set and latest `main` is not fully green; 7.3 remains blocked

### Chunk 7.1 — Release Evidence Refresh
- Update release checklist with latest commit/run IDs.
- Do not overclaim deferred features.
- Status: Partial — evidence refreshed for local `main` commit `b68663b`. Latest GitHub `main` evidence: `ba7b1d32` python ✅ `26023575411`, e2e ✅ `26023575414`, signing-preflight ✅ `26023575408`, node ❌ `26023575413`, ARC Roadmap Gate ❌ `26023575410`. Last all-green required-ish set remains `073238d`: python ✅ `25997787492`, node ✅ `25997787491`, ARC Roadmap Gate ✅ `25997787490`, e2e ✅ `25997787483`, signing-preflight ✅ `25997787503`. Banned-claims verification remains the docs-touch check for this phase.

### Chunk 7.2 — Green Window
- Start only after release date is set.
- Track GitHub green runs for required workflows.
- Status: Deferred — no release date is set and latest GitHub `main` is not fully green (`ba7b1d32` has node and ARC Roadmap Gate failures), so the 3-day green-window clock has not started.

### Chunk 7.3 — `.env` History Scrub
- Execute only after explicit approval for release date + history rewrite + force-push plan.
- Status: Blocked — no `.env` scrub, history rewrite, or force-push may occur without explicit release-date and destructive-action approval.

## Phase Status Table

| Phase | Status | Depends On | Notes |
|---|---|---|---|
| 1 Active Live Streaming | Complete | current CLI/IDE run basics | Full vertical baseline: Python SSE, Theia proxy contract, UI live/replay/disconnected states, stub e2e |
| 2 Runtime Setup UI | Complete polished UI baseline | config/profile CLI | Safe ConfigTab baseline plus YAML-backed safe fields summary, persisted profile copy, remediation wizard, and dedicated export-target env-ref helpers in place |
| 3 Provider/Quota UI | Partial | provider CLI | Typed parser/tests, confirmed local quota-counter reset affordance, profile-linked cost summary, backend cost-gate enforcement, hardened paid/live opt-in gates; no provider network calls by default; real provider execution remains future work |
| 4 HITL/Audit UX | Complete baseline | existing CLI/RunsTab basics | Dedicated Assurance tab; avoids adapter-wide HMAC claim |
| 5 SwarmGraph Insight | Complete baseline + first producer events | event-backed adoption data | LangGraph + SwarmGraph topology/consensus events; no fabricated cost; live-aware UI with backend live SSE still degraded/disconnected |
| 6 Real Adoption | Partial | adoption protocol | `langgraph+swarmgraph` fake/offline CLI baseline remains default; narrow local-real path requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` with no provider calls; provider-backed path gated/not claimed |
| 7 Release Ops | Partial | green CI | 7.1 evidence refreshed for local `b68663b` plus latest `ba7b1d32`/last-green `073238d` GitHub run IDs; 7.2 deferred because no release date is set and latest `main` is not fully green; 7.3 `.env` scrub blocked pending explicit destructive-action approval |
