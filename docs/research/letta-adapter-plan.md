# Letta (MemGPT) Adapter — Implementation Plan

**Status:** Implemented 2026-06-06 | Sources: PyPI letta-client v1.12.1, context7 /letta-ai/letta-python

---

## Verified API facts

| Fact | Source | Value |
|---|---|---|
| Package | PyPI | `letta-client` v1.12.1 |
| Module | PyPI | `letta_client` |
| Sync client | PyPI README | `Letta(api_key=..., base_url=...)` |
| Send message | context7 | `client.agents.messages.create(agent_id=..., messages=[{"role":"user","content":"..."}]) → LettaResponse` |
| Response text | context7 | `msg.content` where `msg.message_type == "assistant_message"` |
| Local server | PyPI README | `base_url="http://localhost:8283"` (default Letta server port) |
| Cloud | PyPI README | `api_key=os.environ["LETTA_API_KEY"]` |
| Agent file | docs | `.af` extension — portable agent bundle |

## Key difference from other adapters

Letta is **server-backed** — the agent lives on a running Letta server with persistent memory. `run_workflow` sends a message to an existing agent (`ARC_LETTA_AGENT_ID`) rather than loading code from a workspace.

## Detection heuristics

1. `find_spec("letta_client")` — SDK installed
2. `LETTA_API_KEY` or `LETTA_BASE_URL` env vars set → a server is configured
3. `from letta` / `import letta_client` in workspace `.py` files
4. `letta-client` in `requirements.txt` / `pyproject.toml`
5. `.af` agent files in workspace

## Gating

- `ARC_LETTA_AGENT_ID` — required: identifies the target agent on the server
- `ARC_LETTA_ALLOW_COSTS=true` — dual-gate for paid calls
- `LETTA_API_KEY` or `LETTA_BASE_URL` — at least one must be set

## WorkflowInfo

Single "Agent" node with agent_id in metadata. No static topology (state lives server-side).

## Acceptance

- `arc runtimes` lists `letta` adapter
- `can_run=False` by default; `True` when gate + agent_id present
- `run_workflow` calls `client.agents.messages.create` and returns `RunRecord`
- 100% offline tests (mock the Letta client)
