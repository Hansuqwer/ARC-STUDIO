---
date: 2026-05-22
commit: b65f57e
source_research_doc: docs/research/adapter-priorities.md
status: DRAFT — ordering based on composite scores from research doc; reconcile against fresh grep.app counts before treating as source of truth
pinned_versions:
  langchain: ">=0.3,<2.0"
  anthropic_sdk: ">=0.104,<1.0"
  openai_sdk: ">=1.55,<3.0"
  haystack_ai: ">=2.29,<3.0"
  semantic_kernel: ">=1.42,<2.0"
  dspy: ">=3.2,<4.0"
  pydantic_ai: ">=1.99,<2.0"
  smolagents: ">=1.0,<2.0"
  google_adk: ">=2.0,<3.0"
  mcp_python_sdk: ">=1.27,<2.0"
next_review_date: 2026-07-22
---

# ARC Studio Adapter Roadmap — Phases 26–35

This roadmap turns the prioritized top-10 adapter list into ten sequential phases (26–35), each delivering one adapter to **Baseline Complete** via a Detection / Export / Live-Streaming PR series. It assumes Phases 23–25 are Baseline Complete; if they are not, Phase 26 is gated on their completion. A prep phase (25.5) lands the shared test harness and `ProviderClient` interface that every later phase depends on.

The roadmap inherits every constraint already established in earlier phases: fail-closed enforcement (Phase 23), TypedRunEvent conformance (Phase 22 + ADR-0022.1), HMAC-signable streaming traces (Phase 21), no banned claims (`scripts/check-banned-claims.sh`), offline-first tests, and additive `extras` dependencies.

## Roadmap Overview

| Phase | Adapter | Composite (0–9) | Tier scope | Est. PRs | Dependencies |
|-------|---------|-----------------|------------|---------:|--------------|
| 25.5 | Prep: harness + ProviderClient | n/a | n/a | 2 | Phases 23, 24, 25 Baseline Complete |
| 26 | LangChain | 8 | T1+T2+T3 | 3 | 25.5 |
| 27 | Anthropic SDK (ProviderClient impl) | 8 | T1+T3 | 2 | 25.5 |
| 28 | OpenAI-compatible provider (consolidated) | 8 | T1+T3 | 2 | 25.5, 27 |
| 29 | Pydantic AI | 8 | T1+T2+T3 | 3 | 25.5, 28 |
| 30 | DSPy | 7 | T1+T2+T3 | 3 | 25.5, 28 |
| 31 | Haystack | 7 | T1+T2+T3 | 3 | 25.5, 28 |
| 32 | Smolagents | 6 | T1+T2+T3 | 3 | 25.5, ADR-0022.1, 28 |
| 33 | Semantic Kernel | 6 | T1+T2 only | 2 | 25.5 |
| 34 | Google ADK | 6 | T1+T2+T3 | 3 | 25.5, 28 |
| 35 | MCP Python SDK | 6 | T1+T3 | 2 | 25.5, ADR-0022.1, ≥3 framework adapters (≥Phase 31) |

**Tier definitions:** T1 Detection = `arc runtimes list` reports the adapter without executing user code. T2 Export = ARC produces a deterministic run-plan JSON from a fixture project without executing it. T3 Live streaming = ARC runs the adapter under `EnforcementContext` and emits TypedRunEvent events conforming to the Phase 22 discriminated union.

## Prep Phase 25.5 — Shared Test Harness and ProviderClient Interface

**Status:** Not Started. **Dependencies:** Phases 23, 24, 25 Baseline Complete. **Goal:** Land the infrastructure every adapter phase depends on.

### Goal statement

Deliver a shared test harness under `python/tests/adapters/_shared/` and a `ProviderClient` interface under `python/src/agent_runtime_cockpit/providers/`. Out of scope: any adapter implementation, any change to enforcement helpers, any change to TypedRunEvent shapes.

### PR 25.5.1 — Shared adapter test harness

Files: `python/tests/adapters/_shared/` containing:
- `TypedRunEventConformance` — asserts an event stream's variants are all members of the Phase 22 discriminated union
- `FakeProviderFixture` — deterministic token/tool-call/error streams using existing fake-provider infra
- `FixtureProjectLoader` — context-manager that materializes a synthetic project on disk and tears it down
- `GoldenFileCompare` — diffs JSON run-plans with stable key ordering
- `DenialEventAssertions` — asserts a specific typed denial event fires under a given EnforcementContext

The harness must be import-light (no adapter dependencies) and usable without network access.

### PR 25.5.2 — ProviderClient interface

Files: `python/src/agent_runtime_cockpit/providers/client.py` defining a `ProviderClient` Protocol with methods for synchronous completion, streamed completion, tool-call streaming, and capabilities introspection. Registry at `providers/registry.py`. No concrete implementation lands in this PR.

**Exit gate:** Both PRs merged, harness imported by at least one non-`_shared/` test, `providers.registry.known()` returns empty without raising.

---

## Phase 26 — LangChain

**Composite:** 8/9 (Adoption 3, Ecosystem fit 3, Integration cost 2). **Pinned upstream:** langchain >=0.3,<2.0. **Dependencies:** 25.5. **Status:** ✅ COMPLETE (T1: 6beedf8, T2: ea567cf, T3: 7566e60).

### Goal

Enable detection, export, and live streaming for LangChain `Runnable`/LCEL pipelines under ARC's Phase 21–23 invariants. Out of scope: `AgentExecutor`, ReAct loops, and any agent surface that LangChain itself now redirects to LangGraph.

### PR 26.1 — Detection ✅ COMPLETE

Add `adapters/langchain/{__init__.py,detect.py,capabilities.py}`. Import-only probe reports installed version, presence of `langchain_core`, `langchain_community`, and importable provider integrations. Wire into `arc runtimes list` with type `framework`. 8 tests minimum.

**Status:** Complete (commit 6beedf8). Evidence: 15 tests passing, all adapter tests green (88/88). Detection covers langchain/core/community packages, 9 provider integrations, workspace scanning, confidence scoring.

### PR 26.2 — Export ✅ COMPLETE

Add `export.py` that AST-walks the workspace for `Runnable` compositions. Static extraction of `|` operator on `Runnable` subclasses. No execution of user code in-process; dynamic-resolution fallback spawns sandboxed subprocess gated by `enforce_shell_gate`. Two fixture projects: trivial chain + retrieval pipeline. 10 tests minimum.

**Status:** Complete (commit ea567cf). Evidence: 15 tests passing, AST-based chain detection, 2 fixture projects, WorkflowInfo conversion.

### PR 26.3 — Live streaming ✅ COMPLETE

Add `runner.py` with `ARCCallbackHandler(BaseCallbackHandler)` subscribing to `on_chain_start/end`, `on_llm_start/token/end`, `on_tool_start/end`. Provider calls route through `ProviderClient` registry. Unrecognized LLM emits `POLICY_BYPASS_WARNING` with `bypass_reason=UNKNOWN_PROVIDER_PLUGIN`. 12 tests minimum.

**Status:** Complete (commit 7566e60). Evidence: 17 tests passing, callback handler implementation, policy bypass warnings, event streaming.

**Known risk:** LangChain API churn between minor versions — pin floor and re-verify at each PR.

---

## Phase 27 — Anthropic SDK (first ProviderClient implementation)

**Composite:** 8/9 (Adoption 3, Ecosystem fit 3, Integration cost 2). **Pinned upstream:** anthropic >=0.104,<1.0. **Dependencies:** 25.5.2. **Status:** Not Started.

### Goal

Provide a concrete `ProviderClient` implementation backed by the Anthropic Python SDK. Out of scope: vendoring Anthropic-specific UI; building a "best provider" selector; Bedrock or Vertex routing.

### PR 27.1 — Detection

Probe `anthropic` import, report SDK version and capability flags (streaming, tool-use, prompt caching). Wire into `arc runtimes list` as a *provider* (distinct from *runtime*). 6–8 tests.

### PR 27.3 — Live streaming

Implement `AnthropicProviderClient(ProviderClient)`. Stream messages and tool-use events to TypedRunEvent. Every network call wrapped by `enforce_network_gate`; every billable call by `enforce_paid_call_gate`. Record/replay fixtures under `tests/fixtures/providers/anthropic/`. 12–15 tests.

**Known risk:** API key handling — source only via env or secrets path, never CLI args.

---

## Phase 28 — OpenAI-Compatible Provider Adapter (Consolidated)

**Composite:** 8/9. **Pinned upstream:** openai >=1.55,<3.0. **Dependencies:** 25.5.2, 27. **Status:** Not Started.

### Goal

One adapter that speaks the OpenAI chat-completions wire format and routes to OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp servers via configurable base URLs. Both Responses API and Chat Completions API surfaces. Out of scope: Assistants API, Realtime API.

### PR 28.1 — Detection

Probe `openai` import, enumerate configured base URLs from environment/config, report each as a logical provider in `arc runtimes list`. Detection must not perform network probes. 6–8 tests.

### PR 28.3 — Live streaming

Implement `OpenAICompatibleProviderClient(ProviderClient)` with `base_url` parameter. Per-vendor allowlist records which surface (Responses/Chat Completions) each vendor implements. Record/replay fixtures per vendor. 15–20 tests.

**Known risk:** Vendor deviations from OpenAI shape (e.g., Groq tool-call quirks, Together reasoning models) — per-vendor compatibility tests and allowlist policy.

---

## Phase 29 — Pydantic AI

**Composite:** 8/9 (Adoption 2, Ecosystem fit 3, Integration cost 3). **Pinned upstream:** pydantic-ai >=1.99,<2.0. **Dependencies:** 25.5, 28. **Status:** Not Started.

### Goal

Detection, export, and live streaming for Pydantic AI agents. The event model is Pydantic-native and maps cleanly to Types that ARC Studio already validates with.

### PR 29.1 — Detection

Probe `pydantic_ai`, report version and configured model providers. 6–8 tests.

### PR 29.2 — Export

Discover Pydantic AI `Agent` definitions in workspace. Emit run plan capturing tools, structured-output schemas, model bindings. Two fixtures: single-agent structured-output, multi-tool agent. 10 tests.

### PR 29.3 — Live streaming

Subscribe to Pydantic AI's run-event interface, translate to TypedRunEvent. Validation errors must surface as typed event variant. 12 tests.

**Known risk:** Pre-2.0 — API may change. Pin floor and contract-test failures detect shape changes.

---

## Phase 30 — DSPy

**Composite:** 7/9. **Pinned upstream:** dspy >=3.2,<4.0. **Dependencies:** 25.5, 28. **Status:** Not Started.

### Goal

Detection, export, and live streaming for DSPy programs. Compile step (prompt optimization) surfaced as distinct lifecycle event.

### PR 30.1 — Detection

Probe `dspy`, report version and importable optimizers. 6–8 tests.

### PR 30.2 — Export

Discover `dspy.Module` subclasses, emit run plan capturing signatures and modules. Three fixtures: CoT, ReAct, RAG. 10 tests.

### PR 30.3 — Live streaming

Instrument `Predict` and `Module.__call__` to emit TypedRunEvent. Compile-time vs run-time events distinguishable. 12 tests.

**Known risk:** Compile step can call paid providers many times — paid-call gate per call, documented cost warning.

---

## Phase 31 — Haystack

**Composite:** 7/9. **Pinned upstream:** haystack-ai >=2.29,<3.0. **Dependencies:** 25.5, 28. **Status:** Not Started.

### Goal

Detection, export, and live streaming for Haystack 2.x pipelines. Pipeline DAG maps to ARC run-plan concept.

### PR 31.1 — Detection

Probe `haystack`, report version, list discoverable components. 6–8 tests.

### PR 31.2 — Export

Discover Haystack `Pipeline` instances, emit run plan capturing component DAG, I/O connections. Two fixtures: RAG pipeline, routing pipeline. 10 tests.

### PR 31.3 — Live streaming

Subscribe to Haystack tracing/callback infrastructure, emit TypedRunEvent per component invocation. 12 tests.

**Known risk:** Component observability inconsistent. Document which built-in components are fully vs partially observable.

---

## Phase 32 — Smolagents

**Composite:** 6/9. **Pinned upstream:** smolagents >=1.0,<2.0. **Dependencies:** 25.5, ADR-0022.1, 28. **Status:** Not Started.

### Goal

Detection, export, and live streaming for smolagents `CodeAgent` and `ToolCallingAgent`. **Highest-risk adapter.** Code execution as action.

### Critical upstream finding

Smolagents upstream states: "The built-in `LocalPythonExecutor` is **not a security sandbox**." Fox-IT and huntr.com have documented exploits. `LocalPythonExecutor` is **rejected by default**. Users opt in via `--allow-unsandboxed-shell` which surfaces the upstream warning verbatim.

### PR 32.1 — Detection

Probe `smolagents`, report version and configured executor backends. Each backend assigned a matrix classification (sandbox / not-a-sandbox / experimental). 8 tests.

### PR 32.2 — Export

Discover agent definitions, emit run plan including executor backend and tool list. `sandbox_backend` field required; absence of explicit backend emits `sandbox_backend: "LocalPythonExecutor"` + `sandbox_warning`. 10 tests.

### PR 32.3 — Live streaming

Subscribe to memory steps. Every executor invocation passes through `enforce_shell_gate`. Unrecognized `Model` subclass emits `POLICY_BYPASS_WARNING`. Sandboxed backends (Docker, E2B, Modal) at T3; experimental (Blaxel, Pyodide) T1+T2 only. 12 tests.

**Exit gate:** Mandatory architecture review sign-off required (the only phase besides Phase 35 with this requirement).

---

## Phase 33 — Semantic Kernel

**Composite:** 6/9. **Pinned upstream:** semantic-kernel >=1.42,<2.0. **Dependencies:** 25.5. **Status:** Not Started. **Tier:** T1+T2 only.

### Goal

Detection and export only. T3 deferred because Python SDK churn makes live streaming uneconomical. Revisit at next-review date.

### PR 33.1 — Detection

Probe `semantic_kernel`, report version and importable features. 6–8 tests.

### PR 33.2 — Export

Discover SK `Kernel` and plugin definitions, emit run plan capturing plugins, planners, connectors. Two fixtures covering common patterns. 10 tests.

**Exit gate:** T3 deferral documented with upstream-version reasoning cited.

---

## Phase 34 — Google ADK

**Composite:** 6/9. **Pinned upstream:** google-adk >=2.0,<3.0. **Dependencies:** 25.5, 28. **Status:** Not Started.

### Goal

Detection, export, and live streaming for Google ADK 2.0 agents. Out of scope: Vertex AI provider routing beyond OpenAI-compatible base URL; ADK UI tooling.

### PR 34.1 — Detection

Probe `google.adk`, report version. Refuse ADK 1.x as unsupported. 6–8 tests.

### PR 34.2 — Export

Discover ADK `Agent` definitions, emit run plan capturing agents, tools, sub-agent topology. Multi-agent fixture required. 10 tests.

### PR 34.3 — Live streaming

Subscribe to ADK event interface. Provider calls route through `ProviderClient`. 12 tests.

**Known risk:** ADK 2.0 breaking changes from 1.x. Contract test fails on 3.0 emergence.

---

## Phase 35 — MCP Python SDK

**Composite:** 6/9. **Pinned upstream:** mcp >=1.27,<2.0. **Dependencies:** 25.5, ADR-0022.1, ≥Phase 31. **Status:** Not Started.

### Goal

Detection and live streaming for MCP client. ARC Studio consumes MCP servers as external capability providers. Out of scope: serving MCP from ARC; MCP authorization beyond per-server consent.

### Transport support matrix

| Transport | Status | Gate |
|-----------|--------|------|
| stdio | Stable | `enforce_shell_gate` |
| Streamable HTTP | Stable (supersedes SSE) | `enforce_network_gate` + lifetime cap |
| SSE | **Deprecated** | `enforce_network_gate` + `POLICY_BYPASS_WARNING` |

### PR 35.1 — Detection

Probe `mcp`, enumerate configured MCP servers from ARC config only (not workspace files). Compute stable `server_id` per server via SHA-256 of (command, args, transport). Report each in `arc runtimes list --type mcp-server`. 10 tests.

### PR 35.3 — Live streaming

Three transport runners, each with appropriate enforcement. Event mapping reuses existing TypedRunEvent variants (RunStart, ToolStart, ToolEnd, etc.) — no union extension. In-process fake server for offline tests. Per-server allow gesture required. 12–15 tests.

**Exit gate:** Mandatory architecture review sign-off. No new TypedRunEvent variants; union extension would require ADR before merge.

---

## Cross-Cutting Workstreams

### 1. Shared adapter test harness

Lives at `python/tests/adapters/_shared/`. Landed in Phase 25.5. Every new adapter phase adds at most one helper; new helpers require ADR.

### 2. Consolidated OpenAI-compatible provider

Phase 28 absorbs 5 potential individual provider phases. Vendor allowlist is the contract; adding a vendor requires fixture + passing test.

### 3. Unified ProviderClient interface

Defined Phase 25.5, implemented Phase 27 (Anthropic) and Phase 28 (OpenAI-compatible). Contract test with subprocess-level network monitor runs against every registered implementation.

### 4. Runtime support matrix in CI

`scripts/generate-runtime-table.sh` fails CI if a previously-detected adapter regresses. Capability-flag changes require ADR.

---

## Sequencing Rationale

Phase 25.5 lands infrastructure first. Phase 26 (LangChain) leads framework adapters due to dominant adoption. Phases 27–28 land ProviderClient implementations early. Phases 29–31 cluster next-tier frameworks (Pydantic AI, DSPy, Haystack) in composite-score order. Phase 32 (Smolagents) late in cluster because code-execution surface needs enforcement maturity. Phase 33 (Semantic Kernel) late with T1+T2 only. Phase 34 (Google ADK) sequenced after ProviderClient matures. Phase 35 (MCP) last — trust posture is most subtle, benefits from lessons learned in all nine prior phases.

---

## Risk Register

| # | Risk | Mitigation |
|---|------|------------|
| 1 | Upstream SDK breaking change between planning and PR 3 | Version pin; contract tests fail loudly; refresh via context7 at each PR start |
| 2 | Fake provider doesn't cover all TypedRunEvent variants | Record/replay fixtures supplement fake provider |
| 3 | Smolagents code-execution gate disabled by users | Loud denial dialog; risk-led documentation; `--allow-unsandboxed-shell` flag verbiage |
| 4 | MCP server treated as in-process trust boundary | Per-server allow gesture required; docs lead with trust model |
| 5 | ProviderClient over-fits to OpenAI shape | Interface derived from Anthropic + OpenAI before freezing; ADR required to extend |
| 6 | TypedRunEvent union pressure (each adapter wants new variant) | Phase-22 amendment ADR required; default is map onto existing variants |
| 7 | Extras-group dependency creeps into core install | CI check on core-install footprint; extras remain optional |
| 8 | Documentation drift across adapter doc, README, phases.md | Ledger row update in exit gate; README regeneration script; quarterly audit |
| 9 | Audit script false-negatives new pattern | Each adapter PR adds patterns to script if new syscall shape appears |
| 10 | Roadmap order outpaces demand; built adapter goes unused | Next-review date every two phases; reorder based on demand signals |

---

## What This Roadmap Does NOT Claim

Per `docs/REALITY_AUDIT.md` and `scripts/check-banned-claims.sh`:

- This roadmap does not claim which adapters will see production use.
- This roadmap does not claim timing beyond ordering. No calendar dates or sprint estimates.
- This roadmap does not claim T3 is feasible for every adapter. Phase 33 (Semantic Kernel) is explicitly T1+T2 only.
- This roadmap does not claim the consolidated OpenAI-compatible adapter supports every vendor. The vendor allowlist is the contract.
- This roadmap does not claim ARC Studio's enforcement guarantees are absolute. Explicit opt-out from every gate is possible and documented honestly.
- This roadmap does not claim "production-ready," "enterprise-grade," "drop-in," or "seamless." All adapter documentation must pass `scripts/check-banned-claims.sh`.
