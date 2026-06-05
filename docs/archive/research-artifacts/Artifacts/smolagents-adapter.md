# Smolagents Adapter Research — R33 (Adapter Phase 32)

**Compiled:** 2026-05-25
**Status:** Research complete; implementation baseline delivered; live T3 remains opt-in gated.
**Sources:** Hugging Face smolagents docs, GitHub `huggingface/smolagents`, ARC adapter patterns.

---

## Summary

Smolagents is a Hugging Face agent framework centered on small abstractions and first-class code-executing agents. The main public surfaces are `CodeAgent`, `ToolCallingAgent`, model wrappers such as `InferenceClientModel`, `LiteLLMModel`, `OpenAIModel`, `TransformersModel`, and tool abstractions/decorators such as `Tool`, `@tool`, and built-in tools.

The code-execution surface is high risk. ARC integration therefore implements T1/T2 static analysis and a T3 gated path only. No agent code is executed by default. `ToolCallingAgent` execution requires both `ARC_SMOLAGENTS_RUNNER_ENABLED=1` and `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`. `CodeAgent` additionally requires `ARC_SMOLAGENTS_SANDBOX=...` and `RUN_SMOLAGENTS_CODE_AGENT=I_UNDERSTAND_CODE_EXECUTION_RISK`.

## Research Notes

| Source | Link | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Hugging Face docs | https://huggingface.co/docs/smolagents/index | `CodeAgent` writes Python actions; `ToolCallingAgent` supports normal tool calling; model wrappers include `InferenceClientModel`, `LiteLLMModel`, `TransformersModel`; secure execution can use Docker/E2B/Modal/Blaxel. | Detect agent/model/tool constructors and keep runner gated. | High | Exact event hooks for future T3 streaming need SDK inspection. |
| GitHub README | https://github.com/huggingface/smolagents | CLI names: `smolagent`, `webagent`; `LocalPythonExecutor` is not a security boundary; code agents should run in sandbox. | Capability report must state high-risk code execution and gated runner only. | High | Sandbox-backed execution remains separate future work. |
| ARC adapters | `python/src/agent_runtime_cockpit/adapters/dspy/`, `haystack/` | Adapter pattern: `detect.py`, `export.py`, `runner.py`, `capabilities.py`, `__init__.py`, tests. | Reuse same T1/T2/T3 scaffold shape. | High | None. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Detection | AST scan + import probe + dependency file check | Runtime introspection | No code execution; matches ARC pattern | `adapters/smolagents/detect.py` | High |
| Export | AST extraction of agents, model bindings, tools | Execute/import workspace | Safe static analysis only | `adapters/smolagents/export.py` | High |
| Runner | `ARC_SMOLAGENTS_RUNNER_ENABLED=1` plus `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`; CodeAgent requires sandbox marker and explicit confirmation | Default live execution | Code execution + provider/network risk | `adapters/smolagents/runner.py` | High |
| Capability | T1/T2 available, T3 gated, provider-backed false | Claim runnable | Avoid overclaim/security risk | `adapters/smolagents/__init__.py` | High |

## Detection Targets

- `import smolagents`
- `from smolagents import CodeAgent, ToolCallingAgent, tool, Tool`
- `CodeAgent(...)`, `ToolCallingAgent(...)`, `ManagedAgent(...)`
- `InferenceClientModel(...)`, `LiteLLMModel(...)`, `OpenAIModel(...)`, `TransformersModel(...)`, `AzureOpenAIModel(...)`, `AmazonBedrockModel(...)`
- `@tool`, subclasses of `Tool`
- `requirements.txt` / `pyproject.toml`: `smolagents`

## Truth Constraints

- No live provider/network calls in tests.
- No agent execution unless `ARC_SMOLAGENTS_RUNNER_ENABLED=1` and `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`.
- No `CodeAgent` execution unless `ARC_SMOLAGENTS_SANDBOX` is set and `RUN_SMOLAGENTS_CODE_AGENT=I_UNDERSTAND_CODE_EXECUTION_RISK`.
- No broad Smolagents adoption claim.
- Detection/export are AST-only.
- Code-agent execution remains high-risk and gated.
