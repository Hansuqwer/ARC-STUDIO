"""Real LangGraph runner. Streams astream_events(version='v2')."""
from __future__ import annotations

import pathlib
import uuid
from typing import Any, AsyncIterator

from agent_runtime_cockpit.ag_ui import map_event, MappingContext
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter

from .loader import load_graph

import agent_runtime_cockpit.adapters.langgraph.mapping  # noqa: F401


class LangGraphRunner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace

    async def run(self, graph_id: str | None, inputs: dict[str, Any]) -> str:
        require_dual_gate("LANGGRAPH")
        run_id = uuid.uuid4().hex[:12]
        ctx = MappingContext(thread_id=f"th-{run_id}", run_id=run_id, runtime="langgraph")

        traces = self.workspace / ".arc" / "traces" / f"{run_id}.jsonl"
        audit = self.workspace / ".arc" / "audit" / f"{run_id}.chain.jsonl"
        traces.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)

        graph = load_graph(self.workspace, graph_id)
        with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
            async for native in self._stream(graph, inputs):
                native.pop("_mock", None)
                for ag in map_event("langgraph", native, ctx):
                    t.write(ag)
                    a.append(ag)
        return run_id

    async def _stream(self, graph: Any, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        async for event in graph.astream_events(inputs, version="v2"):
            yield event
