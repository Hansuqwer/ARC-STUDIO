# ARC Studio — Full Repo Reality Audit

Generated: 2026-05-14; truth notes refreshed 2026-05-18 against locked status docs and release smoke wording.

> **Prerequisite decision confirmed**: `packages/arc-extension` is the true/canonical Theia extension. It is wired into the browser app, has 581 tests in the canonical extension suite, recent commits, and active DI bindings. Legacy `theia-extensions/*` source directories are archived under `docs/archive/theia-extensions/`; they are unwired from browser/electron apps, root typecheck, and the pnpm workspace. This audit is historical unless a row is explicitly refreshed below.

---

## 1. Executive Summary

1. **ARC Studio is a Python CLI + local aiohttp daemon, NOT a real IDE.** The Theia shell exists (12 extensions, meaningful widget code) but talks to the Python daemon via JSON-RPC or CLI subprocess. There is no embedded Python runtime in the Theia process.

2. **There is one live Theia extension path for release scope.** `packages/arc-extension` is canonical. Legacy `theia-extensions/*` source dirs are archived for rollback/history but are not workspace-active or app-wired.

3. **SwarmGraph (vendored in `runtimes/swarmgraph/`) is a real, working runtime.** It has queen/worker graph, 3-protocol consensus, HITL/interrupt, HMAC-SHA256 audit chain, multi-provider gateway (12 providers), quota, replay safety, deterministic orchestration. But ARC does NOT use it as a shared "adoption layer" for other runtimes. ARC calls it only as a CLI subprocess (`swarmgraph swarm --json`).

4. **Refresh 2026-05-17:** fake-tested/gated SwarmGraph adoption runners now exist for LangGraph, AG2, CrewAI, OpenAI Agents, and LlamaIndex. Only `crewai+swarmgraph` is currently exposed as a CLI fake/offline path; do not claim broad live/provider-backed adoption.

5. **CrewAI and OpenAI Agents adapters have real runtime execution code** (not just mocks). Both can import the real library, resolve workspace exports, run workflows, and return RunRecords. However `export_workflow()` returns only a single static node (`_static.py:static_workflow`). No graph extraction.

6. **Refresh 2026-05-17:** AG2 is registered/gated in current runtime capability reporting; real dependency/runtime paths remain gated.

7. **The LM Arena adapter and service are stub-default with a gated live path.** All four modes (battle/direct/code/agent-arena-preview) return canned stub text. There is zero live LLM integration. `ARC_ALLOW_LIVE_ARENA=true` gates nothing real in the current v0.1 code.

8. **The "combo runtime adapter" exists** but only runs adapters sequentially (not SwarmGraph composition). It's a for-loop calling each adapter's `run_workflow` in order. No queen/worker decomposition, no voting, no consensus.

9. **Default test coverage is unit/contract/mock/offline.** An opt-in real-runtime smoke suite exists for release validation, including vendored SwarmGraph imports and a narrow `langgraph+swarmgraph` local-real fixture path. It requires explicit env flags, performs no provider/paid calls, and is not evidence for broad provider-backed adoption.

10. **Security:** no auth by default (optional bearer token via `ARC_DAEMON_TOKEN`), subprocess env redaction exists, ARC adapter run paths generally use SHA-256 audit chains, and a separate keyed-audit CLI/key-management path exists. Do not claim concurrent-user readiness or adapter-wide keyed audit without run-specific evidence.

---

## 2. Implementation Reality Table

| Area | Intended | Actual | Status | Evidence | Gap |
|---|---|---|---|---|---|
| **Product identity** | Eclipse Theia IDE + Python backend | Python CLI/daemon with Theia shell frontend | Partial | README L3; `web/server.py` L1-5; 12 theia-extensions | Theia is a thin UI overlay, not the primary product |
| **Extension split** | Single extension path | `packages/arc-extension` is the only release-wired extension path; legacy `theia-extensions/*` source archived outside workspace | Resolved for v0.1 | `applications/browser/package.json` and `applications/electron/package.json` depend on `arc-extension`; `pnpm-workspace.yaml` excludes legacy extensions | Delete archive later only if rollback/history no longer needed |
| **SwarmGraph vendored** | In-repo canonical runtime | 3-package monorepo with full queen/worker/consensus/HITL/audit | Implemented | `runtimes/swarmgraph/packages/`; `hive-swarm/swarm/nodes/consensus.py`; `swarm_shared/audit.py` | Full, not partial |
| **SwarmGraph as adoption layer** | All runtimes run through SwarmGraph | Fake-tested/gated adoption runners exist; CLI routing is currently limited to `crewai+swarmgraph` fake/offline path | Partial/scaffolded | `adoption/`; `runtime_router.py` | Broad live/provider-backed adoption remains not a v0.1 product claim |
| **SwarmGraph audit in ARC** | HMAC-SHA256 signed audit chain | ARC adapter paths generally use SHA-256 chains; HMAC audit/key CLI path exists separately | Partial | `audit/chain.py`; `audit/hmac_chain.py`; `audit/key_manager.py`; `arc audit verify/export/key` | Adapter-wide HMAC audit population still needs verification |
| **LangGraph adapter** | Full detection + run + stream | Real `importlib` run, AST fallback, streaming fallback | Implemented | `langgraph.py` L159-198 real run; L200-224 stream impl | No live streaming into ARC traces |
| **CrewAI adapter** | Full detection + run + graph | Real `importlib` run, static workflow export, paid-call gating | Partial | `crewai.py` L119-154 real run; L113-117 static export | Graph extraction missing; static export only |
| **OpenAI Agents adapter** | Detection + run + stream | Workspace export target/fake-tested gated path; static export remains limited | Partial | `adapters/openai_agents.py` | No broad live provider claim |
| **AG2 adapter** | Registered + runnable | Registered/gated path exists | Partial | `adapters/ag2/` | Real dependency/runtime path gated |
| **LlamaIndex adapter** | Detection + export/run/adoption scaffold | Fake-tested/gated adapter/adoption path exists | Partial | `adapters/llamaindex.py`; `adoption/` | No broad live provider claim |
| **LM Arena adapter** | Live provider comparison | 100% stub responses | Static | `arena/service.py` L78-150 `_stub_battle/direct/code/agent_preview` | No real LLM calls |
| **Combo adapter** | SwarmGraph composition | Sequential for-loop, no composition | Static | `runtime_router.py:ComboRuntimeAdapter` L42-101 | Not adoption; not SwarmGraph |
| **Theia UI** | Full runtime cockpit | Tabbed canonical extension with Chat/Runs/Workflows/Config plus ported adapters, workflow graph, run timeline, event stream, assurance, and SwarmGraph insight views | Partial | `packages/arc-extension/src/browser/`; locked docs | Active-run SSE bridge still disconnected; provider/cost setup UX remains limited |
| **Python daemon** | Full REST API | REST/SSE endpoints, CORS, optional bearer auth | Implemented | `web/routes.py`; `web/server.py` | Stored-trace SSE/replay exists; active-run SSE wiring in IDE remains a known gap |

---

## 3. Runtime Matrix

### Standalone Runtimes

| Runtime | Can detect | Can inspect/export | Can run | Can stream | Can audit/replay | Status | Evidence |
|---|---|---|---|---|---|---|---|
| SwarmGraph | YES (heuristic) | YES (AST + fixture fallback) | YES (CLI subprocess) | NO | NO (ARC audit, not SG HMAC) | Implemented | `swarmgraph.py` L187-227 detect; L229-290 export; L292-404 run |
| LangGraph | YES (dep check) | YES (real import, AST, fixture) | YES (importlib) | YES (fallback) | NO | Implemented | `langgraph.py` L246-280 detect; L282-498 export; L159-198 run; L200-224 stream |
| CrewAI | YES (dep check) | Static only (1 node) | YES (importlib) | NO | NO | Partial | `crewai.py` L103-111 detect; L113-117 static export; L119-154 run |
| OpenAI Agents | YES (dep check) | Static only (1 node) | YES via workspace export target/fake-tested gated path | NO | ARC trace/audit only unless HMAC material exists | Partial | `adapters/openai_agents.py` |
| AG2 | YES (modular code) | Static only | Gated/fake-tested path | NO | ARC trace/audit only unless HMAC material exists | Partial | `adapters/ag2/` |
| LlamaIndex | YES (dep check) | Static only (1 node) | Gated/fake-tested path | NO | ARC trace/audit only unless HMAC material exists | Partial | `adapters/llamaindex.py` |

### "+ SwarmGraph Adoption Layer" Runtimes

| Runtime + SG | Current status | Evidence | Gap to vision |
|---|---|---|---|
| CrewAI + SwarmGraph | Fake/offline CLI path exists | `crewai+swarmgraph` route; fake adapter emits trace events with `real_provider_call=false` | Real provider-backed adoption remains gated/not claimed |
| LangGraph + SwarmGraph | Runner exists; not broadly productized | `adoption/` | CLI/router product path needs explicit wiring/verification before release claim |
| OpenAI Agents + SwarmGraph | Runner exists; fake-tested/gated | `adoption/` | No broad live provider claim |
| AG2 + SwarmGraph | Runner exists; fake-tested/gated | `adoption/` | Real dependency/runtime path gated |
| LlamaIndex + SwarmGraph | Runner exists; fake-tested/gated | `adoption/` | No broad live provider claim |

**Refresh 2026-05-17:** `+swarmgraph` adoption scaffolds/runners exist, with `crewai+swarmgraph` exposed as a fake/offline CLI path. `ComboRuntimeAdapter` remains sequential and is not SwarmGraph adoption.

---

## 4. Theia UI/UX Status

### Implemented Views (in `packages/arc-extension/`)
- **ARC Studio Widget** (`arc-studio-widget.tsx`): Canonical tabbed shell with Chat, Runs, Workflows, and Config tabs.
- **Legacy ARC Widget** (`arc-widget.tsx`): Retained/marked legacy; runtime readiness, recent runs, execution steps, trace viewer, workflow detection.
- **Runs tab**: Run list basics plus audit-chain verification, replay events, and pending HITL approve/reject basics.
- **Chat tab**: Runtime/profile selectors plus explicit fake/offline run launch path for supported safe modes.
- **Config tab**: Backend-backed config status/save basics.
- **Ported views**: Adapters, workflow graph, run timeline, event stream, assurance, and SwarmGraph insight views live under `packages/arc-extension`.
- **Shared components**: Progress, toast, shortcuts, execution steps, errors, workflow execution, trace viewer, workflow detection, and related reusable UI pieces.

### Legacy Views (source retained, not wired)
- Legacy `theia-extensions/*` source dirs are archived under `docs/archive/theia-extensions/` for rollback/history only and are not active in browser/electron apps, root typecheck, or the pnpm workspace.
- Release-scope views ported into `packages/arc-extension` include adapters, workflow graph, run timeline, event stream, health, status/welcome, chat launch UI, and run diff UI/service.
- `arc-context`, `arc-schemas`, and `arc-arena` remain legacy/out-of-scope source references unless intentionally ported later.

### Missing Core UX
- Rich adapter setup UX for env/export targets remains limited.
- Broad SwarmGraph adoption product mode remains fake-tested/gated, not a live/provider-backed UI claim.
- Active-run streaming remains incomplete: `streamActiveTrace()` reports disconnected for live streams even when a base URL exists; SwarmGraph Insight can ask for a base URL manually.
- Stored trace replay/event viewing exists; do not describe it as live active-run SSE.
- Dedicated audit/HITL workspaces remain deferred; Runs tab exposes basic audit verification and pending HITL actions.
- Provider/cost controls remain explicit opt-in/gated; no paid/provider calls are default.
- Workspace/project setup wizard
- Run comparison side-by-side
- Trace/replay with step-through

---

## 5. Fiction List

| Claim | Location | Reality |
|---|---|---|
| "Support for OpenAI Agents SDK" | README L3, L14 | Current support is workspace-export/fake-tested/gated; no broad live provider claim |
| "Support for LlamaIndex" | README L3 | Current support is fake-tested/gated; no broad live provider claim |
| "ARC Studio uses SwarmGraph as canonical runtime/adoption layer" | README L12-13 | ARC calls SwarmGraph CLI as subprocess; no adapter adopts SwarmGraph engine. "Adoption layer" is a marketing term |
| "$ runtime + SwarmGraph adoption layer" | Product vision | Scaffolds/runners exist, but broad live/provider-backed adoption is not a v0.1 product claim. ComboRuntimeAdapter is sequential, not SwarmGraph |
| "packages/arc-extension is not used" | Historical README wording | **FALSE** — confirmed as the true extension. Actively maintained, wired into browser app, 563 canonical extension tests, recent commits |
| "LM Arena with live modes" | `lmarena.py` docstring | All 4 arena modes are 100% stub responses. `ARC_ALLOW_LIVE_ARENA=true` is a fiction — no live provider integration |
| "CLI has 15 commands" | README L142-155 | Commands exist but `eval`, `context` are thin wrappers; `adapter test` runs conformance only; `run` defaults to fixture ID |
| "HMAC-SHA256 audit chain in ARC" | `docs/SECURITY_AUDIT_REPORT.md` | ARC has `audit/hmac_chain.py` + key manager + CLI verify/export/key path, but adapter-wide run paths generally still use SHA-256 chains unless HMAC material is explicitly written |
| "ARC can stream live events" | `RUNTIMES.md` streaming section | Stored-trace SSE/replay exists, but active-run IDE streaming remains disconnected (`streamActiveTrace()` returns disconnected for live requests). No broad live active-run stream claim |
| "AG2 support" | README L163-164 | AG2 is registered/gated; real dependency/runtime execution remains gated |
| "Combo runtime = SwarmGraph composition" | `runtime_router.py:ComboRuntimeAdapter` | Sequential for-loop adapter execution. No SwarmGraph concepts |

---

## 6. Underclaimed List

| Feature | Evidence | Current doc claim |
|---|---|---|
| SwarmGraph vendor has full queen/worker/consensus/HITL/audit | `hive-swarm/swarm/nodes/` + `swarm_shared/audit.py` | README understates as "vendored SwarmGraph runtime sub-project" |
| CrewAI adapter has real `importlib` run with timeout/cancellation/paid-gating | `crewai.py:run_workflow()` L119-154 | README says "Adapter implemented" — code is more complete than implied |
| LangGraph adapter has streaming path | `langgraph.py:_stream_graph()` L200-224 | RUNTIMES.md covers it well, but README says "non-streaming run path" — streaming exists |
| `packages/arc-extension` is the true, live, canonical extension | Confirmed by user; wired in `applications/browser/package.json`; 563 canonical extension tests; recent commits | Current README correctly treats it as canonical |
| OTLP telemetry export endpoint | `web/routes.py:export_trace()` L384-413; `telemetry/otlp_exporter.py` | Not mentioned in README or docs |
| 18 REST API endpoints | `web/routes.py:setup_routes()` L558-590 | README only mentions a few CLI commands |
| Provider routing store with persistence | `providers.py:ProviderRoutingStore` | Not highlighted; daemon routes hidden |
| Security profiles with enforce_profile | `security/profiles.py` | Mentioned only briefly |
| ARC audit chain (SHA-256) with SwarmGraphRunner | `audit/chain.py` + `swarmgraph/runner.py` L10-11 | Not documented anywhere |
| AST-based workflow scanning | `swarmgraph.py:_scan_workflow()` L240-290; `langgraph.py:_ast_scan()` L412-476 | RUNTIMES.md mentions it for LangGraph only |

---

## 7. Historical Roadmap Snapshot

This section is retained as historical audit context from 2026-05-14. Many items below are now complete, scaffolded, or explicitly deferred; use `docs/LOCKED_REMAINING_ROADMAP.md` and `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md` for current ordered work.

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
- "Supports standalone execution via adapters for: SwarmGraph, LangGraph, CrewAI, OpenAI Agents SDK (workspace export/gated), AG2 (registered/gated), LlamaIndex (gated)"
- "SwarmGraph is vendored as an in-repo runtime with queen/worker orchestration, consensus, HITL, HMAC audit chain, and provider gateway"
- "LlamaIndex: gated/fake-tested path; no broad live provider claim"
- "LM Arena: stub/test mode only"
- "Trace visualization via Theia shell (optional); `packages/arc-extension` is the primary Theia extension"
- "Provider-backed or paid-call execution is opt-in/gated; offline/fake/local-real smoke paths are the defaults for release validation"
- "Pre-release v0.1.0-alpha. No API stability guarantees."
- "No telemetry. Loopback-only by default."

### Claims to Remove/Change
- "Adoption layer for all runtimes" → fake-tested/gated runners exist; broad live/provider-backed support is not a v0.1 claim
- "OpenAI Agents SDK full support" → workspace-export/gated path only; no broad live provider claim
- "LlamaIndex support" → gated/fake-tested path only; no broad live provider claim
- "AG2 support" → registered/gated; real dependency/runtime path gated
- "`packages/arc-extension` not used" → **FALSE** — it IS the canonical extension
- "HMAC-SHA256 audit" → adapter paths generally use ARC SHA-256 chains; keyed CLI audit path exists separately
- "Live streaming" → stored-trace replay exists; active-run IDE stream still disconnected
- "15 CLI commands" → 9-10 are real, rest are thin
