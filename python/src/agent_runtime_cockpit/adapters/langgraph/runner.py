"""Real LangGraph runner. Streams astream_events(version='v2')."""

from __future__ import annotations

import pathlib
import uuid
from typing import Any, AsyncIterator

import agent_runtime_cockpit.adapters.langgraph.mapping  # noqa: F401
from agent_runtime_cockpit.ag_ui import MappingContext, map_event
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.audit.runner_integration import log_agui_to_audit
from agent_runtime_cockpit.audit.schema import RuntimeMode
from agent_runtime_cockpit.audit.session import AuditSession
from agent_runtime_cockpit.audit.storage import AuditChainStore
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter

from .loader import load_graph


class LangGraphRunner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace
        self._audit_store = AuditChainStore(audit_dir=workspace / ".arc" / "audit")

    async def run(self, graph_id: str | None, inputs: dict[str, Any]) -> str:
        require_dual_gate("LANGGRAPH")
        run_id = uuid.uuid4().hex[:12]
        ctx = MappingContext(thread_id=f"th-{run_id}", run_id=run_id, runtime="langgraph")

        traces = self.workspace / ".arc" / "traces" / f"{run_id}.jsonl"
        audit = self.workspace / ".arc" / "audit" / f"{run_id}.chain.jsonl"
        traces.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)

        graph = load_graph(self.workspace, graph_id)

        async with AuditSession(run_id=run_id, store=self._audit_store) as session:
            session.log_run_started(runtime="langgraph", mode=RuntimeMode.gated_local)

            with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
                async for native in self._stream(graph, inputs):
                    native.pop("_mock", None)
                    for ag in map_event("langgraph", native, ctx):
                        t.write(ag)
                        a.append(ag)
                        log_agui_to_audit(session, ag)

            session.log_run_completed(runtime="langgraph")

        return run_id

    async def _stream(self, graph: Any, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        async for event in graph.astream_events(inputs, version="v2"):
            yield event
