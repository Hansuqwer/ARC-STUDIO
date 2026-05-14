# ARC Studio — Full Repo Reality Audit

Generated: 2026-05-14

> **Prerequisite decision confirmed**: `packages/arc-extension` is the true/canonical Theia extension. The README claim (line 208) that it is unused is **incorrect** — it is wired into the browser app, has 239 tests, recent commits, and active DI bindings. `theia-extensions/arc-core` is a duplicate/alternative that should be reconciled or removed.

---

## 1. Executive Summary

1. **ARC Studio is a Python CLI + local aiohttp daemon, NOT a real IDE.** The Theia shell exists (12 extensions, meaningful widget code) but talks to the Python daemon via JSON-RPC or CLI subprocess. There is no embedded Python runtime in the Theia process.

2. **There are TWO live Theia extension packages, which is contradictory.** `packages/arc-extension` is the canonical one (per user confirmation). `theia-extensions/arc-core` is a parallel implementation. The README says `arc-extension` is dead — this is false. Both are live. This must be reconciled.

3. **SwarmGraph (vendored in `runtimes/swarmgraph/`) is a real, working runtime.** It has queen/worker graph, 3-protocol consensus, HITL/interrupt, HMAC-SHA256 audit chain, multi-provider gateway (12 providers), quota, replay safety, deterministic orchestration. But ARC does NOT use it as a shared "adoption layer" for other runtimes. ARC calls it only as a CLI subprocess (`swarmgraph swarm --json`).

4. **No runtime adapter uses SwarmGraph as its execution engine.** Every adapter runs standalone: SwarmGraph CLI, LangGraph via `importlib`, CrewAI via `importlib`, OpenAI Agents via in-process SDK, AG2 via `a_run_group_chat`. There is zero shared SwarmGraph orchestration wrapping other runtimes — no other runtime goes through queen/worker/consensus/HITL/audit.

5. **CrewAI and OpenAI Agents adapters have real runtime execution code** (not just mocks). Both can import the real library, resolve workspace exports, run workflows, and return RunRecords. However `export_workflow()` returns only a single static node (`_static.py:static_workflow`). No graph extraction.

6. **AG2 adapter code exists but is NOT registered in the adapter registry.** It has a runner, detections, and mapping but is absent from `adapters/registry.py:build_default()`. It is invisible to `arc runtimes` and `arc run`.

7. **The LM Arena adapter and service are stub-default with a gated live path.** All four modes (battle/direct/code/agent-arena-preview) return canned stub text. There is zero live LLM integration. `ARC_ALLOW_LIVE_ARENA=true` gates nothing real in the current v0.1 code.

8. **The "combo runtime adapter" exists** but only runs adapters sequentially (not SwarmGraph composition). It's a for-loop calling each adapter's `run_workflow` in order. No queen/worker decomposition, no voting, no consensus.

9. **Test coverage is entirely unit/contract/mock.** No end-to-end test proves any real runtime executes a real workflow. Tests prove ARC plumbing, schema compatibility, trace persistence, and SSE endpoints — but not runtime execution against real SwarmGraph/LangGraph/CrewAI/OpenAI Agents.

10. **Security: no auth by default** (optional bearer token via `ARC_DAEMON_TOKEN`), subprocess env redaction implemented but not comprehensive, audit chain is SHA-256 only (no HMAC), no concurrent-user readiness, no release packaging.

---

## 2. Implementation Reality Table

| Area | Intended | Actual | Status | Evidence | Gap |
|---|---|---|---|---|---|
| **Product identity** | Eclipse Theia IDE + Python backend | Python CLI/daemon with Theia shell frontend | Partial | README L3; `web/server.py` L1-5; 12 theia-extensions | Theia is a thin UI overlay, not the primary product |
| **Extension split** | Single extension path | TWO live extensions: `packages/arc-extension` (canonical) + `theia-extensions/arc-core` (duplicate) | Contradictory | `applications/browser/package.json` depends on `arc-extension`; `arc-core` has parallel impl; README L208 claims arc-extension is dead (false) | Must reconcile: keep arc-extension, deprecate/remove arc-core |
| **SwarmGraph vendored** | In-repo canonical runtime | 3-package monorepo with full queen/worker/consensus/HITL/audit | Implemented | `runtimes/swarmgraph/packages/`; `hive-swarm/swarm/nodes/consensus.py`; `swarm_shared/audit.py` | Full, not partial |
| **SwarmGraph as adoption layer** | All runtimes run through SwarmGraph | No adapter uses SwarmGraph engine | Fiction | `swarmgraph/runner.py` calls CLI subprocess; all other adapters import runtimes directly | **Core gap: no adoption layer exists** |
| **SwarmGraph audit in ARC** | HMAC-SHA256 signed audit chain | SHA-256 hash chain (no HMAC secret) | Partial | `audit/chain.py` L1-5 SHA256 only; `swarm_shared/audit.py` has real HMAC | ARC audit is simplified; SwarmGraph audit not exposed |
| **LangGraph adapter** | Full detection + run + stream | Real `importlib` run, AST fallback, streaming fallback | Implemented | `langgraph.py` L159-198 real run; L200-224 stream impl | No live streaming into ARC traces |
| **CrewAI adapter** | Full detection + run + graph | Real `importlib` run, static workflow export, paid-call gating | Partial | `crewai.py` L119-154 real run; L113-117 static export | Graph extraction missing; static export only |
| **OpenAI Agents adapter** | Detection + run + stream | Inline hardcoded TestAgent, static export, RunHooks | Partial | `openai_agents.py` L268-281 hardcoded `Agent(name="TestAgent")` | No workspace export target; hardcoded agent |
| **AG2 adapter** | Registered + runnable | Code exists but NOT registered | Stub-only | `adapters/ag2/runner.py` exists; NOT in `registry.py:build_default()` | Not wired; invisible to CLI/daemon |
| **LlamaIndex adapter** | Detection + export | Static detection only; no run | Partial | `llamaindex.py` 38 lines, detect only, no run_workflow | No execution capability |
| **LM Arena adapter** | Live provider comparison | 100% stub responses | Static | `arena/service.py` L78-150 `_stub_battle/direct/code/agent_preview` | No real LLM calls |
| **Combo adapter** | SwarmGraph composition | Sequential for-loop, no composition | Static | `runtime_router.py:ComboRuntimeAdapter` L42-101 | Not adoption; not SwarmGraph |
| **Theia UI** | Full runtime cockpit | Status cards + basic actions | Partial | `arc-main-widget.tsx` runtime readiness, recent runs | No runtime config, HITL, audit viewer, event stream |
| **Python daemon** | Full REST API | 18 endpoints, CORS, optional auth | Implemented | `web/routes.py` L558-590; `web/server.py` L70-98 | SSE replay-only, no live streaming |

---

## 3. Runtime Matrix

### Standalone Runtimes

| Runtime | Can detect | Can inspect/export | Can run | Can stream | Can audit/replay | Status | Evidence |
|---|---|---|---|---|---|---|---|
| SwarmGraph | YES (heuristic) | YES (AST + fixture fallback) | YES (CLI subprocess) | NO | NO (ARC audit, not SG HMAC) | Implemented | `swarmgraph.py` L187-227 detect; L229-290 export; L292-404 run |
| LangGraph | YES (dep check) | YES (real import, AST, fixture) | YES (importlib) | YES (fallback) | NO | Implemented | `langgraph.py` L246-280 detect; L282-498 export; L159-198 run; L200-224 stream |
| CrewAI | YES (dep check) | Static only (1 node) | YES (importlib) | NO | NO | Partial | `crewai.py` L103-111 detect; L113-117 static export; L119-154 run |
| OpenAI Agents | YES (dep check) | Static only (1 node) | YES (importlib, hardcoded agent) | NO | NO | Partial | `openai_agents.py` L132-148 detect; L150-154 static export; L156-323 run |
| AG2 | YES (modular code) | Static only | YES if registered | NO | NO | Stub (not registered) | `adapters/ag2/` code exists; NOT in `registry.py:build_default()` |
| LlamaIndex | YES (dep check) | Static only (1 node) | NO | NO | NO | Partial | `llamaindex.py` 38 lines, no run_workflow |

### "+ SwarmGraph Adoption Layer" Runtimes

| Runtime + SG | Current status | Evidence | Gap to vision |
|---|---|---|---|
| CrewAI + SwarmGraph | **Does not exist** | No code references SG adoption | Need SwarmGraph runner wrapping CrewAI kickoff through queen/workers/consensus |
| LangGraph + SwarmGraph | **Does not exist** | No code references SG adoption | Need SG wrapper around LangGraph graphs |
| OpenAI Agents + SwarmGraph | **Does not exist** | No code references SG adoption | Need SG runner wrapping Agents SDK Runner.run() |
| AG2 + SwarmGraph | **Does not exist** | No code references SG adoption | Need SG runner wrapping AG2 group chat |
| LlamaIndex + SwarmGraph | **Does not exist** | No code references SG adoption | Need SG runner wrapping LI workflows |

**None of the "+ SwarmGraph" modes exist.** The concept is pure fiction in code. The `ComboRuntimeAdapter` is a sequential for-loop — it does not use queen/worker decomposition, voting, consensus, HITL, or audit.

---

## 4. Theia UI/UX Status

### Implemented Views (in `packages/arc-extension/`)
- **ARC Main Widget** (`arc-widget.tsx`): Runtime readiness cards, recent runs list, execution steps, trace viewer, workflow detection — reads from Python daemon/CLI via backend service
- **ProgressBar**: Progress bar component
- **ToastContainer**: Toast notifications with auto-dismiss
- **ShortcutsModal**: Keyboard shortcuts help dialog
- **ExecutionSteps**: Workflow execution progress steps
- **ErrorBanner**: Error display with retry action
- **WorkflowExecutionSection**: Workflow execution UI section
- **TraceViewerSection**: Trace viewer UI section with filtering
- **WorkflowDetectionSection**: Workflow detection UI section

### Partially Wired Views (in `theia-extensions/`)
- **Runtime/Provider Readiness** (`arc-adapters`): Shows adapter detect/run/gate status with DoctorAction suggestions
- **Workflow Graph** (`arc-workflows`): SVG graph layout for exported workflow nodes/edges
- **Schema Inspector** (`arc-schemas`): JSON schema viewer with detail/raw toggle
- **Event Stream** (`arc-event-stream`): SSE event stream viewer with filtering
- **Run Timeline** (`arc-runs`): Chat launcher, timeline, run diff
- **Health** (`arc-health`): Daemon status poller
- **Welcome Widget** (`arc-welcome-widget.tsx`): Getting-started landing page
- **Context Pack** (`arc-context`): Trigger context pack generation
- **Provider Accounts** (`arc-service-impl.ts`): REST endpoints exist but `listProviders()` returns hardcoded data (no daemon routing)
- **Cost Warning** (`cost-warning/`): directory exists
- **Arena** (`arc-arena`): Theia extension with node service impl but backend not wired in `package.json`

### Missing Core UX
- Runtime selection/comparison dropdown (none exists)
- Adapter config UI (set `ARC_CREWAI_EXPORT`, etc.)
- SwarmGraph adoption mode toggle (fiction)
- Live run launch with streaming events (only post-hoc replay via SSE)
- Live event stream during run (SSE is replay-only from stored JSONL)
- Audit viewer (no endpoint exposes audit chain data)
- HITL approval UI (no Theia view for `interrupt` payloads)
- Provider/cost controls (daemon routes exist, no Theia view)
- Workspace/project setup wizard
- Run comparison side-by-side
- Trace/replay with step-through

---

## 5. Fiction List

| Claim | Location | Reality |
|---|---|---|
| "Support for OpenAI Agents SDK" | README L3, L14 | Implementation exists but `run_workflow()` creates a hardcoded `Agent(name="TestAgent")` — it does NOT load actual user workspace agents |
| "Support for LlamaIndex" | README L3 | 38-line detect-only adapter. No `run_workflow()`. Cannot execute any LlamaIndex workflow |
| "ARC Studio uses SwarmGraph as canonical runtime/adoption layer" | README L12-13 | ARC calls SwarmGraph CLI as subprocess; no adapter adopts SwarmGraph engine. "Adoption layer" is a marketing term |
| "$ runtime + SwarmGraph adoption layer" | Product vision | Zero code. ComboRuntimeAdapter is sequential, not SwarmGraph |
| "packages/arc-extension is not used" | README L208 | **FALSE** — confirmed by user as the true extension. Actively maintained, wired into browser app, 239 tests, recent commits |
| "LM Arena with live modes" | `lmarena.py` docstring | All 4 arena modes are 100% stub responses. `ARC_ALLOW_LIVE_ARENA=true` is a fiction — no live provider integration |
| "CLI has 15 commands" | README L142-155 | Commands exist but `eval`, `context` are thin wrappers; `adapter test` runs conformance only; `run` defaults to fixture ID |
| "HMAC-SHA256 audit chain in ARC" | `docs/SECURITY_AUDIT_REPORT.md` | ARC's `audit/chain.py` uses SHA-256 hash chaining (no HMAC secret). HMAC exists only in the vendored SwarmGraph package |
| "ARC can stream live events" | `RUNTIMES.md` streaming section | SSE endpoint (`run_events_sse`) reads stored JSONL traces — replay only. No live streaming channel |
| "AG2 support" | README L163-164 | Code exists but is NOT registered. `arc runtimes` will never show AG2 |
| "Combo runtime = SwarmGraph composition" | `runtime_router.py:ComboRuntimeAdapter` | Sequential for-loop adapter execution. No SwarmGraph concepts |

---

## 6. Underclaimed List

| Feature | Evidence | Current doc claim |
|---|---|---|
| SwarmGraph vendor has full queen/worker/consensus/HITL/audit | `hive-swarm/swarm/nodes/` + `swarm_shared/audit.py` | README understates as "vendored SwarmGraph runtime sub-project" |
| CrewAI adapter has real `importlib` run with timeout/cancellation/paid-gating | `crewai.py:run_workflow()` L119-154 | README says "Adapter implemented" — code is more complete than implied |
| LangGraph adapter has streaming path | `langgraph.py:_stream_graph()` L200-224 | RUNTIMES.md covers it well, but README says "non-streaming run path" — streaming exists |
| `packages/arc-extension` is the true, live, canonical extension | Confirmed by user; wired in `applications/browser/package.json`; 239 tests; recent commits | README L208 says it's "not used" — **incorrect** |
| OTLP telemetry export endpoint | `web/routes.py:export_trace()` L384-413; `telemetry/otlp_exporter.py` | Not mentioned in README or docs |
| 18 REST API endpoints | `web/routes.py:setup_routes()` L558-590 | README only mentions a few CLI commands |
| Provider routing store with persistence | `providers.py:ProviderRoutingStore` | Not highlighted; daemon routes hidden |
| Security profiles with enforce_profile | `security/profiles.py` | Mentioned only briefly |
| ARC audit chain (SHA-256) with SwarmGraphRunner | `audit/chain.py` + `swarmgraph/runner.py` L10-11 | Not documented anywhere |
| AST-based workflow scanning | `swarmgraph.py:_scan_workflow()` L240-290; `langgraph.py:_ast_scan()` L412-476 | RUNTIMES.md mentions it for LangGraph only |

---

## 7. Recommended Roadmap

### P0: Make Truth Coherent and Runnable (1-2 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| Deprecate `theia-extensions/arc-core` | Single canonical extension: `packages/arc-extension` | `theia-extensions/arc-core/`, move any unique functionality to arc-extension | Decision confirmed | `pnpm build` succeeds; all tests pass |
| Register AG2 adapter | `arc runtimes` shows AG2, `arc run` works | `adapters/registry.py:build_default()` | AG2 runner code (exists) | Test with fake AG2 team |
| Fix OpenAI Agents adapter to accept workspace export target | No more hardcoded TestAgent | `openai_agents.py:run_workflow()` | `ARC_OPENAI_EXPORT` env var | Run with fake agents SDK project |
| Remove fiction claims from README | Truthful README | `README.md` | Audit complete | Manual review |
| Flag arena as stub only | No "live mode" fiction | `arena/service.py` docstrings, README | Audit complete | grep for stub markers |

### P1: SwarmGraph Adoption Layer Architecture (2-4 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| Define `SwarmGraphAdoptionRunner` interface | Common interface wrapping any runtime in SG queen/workers | New `adapters/adoption/` package | P0 cleanups | Contract tests for interface |
| Implement SG wrapper for LangGraph | LangGraph graphs run through SG consensus/audit | `adapters/adoption/langgraph_adoption.py` | P1 interface | E2E test with real LangGraph graph through SG |
| Implement SG wrapper for CrewAI | CrewAI crews run through SG consensus/audit | `adapters/adoption/crewai_adoption.py` | P1 interface | E2E test with real CrewAI crew |
| Replace ComboRuntimeAdapter with SG adoption | Combo mode uses queen/worker decomposition | `orchestration/runtime_router.py` | P1 interface | Conformance test |
| Wire SG HMAC audit into ARC | Run records carry HMAC-SHA256 signature | `audit/` package, `swarmgraph/runner.py` | SwarmGraph audit lib | `audit verify` CLI command |

### P2: Runtime + SwarmGraph Integrations (2-3 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| OpenAI Agents + SG adoption | Agents SDK runs through SG | `adapters/adoption/openai_adoption.py` | P1 interface | E2E with fake agents runner |
| AG2 + SG adoption | AG2 teams run through SG | `adapters/adoption/ag2_adoption.py` | P1 interface, P0 AG2 reg | E2E with fake AG2 team |
| LlamaIndex + SG adoption | LI workflows run through SG | `adapters/adoption/llamaindex_adoption.py` | P1 interface | E2E with fake LI workflow |
| Live Arena integration | Arena uses real provider calls | `arena/service.py` live mode | Provider gateway | E2E with real model |

### P3: Theia UX Productization (3-4 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| Runtime selection dropdown | User picks runtime from adapter list | `arc-extension/` widget | P0 extension cleanup | UI test |
| Adapter config panel | Set `ARC_CREWAI_EXPORT` etc from UI | `arc-extension/` config view | P0 extension cleanup | UI test |
| Live event stream view | SSE during run (not replay) | `arc-extension/`, daemon SSE | P0 daemon SSE | E2E with stub run |
| Audit viewer | Browse HMAC audit chain | `arc-extension/` widget | SwarmGraph audit integration | UI test |
| HITL approval dialog | Approve/deny with decision token | `arc-extension/` + daemon SSE | SSE/HITL bridge | E2E with SG HITL |
| Run launch UI | Select workflow, config, launch | `arc-extension/` | P0 extension cleanup | E2E test |

### P4: Audit/Replay/HITL/Security Hardening (2-3 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| HMAC audit viewer | Browse + verify audit chain | `arc-extension/`, `audit/chain.py` | SwarmGraph HMAC | `audit verify` pass |
| Run replay with step-through | Step through run events | `arc-extension/` | Trace persistence | E2E replay test |
| HITL approval via Theia | Interrupt/resume from UI | Daemon SSE, Theia HITL widget | SSE streaming | E2E HITL test |
| Default bearer token auth | All daemon endpoints require token | `web/server.py` | None | Integration test |
| Comprehensive env redaction | All adapter subprocess env filtered | All adapter `_filtered_env()` methods | None | Security conformance test |

### P5: Release Readiness (2-3 weeks)

| Item | Outcome | Files involved | Dependencies | Verification |
|---|---|---|---|---|
| Signed Electron packaging | macOS installer | `applications/electron/` | Signing env vars | `pnpm package:electron` |
| E2E test suite | Real runtime execution tests | `tests/e2e/` | P1-P4 implementations | CI passes |
| Truthful README + docs | No fiction claims | `README.md`, `docs/` | All P0-P4 | Manual doc audit |
| Release checklist + CI | Tagged release build | `.github/workflows/` | All dependencies | CI passes |

---

## 8. README Rewrite Plan

### Structure Outline
1. **What ARC Studio Is** — Python CLI + daemon with optional Theia shell
2. **Quick Start** — `uv run arc --help`, `uv run arc serve`
3. **CLI Reference** — Accurate command table
4. **Runtime Adapters** — Separate "standalone" and "+ SwarmGraph" tables
5. **Theia Shell** — Optional browser/Electron GUI; note `packages/arc-extension` is the canonical extension
6. **Architecture** — CLI → daemon → adapters + SwarmGraph (vendored)
7. **Status** — Pre-alpha, NOT production ready
8. **Security** — Loopback only, optional bearer token
9. **Development** — Build, test, contribute

### Claims Safe to Make
- "ARC Studio is a Python CLI and daemon for inspecting, running, and debugging agent workflows"
- "Supports standalone execution via adapters for: SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK (partial), AG2 (pending registry)"
- "SwarmGraph is vendored as an in-repo runtime with queen/worker orchestration, consensus, HITL, HMAC audit chain, and provider gateway"
- "LlamaIndex: detection only"
- "LM Arena: stub/test mode only"
- "Trace visualization via Theia shell (optional); `packages/arc-extension` is the primary Theia extension"
- "All runtime execution is gated behind environment variables and paid-call flags"
- "Pre-release v0.1.0-alpha. No API stability guarantees."
- "No telemetry. Loopback-only by default."

### Claims to Remove/Change
- "Adoption layer for all runtimes" → not implemented
- "OpenAI Agents SDK full support" → partial, hardcoded agent
- "LlamaIndex support" → detection only
- "AG2 support" → not registered
- "`packages/arc-extension` not used" → **FALSE** — it IS the canonical extension
- "HMAC-SHA256 audit" → ARC hash chain only, HMAC in SG package
- "Live streaming" → replay only
- "15 CLI commands" → 9-10 are real, rest are thin
