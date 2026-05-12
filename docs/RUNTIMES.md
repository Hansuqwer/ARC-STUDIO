# ARC Runtimes

## LangGraph

Set `ARC_LANGGRAPH_EXPORT=module:function` to run a LangGraph workflow. The module must be importable from the workspace root or `src/` inside the workspace. Absolute filesystem paths, relative module names, parent traversal, and imports resolving outside the workspace are rejected.

Accepted target shapes:

- A `StateGraph`-like object with `.compile()`.
- A compiled graph/Pregel-like object with `.invoke()`.
- A zero-argument sync factory returning either shape.
- A zero-argument async factory returning either shape.

Resolution order: ARC imports the explicit target, calls it if it is a factory, awaits it if needed, compiles it if it has `.compile()`, then requires the final object to expose `.invoke()`.

Security model: `ARC_LANGGRAPH_EXPORT` is treated as untrusted workspace configuration. ARC only accepts dotted module names, never filesystem paths. During resolution, ARC temporarily adds the workspace root and workspace `src/` to `sys.path`, resolves the module with `importlib.util.find_spec()`, and rejects any module whose resolved origin is outside those workspace paths before importing it. Standard library and installed package targets such as `os:getcwd` are rejected even though Python can import them.

MVP run output: the non-streaming `run_workflow` path emits exactly `RUN_STARTED` then `RUN_COMPLETED` with `{ "state": <final_state_dict> }`. Per-node events are reserved for the streaming implementation.

### Streaming Persistence

LangGraph streaming uses `graph.stream(..., stream_mode=["updates", "messages"])` when the compiled graph exposes `.stream()`. If `.stream()` is unavailable, ARC falls back to the existing non-streaming `.invoke()` path.

Persistence rules:

- Raw token-level `MESSAGE_CHUNK` events are SSE-only and ephemeral. They are never written to the persisted `RunRecord.events` trace.
- Coalesced `NODE_UPDATE` events are persisted. They contain the per-node update payload returned by LangGraph `updates` mode.
- `RUN_STARTED`, `RUN_COMPLETED`, and `RUN_FAILED` are persisted.
- The final persisted `RUN_COMPLETED` event still includes `{ "state": <final_state_dict> }` when ARC can derive a final state from stream output.
- Stream payloads are redacted before entering ARC events. Messages containing secret-like material are replaced with the same redacted marker used by non-streaming failures.

Current limitation: ARC's persisted run-start endpoints return completed `RunRecord` objects, so token chunks are not exposed by the existing REST response. A future live SSE runner may forward ephemeral `MESSAGE_CHUNK` events while persisting only coalesced updates.

Error codes:

| Code | Meaning |
| --- | --- |
| `LG_DEP_MISSING` | `langgraph` is not importable in the Python environment. |
| `LG_EXPORT_UNSET` | `ARC_LANGGRAPH_EXPORT` is missing or malformed. |
| `LG_EXPORT_NOT_FOUND` | The module or attribute could not be resolved. |
| `LG_TARGET_INVALID` | The target resolved outside the workspace or did not produce an invokable graph. |
| `LG_INVOKE_FAILED` | The graph raised during `.invoke()`. |

LangGraph defaults to `requires_paid_calls=false`; ARC does not assume that graph control flow calls an LLM. If a future graph target needs paid-call declaration, add explicit metadata rather than inferring it from LangGraph itself.

Example:

```python
# graph_module.py
from langgraph.graph import StateGraph


def build_graph():
    graph = StateGraph(dict)
    graph.add_node("start", lambda state: {"messages": ["ok"]})
    graph.set_entry_point("start")
    graph.set_finish_point("start")
    return graph
```

Run:

```bash
ARC_LANGGRAPH_EXPORT=graph_module:build_graph arc run wf-langgraph --runtime langgraph --json
```
