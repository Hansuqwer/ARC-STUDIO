# Semantic Kernel Adapter Research

Status: research complete for R34 / Adapter Phase 33. Implementation is T1 detection and T2 static export only. No Semantic Kernel runtime execution is implemented or claimed.

## Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 Semantic Kernel docs | `/microsoft/semantic-kernel` | Current Python examples use `from semantic_kernel import Kernel`, `kernel.add_service(...)`, `kernel.add_plugin(...)`, `@kernel_function`, `kernel.invoke(...)`, and `kernel.invoke_prompt(...)`. | Detection scans for `semantic_kernel` imports, `Kernel`, plugin registration, kernel functions, and invocations. Export maps plugins/functions/invocations to static ARC workflow nodes. | High | SDK APIs are still active; execution remains out of scope. |
| Context7 Semantic Kernel agent docs | `/microsoft/semantic-kernel` | Agent orchestration examples use `ChatCompletionAgent`, `SequentialOrchestration`, `ConcurrentOrchestration`, `HandoffOrchestration`, `GroupChatOrchestration`, and `InProcessRuntime`. | Detection/export includes agent and orchestration class names as agent nodes, without instantiating or running them. | High | Agent APIs may change across Semantic Kernel releases. |
| Local adapter patterns | `python/src/agent_runtime_cockpit/adapters/dspy`, `haystack`, `smolagents` | Recent adapters use separate `detect.py`, `export.py`, `capabilities.py`, adapter `__init__.py`, registry registration, and isolated tests. | Semantic Kernel adapter follows the same additive T1/T2-only shape and capability-report language. | High | None. |
| Vercel Grep/code search | N/A in this runtime | No dedicated Vercel Grep tool is exposed in the available toolset. | Used local repository pattern search instead; external corpus comparison remains a follow-up before security-signoff claims. | Low | Run Vercel Grep externally when available. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Adapter scope | T1 detection + T2 static export only | Gated runner scaffold, live execution | Semantic Kernel can trigger provider calls; Python SDK churn makes execution too risky for this slice. | `python/src/agent_runtime_cockpit/adapters/semantic_kernel/*` | High |
| Detection strategy | Import/config/static-pattern scan | Import workspace modules, run examples | Avoids executing user code and provider setup. | `detect.py` | High |
| Export model | One `WorkflowInfo` per Semantic Kernel source file with Kernel/plugin/function/agent/invocation nodes | Per-agent workflows, dynamic runtime introspection | Static AST export is safer and matches existing adapter phases. | `export.py` | Medium |
| Registration | Built-in default adapter registry | Manual opt-in registry | Matches DSPy/Haystack/Smolagents adapter pattern. | `adapters/registry.py` | High |

## Current Scope

Real now:
- `semantic_kernel` adapter detection via installed package, Python imports, dependency files, Kernel/plugins/agents/processes patterns.
- Static workflow export for Kernel variables, `@kernel_function` plugins/functions, `add_plugin`, agents/orchestrations, and `invoke`/`invoke_prompt` calls.
- Default registry registration.
- Focused tests covering detection, export, adapter capability reports, and registry inclusion.

Design-only/deferred:
- Runtime execution.
- Event streaming.
- Provider-backed Semantic Kernel flows.
- Process framework execution.

Claim boundary:
- This adapter can inspect/export Semantic Kernel project structure.
- It cannot run Semantic Kernel workloads.
- It performs no provider calls.
