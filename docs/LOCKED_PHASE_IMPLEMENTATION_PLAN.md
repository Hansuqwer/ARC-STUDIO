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
**Status:** Active narrow real-provider action baseline — provider diagnostics/quota scaffold exists with typed parsing/tests, targeted confirmation before local quota-counter reset, profile-linked cost policy summary, backend cost-gate enforcement, and explicit paid/live opt-in gates. Reset remains local quota-counter reset only; default UX is offline/gated and performs no provider network calls. R3 now includes one narrow gated provider action baseline for 9router/Qwen via `arc providers action`, requiring live env gate, paid-call opt-in, exact confirmation, and env/key references only. Successful live actions may update ARC local accounting only; there is no remote quota reset, provider-backed adoption, SwarmGraph/provider adoption wiring, or broad real-runtime completion claim.

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
- Status: Partial — provider-backed/live actions remain gated/offline by default. Current live-provider UX is preview/gate only unless every explicit gate is supplied; hardened UI copy/actions distinguish dry-run/offline, local quota reset, backend cost-gate enforcement, and the narrow 9router/Qwen provider-action baseline. This proves only one gated action path, not provider-backed adoption or broad real-runtime support.

### Chunk 3.4 — Real Provider Execution Contract
- Define the narrow real provider-backed action contract before implementation.
- Preserve dry-run default, explicit `allowPaidCalls`/provider-live gates, env/keychain references only, no raw secret persistence/display, and no broad provider-backed adoption claim.
- Status: Complete baseline — contract stays narrow: one explicit 9router/Qwen provider-backed action path, dry-run default, no default network, explicit paid/provider gates, env/key refs only, no raw secrets, local accounting only, no remote quota reset, and no broad adoption claim.

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
- Status: Partial — smoke/manual verification is opt-in and narrow. Evidence may prove only the gated 9router/Qwen provider action path with `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`, `--live`, `--allow-paid-calls`, and exact `RUN_PROVIDER_ACTION:<provider>:<model>` confirmation; it does not prove provider-backed adoption, SwarmGraph runtime execution, or broad real-runtime completion.

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
- Surface local-real availability in CLI/IDE capability views without claiming provider-backed adoption or readiness.
- Status: Complete — trace/metadata and CLI/IDE capability surfaces identify fake/offline versus gated local-real execution, preserve provider-backed-not-claimed copy, and have metadata/copy-guard coverage.

### Chunk 6.7 — Deterministic Regression + Opt-In Smoke
- Keep fake/offline regression tests deterministic and default in CI.
- Add/maintain opt-in local-real smoke/manual verification requiring both gates and installed deps.
- Status: Complete — fake/offline regression coverage remains deterministic/default. Opt-in local-real smoke/manual verification requires both gates plus installed deps and proves only the local-real path, not provider-backed execution.

## Phase 7 — Release Operations

**Roadmap:** R7  
**Status:** Partial — 7.1 evidence refreshed against pushed `main` commit `6d3f559` and green GitHub `main` run IDs; 7.2 green-window started from 2026-05-18 evidence toward the 2026-06-01 release date; 7.3 remains blocked with non-destructive prep checklist and destructive approval packet only

### Chunk 7.1 — Release Evidence Refresh
- Update release checklist with latest commit/run IDs.
- Do not overclaim deferred features.
- Status: Partial — evidence refreshed for pushed `main` commit `6d3f559`. Latest GitHub `main` evidence: python ✅ `26031641317`, node ✅ `26031641320`, ARC Roadmap Gate ✅ `26031641345`, e2e ✅ `26031641289`, signing-preflight ✅ `26031641260`. Banned-claims verification remains the docs-touch check for this phase.

### Chunk 7.2 — Green Window
- Start only after release date is set.
- Track GitHub green runs for required workflows.
- Status: Active — release date is set for 2026-06-01. The 3-day green-window starts from 2026-05-18 green evidence on `6d3f559` and completes on 2026-05-21 only if required workflows stay green.

### Chunk 7.3 — `.env` History Scrub
- Execute only after explicit approval for release date + history rewrite + force-push plan.
- Status: Blocked — no `.env` scrub, history rewrite, or force-push may occur without exact destructive-action approval. Current plan update is non-destructive preparation and approval-packet documentation only.

## Phase Status Table

| Phase | Status | Depends On | Notes |
|---|---|---|---|
| 1 Active Live Streaming | Complete | current CLI/IDE run basics | Full vertical baseline: Python SSE, Theia proxy contract, UI live/replay/disconnected states, stub e2e |
| 2 Runtime Setup UI | Complete polished UI baseline | config/profile CLI | Safe ConfigTab baseline plus YAML-backed safe fields summary, persisted profile copy, remediation wizard, and dedicated export-target env-ref helpers in place |
| 3 Provider/Quota UI | Active narrow real-provider action baseline | provider CLI + explicit paid/provider gates | Typed parser/tests, confirmed local quota-counter reset affordance, profile-linked cost summary, backend cost-gate enforcement, hardened paid/live opt-in gates; offline/gated by default with no provider network calls; one narrow 9router/Qwen provider action exists behind live env gate, paid opt-in, exact confirmation, env/key refs only, and ARC local accounting only; no remote quota reset or provider-backed adoption claim |
| 4 HITL/Audit UX | Complete baseline | existing CLI/RunsTab basics | Dedicated Assurance tab; avoids adapter-wide HMAC claim |
| 5 SwarmGraph Insight | Complete baseline + first producer events | event-backed adoption data | LangGraph + SwarmGraph topology/consensus events; no fabricated cost; live-aware UI with backend live SSE still degraded/disconnected |
| 6 Real Adoption | Complete local-real hardening baseline | adoption protocol + dual explicit local-real gates | `langgraph+swarmgraph` fake/offline CLI baseline remains default; narrow local-real path has contract, dependency/preflight states, metadata/IDE surfacing, and smoke/regression coverage; both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` are required for local-real availability; no provider calls are made or claimed |
| 7 Release Ops | Partial | green CI | 7.1 evidence refreshed for pushed `6d3f559` with green `python`, `node`, `ARC Roadmap Gate`, `e2e`, and `signing-preflight`; 7.2 active toward 2026-06-01 release date; 7.3 `.env` scrub blocked pending explicit destructive-action approval with non-destructive prep checklist and approval packet only |
