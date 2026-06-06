# Prompt — Research: Strands Agents (AWS) Adapter for ARC Studio

> **Purpose:** Ground the Strands Agents adapter implementation in verified
> SDK facts before writing any code. Follow the verify-don't-trust rule:
> every API signature and detection heuristic must be checked against the
> real SDK or official docs, not assumed.

## Goal

Add a `StrandsAdapter` to `python/src/agent_runtime_cockpit/adapters/` that
lets ARC Studio detect, inspect, and (optionally, gated) run
[Strands Agents](https://github.com/strands-agents/sdk-python) projects.

## Questions to answer

1. **Detection** — what files/imports uniquely identify a Strands project?
   - Import patterns: `from strands import Agent`, `import strands`, etc.
   - Config files: `strands.yaml`, `strands.json`, `pyproject.toml [tool.strands]`?
   - Dependency name in `requirements.txt` / `pyproject.toml`: `strands-agents`?

2. **Run API** — what is the minimal call to execute an agent?
   - Is it `agent("prompt")` (callable), `agent.invoke(...)`, or something else?
   - Async variant? `await agent.ainvoke(...)`?
   - Streaming: does it yield events? What iterator protocol?

3. **Model binding** — how is the LLM attached?
   - `BedrockModel`, `AnthropicModel`, `OpenAIModel`?
   - What env vars are required per model type?
   - Which require AWS credentials vs a plain API key?

4. **Tool definitions** — how are tools declared?
   - `@tool` decorator? `Tool(...)` class? MCP tools?
   - What does the tool registration look like in the agent definition?

5. **Event/result structure** — what does a completed run return?
   - `result.message["content"]`? `result.text`? Something else?
   - Are there streaming event types (like AG-UI `TEXT_MESSAGE_CONTENT`)?

6. **Gating requirements** — what must be true to run?
   - Always needs AWS creds (Bedrock) OR can use Anthropic/OpenAI keys?
   - What is the right dual-gate key name (e.g. `"STRANDS"`, `"AWS_BEDROCK"`)?

7. **Version / package name** — `strands-agents` on PyPI?
   - `importlib.util.find_spec("strands")` — what is the top-level module?
   - Current stable version?

## Method

- Check the official Strands docs: https://strandsagents.com/0.1/
- Check the PyPI page: https://pypi.org/project/strands-agents/
- Check the SDK source: https://github.com/strands-agents/sdk-python
- Look at existing ARC adapters (langgraph.py, crewai.py) for the pattern to follow.

## Deliverable

`docs/research/strands-adapter-plan.md` with:
- Verified API signatures (method names + return types, with source link)
- Detection heuristics ranked by confidence
- Gating decision (which env var gates paid/cloud execution)
- WorkflowInfo topology shape (what nodes/edges a static export produces)
- Implementation plan: slices with acceptance criteria
