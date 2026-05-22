"""Real LangGraph runner. Streams astream_events(version='v2')."""
from __future__ import annotations

import pathlib
import uuid
from typing import Any, AsyncIterator

from agent_runtime_cockpit.ag_ui import map_event, MappingContext, AGUIEventType
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.audit.session import AuditSession
from agent_runtime_cockpit.audit.schema import RuntimeMode
from agent_runtime_cockpit.audit.storage import AuditChainStore
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter

from .loader import load_graph

import agent_runtime_cockpit.adapters.langgraph.mapping  # noqa: F401


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
                        _log_agui_to_audit(session, ag)

            session.log_run_completed(runtime="langgraph")

        return run_id

    async def _stream(self, graph: Any, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        async for event in graph.astream_events(inputs, version="v2"):
            yield event


def _log_agui_to_audit(session: Any, agui_event: dict[str, Any]) -> None:
    event_type = agui_event.get("type", "")
    if event_type == AGUIEventType.TOOL_CALL_START.value:
        session.log_tool_call(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            arguments=agui_event.get("args", {}),
            trust_level=agui_event.get("trust_level", "untrusted"),
        )
    elif event_type == AGUIEventType.TOOL_CALL_RESULT.value:
        session.log_tool_result(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            result=agui_event.get("result", {}),
            trust_level=agui_event.get("trust_level", "untrusted"),
        )
    elif event_type == AGUIEventType.TOOL_CALL_ERROR.value:
        session.log_tool_result(
            tool_name=agui_event.get("tool_name", ""),
            tool_id=agui_event.get("tool_id", ""),
            trust_level=agui_event.get("trust_level", "untrusted"),
            error={"code": "AGUI_TOOL_ERROR", "message": str(agui_event.get("error", ""))},
        )
