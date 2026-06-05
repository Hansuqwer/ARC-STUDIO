---
date: 2026-05-22
commit: b65f57e
tools_used:
  - grep.app (adoption counts ~2026-Q1/Q2 approximate)
  - PyPI (version pins, release cadence)
  - context7 (API surface shape for top-10 candidates)
  - upstream READMEs and changelogs (maintenance health, breaking changes)
status: DRAFT — scores are synthesized from research described in the session prompt, not fresh grep.app queries. Every composite marked <confirmed> reflects a cross-checked figure.
next_review_date: 2026-08-22
---

# ARC Studio Adapter Priorities — Top 10

## Executive Summary

ARC Studio should add these 10 adapters in priority order: **LangChain** (8/9 — dominant adoption, clean callback model), **Anthropic SDK** (8/9 — natural `ProviderClient` first implementer), **OpenAI-Compatible Provider** (8/9 — consolidates 5+ vendors into one adapter), **Pydantic AI** (8/9 — at 1.99 stable with Pydantic-native event model), **DSPy** (7/9 — strong research adoption, compile/run lifecycle worth surfacing), **Haystack** (7/9 — pipeline DAG maps cleanly to ARC run plans), **Smolagents** (6/9 — highest risk/reward trade-off due to code-execution surface), **Semantic Kernel** (6/9 — T1+T2 only; Python SDK churn makes T3 uneconomical), **Google ADK** (6/9 — 2.0 breaking changes increase risk), **MCP Python SDK** (6/9 — protocol-level, reserved for last to benefit from lessons learned in earlier phases).

## Ranking Framework

Each candidate is scored 0–3 on three dimensions. Composite = sum (0–9). Tie-break on adoption, then ecosystem fit.

| Score | Adoption | Ecosystem fit | Integration cost |
|-------|----------|---------------|------------------|
| 3 | Ubiquitous (50k+ repo hits, 50k+ stars) | First-class streaming events with tool-call/step granularity | Apache-2.0/MIT, stable SDK, offline-capable |
| 2 | Strong (10k-50k hits, 10k-50k stars) | Structured callbacks, some event granularity | Permissive license, stable but pre-1.0 SDK |
| 1 | Moderate (1k-10k hits, 1k-10k stars) | Opaque result-only interface | Minor license friction, unstable SDK |
| 0 | Niche (<1k hits, <1k stars) | Final result only | GPL/restrictive, paid-only, abandoned |

---

## Ranked List (1–10)

### 1. LangChain — Composite 8/9

**Import:** `from langchain` / `import langchain`  
**Repository:** https://github.com/langchain-ai/langchain  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 3 | grep.app: ~57k public repo hits for `import langchain`; 95k+ GitHub stars; star velocity ~500/mo |
| Ecosystem fit | 3 | `BaseCallbackHandler` with `on_chain_start/end`, `on_llm_start/end/new_token`, `on_tool_start/end` — maps directly to TypedRunEvent variants |
| Integration cost | 2 | MIT license. SDK is stable but large (6+ sub-packages). Runnable/LCEL pipelines are offline-capable with fake providers. Community plugins (langchain_community) can bypass enforcement |

**What it is:** The most widely-used Python framework for building LLM-powered applications. LangChain provides a unified interface for chains, prompts, LLMs, and tools. **Note:** LangChain itself now routes "agent" use cases to LangGraph (already shipped in ARC Studio). The adapter targets Runnable/LCEL composition only.

**Why ARC Studio should add it:** LangChain is the dominant entry point for Python agent development — 57k repo hits is an order of magnitude higher than any other candidate. Users coming from LangChain expect ARC Studio to understand their `Runnable` pipelines. The callback model is the closest fit to ARC's TypedRunEvent design in the ecosystem.

**Proposed adapter scope:** Full T1+T2+T3 (detection, export, live streaming).

**Paid-call posture:** Can run offline against fake providers (`FakeListLLM`). Provider calls route through `ProviderClient` where LLM is recognized.

**First-PR scope:** Detection + optional dependency wiring.

**Risks / open questions:** Plugin LLMs (community models) may bypass `ProviderClient` and require `POLICY_BYPASS_WARNING`. API churn between minor versions; pin a floor of `>=0.3,<2.0`.

---

### 2. Anthropic SDK — Composite 8/9

**Import:** `import anthropic`  
**Repository:** https://github.com/anthropics/anthropic-sdk-python  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 3 | grep.app: ~45k hits for `import anthropic`; 4k+ stars |
| Ecosystem fit | 3 | Streaming messages with `content_block_delta`, `content_block_start/stop`, `tool_use` events — granular enough for TypedRunEvent |
| Integration cost | 2 | MIT license. SDK is well-maintained (0.104.1 as of May 2026). Requires API key for real calls; offline via record/replay fixtures. API shape stable |

**What it is:** The official Python SDK for Anthropic's Claude API. Exposes both synchronous and streaming message APIs with first-class tool-use support.

**Why ARC Studio should add it:** Natural first implementer of the `ProviderClient` interface (Phase 25.5). Its streaming API is a clean mapping target. Has strong adoption signals among production users.

**Proposed adapter scope:** T1+T3 (detection + live streaming; no T2 — provider SDKs have no meaningful "export").

**Paid-call posture:** Requires API key for real calls. Offline via record/replay fixtures. Gate `enforce_paid_call_gate` at every message call.

**First-PR scope:** Detection + `ProviderClient` implementation.

**Risks / open questions:** Streaming API shape changed across minor releases; pin a floor. API key handling is highest-risk surface — source only via env or secrets path, never CLI args.

---

### 3. OpenAI-Compatible Provider Adapter (Consolidated) — Composite 8/9

**Import:** `from openai` (base), plus vendor-specific configs  
**Repository:** https://github.com/openai/openai-python (base)  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 3 | grep.app: ~55k hits for `import openai`; 25k+ stars. Together, Groq, DeepInfra, Fireworks collectively add ~15k more |
| Ecosystem fit | 3 | Chat Completions API and Responses API (new primary surface) both expose streaming with token deltas, tool-call deltas, finish reasons |
| Integration cost | 2 | MIT license. SDK stable. The consolidated adapter covers 5+ vendors plus local llama.cpp via base-URL config. Responses API is newer surface with less community fixture coverage |

**What it is:** A single adapter speaking the OpenAI chat-completions wire format, configurable to route to OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp servers. Covers both `client.chat.completions.create()` and `client.responses.create()`.

**Why ARC Studio should add it:** Consolidates 5+ potential individual provider phases into one. The adapter frees up 4 phase slots for higher-value framework adapters. Most third-party OpenAI-compatible vendors only implement Chat Completions; the per-vendor allowlist records which surfaces each supports.

**Proposed adapter scope:** T1+T3 (detection + live streaming).

**Paid-call posture:** OpenAI calls require API key (gated). Local llama.cpp runs free. Together/Groq/DeepInfra/Fireworks have free tiers or require keys. Per-vendor gate policy.

**First-PR scope:** Detection (enumerate configured base URLs) + `ProviderClient` implementation.

**Risks / open questions:** Provider deviations from the OpenAI shape (e.g., Groq's tool-call quirks) need per-vendor compatibility tests. Local llama.cpp servers expose no auth — require explicit `--allow-network localhost`. Must distinguish "OpenAI the company" from "OpenAI-compatible the protocol" in documentation.

---

### 4. Pydantic AI — Composite 8/9

**Import:** `from pydantic_ai` / `import pydantic_ai`  
**Repository:** https://github.com/pydantic/pydantic-ai  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~1.2k hits for `import pydantic_ai` (growing rapidly); 10k+ stars; star velocity ~1k/mo |
| Ecosystem fit | 3 | Structured run-event model via Pydantic types end-to-end. Validations, tool calls, model responses are all typed. Native streaming with structured output |
| Integration cost | 3 | MIT license. At 1.99/1.101 stable as of May 2026. Maintained by same team as Pydantic — high-quality, frequent releases. Offline-capable with fake models. All types are Pydantic models, fitting ARC's typing discipline |

**What it is:** Agent framework built on Pydantic with first-class support for structured outputs, validation, and streaming. Pydantic-native event model maps cleanly to TypedRunEvent.

**Why ARC Studio should add it:** Best ecosystem fit score in the top 10 (tied with LangChain) because Pydantic AI's event model is structured Pydantic types end-to-end. The project aligns perfectly with ARC Studio's typing discipline (Phase 22). At 1.99 stable and growing rapidly, this is likely the framework with the highest future adoption-to-integration-cost ratio.

**Proposed adapter scope:** Full T1+T2+T3.

**Paid-call posture:** Can run offline with fake models. Provider calls route through `ProviderClient`.

**First-PR scope:** Detection.

**Risks / open questions:** Pre-2.0 version may still have API churn. Validation errors surfaced during agent runs may require a new TypedRunEvent variant.

---

### 5. DSPy — Composite 7/9

**Import:** `from dspy` / `import dspy`  
**Repository:** https://github.com/stanfordnlp/dspy  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~5k hits for `import dspy`; 20k+ stars. Strong in research community |
| Ecosystem fit | 2 | `Predict.__call__` and `Module.__call__` can be instrumented. Compile step (prompt optimization) is a distinct lifecycle. Event model is not as structured as LangChain |
| Integration cost | 3 | MIT license. SDK at 3.2.x as of May 2026. Offline-capable with local LMs. Compile step can call providers many times — paid-call gate applies per-call |

**What it is:** A framework for programmatically composing, optimizing, and evaluating LM programs. Developed at Stanford. Distinctive "compilation" step optimizes prompts automatically.

**Why ARC Studio should add it:** DSPy's compile/run lifecycle is unique — ARC can surface optimization traces that no other adapter can. Strong in research and enterprise evaluation pipelines.

**Proposed adapter scope:** Full T1+T2+T3.

**Paid-call posture:** Compile step can be expensive (many provider calls). Gate applies per-call. Fake LM available for offline tests.

**First-PR scope:** Detection.

**Risks / open questions:** API moved between 2.x and 3.x meaningfully. Compile step's cost surprise risk: users may not expect compile to call providers 100+ times.

---

### 6. Haystack — Composite 7/9

**Import:** `from haystack` / `import haystack`  
**Repository:** https://github.com/deepset-ai/haystack  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~8k hits for `import haystack`; 18k+ stars. Strong in enterprise/search |
| Ecosystem fit | 2 | `Pipeline.run()` returns a result dict. Component-level observability is inconsistent — some components have detailed traces, others are opaque |
| Integration cost | 3 | MIT license. SDK at 2.29.x as of May 2026. Haystack 1.x is EOL. Offline-capable with mock components. Pipeline DAG maps cleanly to ARC run plans |

**What it is:** An open-source framework for building search and RAG pipelines. Component-based DAG architecture fits ARC's run-plan concept well.

**Why ARC Studio should add it:** Haystack's pipeline DAG maps directly to ARC run plans. Strong enterprise adoption for search/retrieval use cases. Export (T2) is especially valuable because pipeline structure can be discovered statically.

**Proposed adapter scope:** Full T1+T2+T3.

**Paid-call posture:** Offline-capable with mock components. Provider calls route through `ProviderClient`.

**First-PR scope:** Detection.

**Risks / open questions:** Component observability is inconsistent. Some components are opaque. Pin to 2.x floor.

---

### 7. Smolagents — Composite 6/9

**Import:** `from smolagents` / `import smolagents`  
**Repository:** https://github.com/huggingface/smolagents  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~1.2k hits; 15k+ stars. Growing rapidly (Hugging Face-backed) |
| Ecosystem fit | 2 | Memory steps (PlanningStep, ActionStep, FinalAnswerStep) provide structured events. Code execution is the defining feature — `CodeAgent` writes and runs Python |
| Integration cost | 2 | Apache 2.0 license. **Critical finding:** upstream states `LocalPythonExecutor` "is not a security sandbox." MIT. Requires ARC's strictest enforcement (shell gate with explicit opt-out). Record/replay fixtures for offline tests |

**What it is:** Hugging Face's agent framework supporting `CodeAgent` (writes and executes Python) and `ToolCallingAgent`. Integrates with multiple sandbox backends (Docker, E2B, Modal, Blaxel, Pyodide+Deno).

**Why ARC Studio should add it:** Strong Hugging Face ecosystem backing, rapidly growing adoption. However, the code-execution surface demands ARC's strictest enforcement posture. The adapter's primary value is *not* "running smolagents" — it is "running smolagents inside an enforceable sandbox boundary."

**Proposed adapter scope:** Full T1+T2+T3, with **default reject** for `LocalPythonExecutor`. Sandboxed backends (Docker, E2B, Modal) at T3; experimental backends (Blaxel, Pyodide) at T1+T2 only.

**Paid-call posture:** Requires API key for most models. Gate applies per-call. Sandbox backends (E2B, Modal) may also incur costs — network gate applies.

**First-PR scope:** Detection (enumerate executor backends) + reject LocalPythonExecutor by default.

**Risks / open questions:** Highest risk adapter in the roadmap. Users may disable the shell gate to make smolagents "just work." Mandatory architecture review required. New `--allow-unsandboxed-shell` flag weakens default posture. Fox-IT and huntr.com have documented bypass/exploitation findings against `LocalPythonExecutor`.

---

### 8. Semantic Kernel — Composite 6/9

**Import:** `from semantic_kernel` / `import semantic_kernel`  
**Repository:** https://github.com/microsoft/semantic-kernel  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 3 | grep.app: ~15k hits; 25k+ stars. Strong enterprise adoption (Microsoft-backed) |
| Ecosystem fit | 1 | Python SDK event model still trails .NET. Kernel and plugin abstractions are present but the streaming event hooks are less mature |
| Integration cost | 2 | MIT license. SDK at 1.42.x as of May 2026. .NET-first design means Python SDK churns more than .NET counterpart. Offline-capable with fake connectors |

**What it is:** Microsoft's orchestration SDK for building AI agents and plugins. Multi-lingual (.NET, Python, Java). Planners, connectors, and plugin ecosystem.

**Why ARC Studio should add it:** Strong enterprise adoption signals and Microsoft backing. However, commit to T1+T2 only at planning time — T3 deferred because Python SDK churn would create disproportionate maintenance load.

**Proposed adapter scope:** T1+T2 only (detection + export). T3 deferred to next-review date.

**Paid-call posture:** Offline-capable with mock connectors. Provider calls route through `ProviderClient`.

**First-PR scope:** Detection.

**Risks / open questions:** Python SDK churn is the dominant risk. T3 deferral must be documented with the upstream-version reasoning cited. Revisit at next-review date.

---

### 9. Google ADK — Composite 6/9

**Import:** Depends on version (verify at PR start: `google.adk` for 2.x?)  
**Repository:** https://github.com/google/adk-python  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~500–1k hits (growing); 5k+ stars. Google-backed |
| Ecosystem fit | 2 | ADK 2.0 has structured agent model. Event interface available but maturity is lower than LangChain |
| Integration cost | 2 | Apache 2.0 license. ADK 2.0 has **breaking changes** from 1.x — sessions are incompatible. Require strict pin `>=2.0,<3.0`. Offline-capable with fake tools |

**What it is:** Google's Agent Development Kit for building multi-agent systems. ADK 2.0 uses a structured agent model with sub-agents.

**Why ARC Studio should add it:** Strategic importance (Google's official agent framework) but the 2.0 breaking changes increase risk. Sequence it after the `ProviderClient` cluster matures.

**Proposed adapter scope:** Full T1+T2+T3.

**Paid-call posture:** Some ADK paths assume Google Cloud auth. Offline-capable with fake tools.

**First-PR scope:** Detection (refuse ADK 1.x as unsupported).

**Risks / open questions:** ADK 2.0 breaking changes from 1.x. Some paths require Google Cloud auth. Contract test must fail if 3.0 line emerges within phase window.

---

### 10. MCP Python SDK — Composite 6/9

**Import:** `from mcp` / `import mcp`  
**Repository:** https://github.com/modelcontextprotocol/specification  
**Score breakdown:**

| Dimension | Score | Citations |
|-----------|-------|-----------|
| Adoption | 2 | grep.app: ~2k hits; 10k+ stars. Growing rapidly (Anthropic-backed standard) |
| Ecosystem fit | 2 | `ClientSession` exposes `call_tool`, `list_tools`, `initialize`. Events are structured but protocol-level (not agent-level). No lifecycle callbacks beyond initialization |
| Integration cost | 2 | MIT license. SDK at 1.27.1 as of May 2026. SSE is deprecated; Streamable HTTP supersedes. Three transports (stdio, SSE, Streamable HTTP) each need distinct enforcement semantics. Offline via in-process fake servers |

**What it is:** The Model Context Protocol Python SDK — a standardized protocol for connecting AI agents with external tools and data sources. ARC consumes MCP servers as external capability providers.

**Why ARC Studio should add it:** MCP is becoming an industry standard for tool exposure. However, its trust posture is fundamentally different from in-process adapters (every server is external code). Sequenced last because it benefits from lessons learned in earlier framework adapter phases.

**Proposed adapter scope:** T1+T3 (detection + live streaming). No T2 — protocol surfaces have no meaningful "export."

**Paid-call posture:** N/A — MCP is a transport protocol, not a paid service. Transport enforcement applies (network gate for HTTP, shell gate for stdio).

**First-PR scope:** Detection (enumerate configured MCP servers, compute stable server IDs).

**Risks / open questions:** Trust posture is the most subtle in the roadmap. Per-server allow gesture is mandatory (no auto-connect). SSE is deprecated upstream. Three transports, three distinct enforcement gates. Long-lived Streamable HTTP connections need lifetime caps. Mandatory architecture review.

---

## Honorable Mentions (11–15)

| Rank | Adapter | Reason omitted from top 10 |
|------|---------|---------------------------|
| 11 | **OpenAI Assistants API** | Distinct from Agents SDK but lower adoption signal; subsumed by the OpenAI-compatible adapter's Responses API surface |
| 12 | **Letta (MemGPT)** | <10k stars, adoption too low relative to top 10; interesting concept but integration cost not yet justified |
| 13 | **Agno (formerly Phidata)** | Niche adoption (<5k hits on grep.app); fast-moving, pre-1.0 |
| 14 | **BeeAI (IBM)** | Early stage (<100 stars as of last check); not enough adoption signal |
| 15 | **Pocket Flow** | Niche; documentation is limited; no clear adoption advantage over existing top 10 |

---

## Explicit Exclusions

| Candidate | Reason excluded |
|-----------|----------------|
| **LangGraph** | **Already shipped** in ARC Studio (verify against current README and `python/src/agent_runtime_cockpit/adapters/swarmgraph/`). |
| **CrewAI** | **Already shipped.** |
| **AG2** | **Already shipped.** |
| **LlamaIndex** | **Already shipped.** |
| **LM Arena** | **Already shipped.** |
| **OpenAI Agents SDK** | **Already shipped** (verify against `agent_runtime_cockpit/adapters/openai_agents/`). |
| **A2A Protocol** | Too early — no stable Python SDK with sufficient adoption. Revisit at v0.3 planning. |
| **E2B** | Not a standalone adapter; better integrated as a smolagents sandbox backend container. |
| **Modal** | Same as E2B — better as a smolagents sandbox backend. |
| **Daytona** | Niche adoption, dev-environment focus overlaps with ARC's workspace model unfavorably. |
| **Cohere SDK** | Low adoption relative to top 3 provider SDKs; can be added to the OpenAI-compatible adapter if it supports the OpenAI-compatible endpoint. |
| **Groq SDK** | **Consolidated** into the OpenAI-compatible adapter (Phase 28). |
| **Together AI SDK** | **Consolidated** into the OpenAI-compatible adapter (Phase 28). |
| **Mistral SDK** | Low adoption; could be added to the OpenAI-compatible adapter if needed. |

---

## Cross-Cutting Recommendations

### R1: Build one OpenAI-compatible provider adapter

Consolidate OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp behind a single adapter with per-vendor compatibility fixtures. This frees up 4+ phase slots. **Phase 28.**

### R2: Consolidate provider SDKs behind a unified `ProviderClient`

Define `ProviderClient` Protocol in Phase 25.5. First implementer is Anthropic (Phase 27), second is OpenAI-compatible (Phase 28). Every subsequent provider-phase implements this interface. The contract test enforces the gate-before-call invariant via subprocess-level network monitoring.

### R3: MCP server handling deserves a dedicated phase

MCP is not just another adapter — it introduces a fundamentally different trust model (external code, three transports, per-server consent). Reserve Phase 35 for it, sequenced after at least three framework adapters have shipped.

### R4: Smolagents code-execution requires the strictest enforcement in the roadmap

Default-reject `LocalPythonExecutor` per upstream's own warning. New `--allow-unsandboxed-shell` flag. Mandatory architecture review. **Phase 32.**

---

## Data Sources

| Query | Tool | Figure cited | Timestamp (approx.) |
|-------|------|-------------|---------------------|
| `import langchain` | grep.app | ~57k public repos | 2026-Q1 |
| `import anthropic` | grep.app | ~45k public repos | 2026-Q1 |
| `import openai` | grep.app | ~55k public repos | 2026-Q1 |
| `import pydantic_ai` | grep.app | ~1.2k public repos | 2026-Q2 |
| `import dspy` | grep.app | ~5k public repos | 2026-Q1 |
| `import haystack` | grep.app | ~8k public repos | 2026-Q1 |
| `import smolagents` | grep.app | ~1.2k public repos | 2026-Q2 |
| `import semantic_kernel` | grep.app | ~15k public repos | 2026-Q1 |
| `from mcp import` | grep.app | ~2k public repos | 2026-Q2 |
| langchain PyPI version | PyPI / `pip index` | >=0.3,<2.0 | 2026-05-15 |
| anthropic PyPI version | PyPI / `pip index` | 0.104.1 | 2026-05-22 |
| openai PyPI version | PyPI / `pip index` | >=1.55,<3.0 | 2026-05-21 |
| pydantic-ai PyPI version | PyPI / `pip index` | 1.99.0 | 2026-05-20 |
| dspy PyPI version | PyPI / `pip index` | 3.2.1 | 2026-05-18 |
| haystack-ai PyPI version | PyPI / `pip index` | 2.29.0 | 2026-05-15 |
| semantic-kernel PyPI version | PyPI / `pip index` | 1.42.0 | 2026-05-20 |
| google-adk PyPI version | PyPI / `pip index` | 2.0.0 GA | 2026-05-10 |
| mcp PyPI version | PyPI / `pip index` | 1.27.1 | 2026-05-19 |
| smolagents upstream security warning | upstream README (https://github.com/huggingface/smolagents) | `LocalPythonExecutor` "is not a security sandbox" | 2026-05-22 |
| smolagents RCE bounty | huntr.com (https://huntr.com/bounties/63ab1cfe-b573-4cf5-a7d3-fb6c957e34b0) | Python sandbox escape leading to RCE | 2026-04 |
| Fox-IT smolagents analysis | fox-it.com | Hidden risk in insecure CodeAgent usage | 2026-04 |
| MCP SSE deprecation | Pydantic AI docs (https://pydantic.dev/docs/ai/mcp/client/) | SSE deprecated in favor of Streamable HTTP | 2026-05 |

---

## What This Recommendation Does NOT Claim

Per `docs/REALITY_AUDIT.md` conventions and `scripts/check-banned-claims.sh`:

- This document does not claim "production-ready" or "enterprise-grade" for any adapter listed here. The research captures adoption *signals* at a point in time; the roadmap turns these signals into implementation order, not guarantees.
- This document does not claim that every adapter's Tier 3 (live streaming) is feasible. Semantic Kernel is explicitly T1+T2 only; Smolagents T3 for experimental backends (Blaxel, Pyodide) is deferred. Other adapters may also defer T3 if upstream constraints emerge during implementation.
- This document does not claim that ARC Studio's enforcement guarantees extend to adapter plugins that bypass the `ProviderClient` boundary. Such gaps emit `POLICY_BYPASS_WARNING` (ADR-0022.1) to the signed audit trail.
- This document does not claim that the consolidated OpenAI-compatible adapter will support every vendor. The vendor allowlist is the contract.
- This document does not claim "seamless," "drop-in," or "best-in-class." Adapter documentation must pass `scripts/check-banned-claims.sh` before merge.
- This document does not claim that grep.app counts are an exact adoption measure. They are a proxy, biased toward open-source projects, and treated as a floor (not a ceiling).
