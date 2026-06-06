# Strands Agents (AWS) Adapter — Implementation Plan

**Status:** Implemented 2026-06-06 | Sources: PyPI strands-agents v1.42.0, strandsagents.com, github.com/strands-agents/harness-sdk

---

## Verified API facts

| Fact | Source | Value |
|---|---|---|
| Package name | PyPI | `strands-agents` |
| Top-level module | PyPI / SDK | `strands` |
| Version | PyPI | 1.42.0 (Production/Stable) |
| Run API | SDK source | `agent("prompt") → AgentResult` (callable) |
| `AgentResult.message` | agent_result.py | `dict` with `"content": list[dict]` |
| Text extraction | agent_result.py `__str__` | `item["text"]` for text-type content blocks |
| `str(result)` | agent_result.py | Concatenated text blocks |
| Default model | PyPI README | `BedrockModel` (needs AWS creds) |
| Other models | PyPI README | `AnthropicModel`, `OpenAIModel`, `GeminiModel`, `OllamaModel` |
| Tool declaration | PyPI README | `@tool` decorator, `Tool(...)` class |
| Hooks | strandsagents.com | `BeforeToolCallEvent`, `AfterToolCallEvent` |

## Detection heuristics (ranked by confidence)

1. `importlib.util.find_spec("strands")` — confirms SDK installed (high confidence)
2. `from strands import Agent` / `import strands` in any `.py` file (high)
3. `strands-agents` in `requirements.txt` / `pyproject.toml` (medium)
4. `strands.yaml` or `strands.json` config file (low, edge case)

## Gating decision

Default Strands model = BedrockModel → requires AWS credentials (`AWS_DEFAULT_REGION`
or `AWS_ACCESS_KEY_ID`). Other providers need their own keys. Gate as:

- Dual-gate key: `"STRANDS"` → requires `ARC_STRANDS_ALLOW_COSTS=true`
- `can_run=True` only when gating passes AND export target is set via `ARC_STRANDS_EXPORT`
- `can_run=False` (default) — detect/export only, no execution without explicit opt-in

## WorkflowInfo topology

Static export produces a single `"Agent"` node (no static tool topology without
running code — tools are registered at runtime). Honest: mark
`export_fidelity="static"` in doctor actions.

## Implementation slices

### Slice 1 — Detect + capabilities (P0)
- `detect(workspace)` → `(bool, float, list[str])`
- `capabilities()` → `RuntimeCapabilities(can_run=False, ...)`
- `capability_report(workspace)` → `CapabilityReport` with doctor actions

### Slice 2 — Static export (P0)
- `export_workflow(workspace)` → single-node `WorkflowInfo`

### Slice 3 — Gated run (P1)
- `run_workflow(workflow_id, inputs)` → `RunRecord`
- Loads agent via `ARC_STRANDS_EXPORT=module:attr`
- Calls `agent(prompt)` → `AgentResult`
- Maps result to `RunRecord` (status=completed, output=str(result))
- Dual-gate enforced: `ARC_STRANDS_ALLOW_COSTS=true`

## Acceptance criteria
- `arc runtimes` lists `strands` adapter
- `detect()` returns `(False, 0.0, [])` when `strands` not installed
- `can_run=False` by default; `True` only when gate + export target present
- `run_workflow` raises `GatingError` without the gate env var
- 100% offline tests (no actual Bedrock/API calls)
