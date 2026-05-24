"""CrewAI runner. Real execution gated; events come from listener."""

from __future__ import annotations

import asyncio
import pathlib
import uuid
from typing import Any

from agent_runtime_cockpit.ag_ui import MappingContext, map_event
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.audit.runner_integration import log_agui_to_audit
from agent_runtime_cockpit.audit.schema import RuntimeMode
from agent_runtime_cockpit.audit.session import AuditSession
from agent_runtime_cockpit.audit.storage import AuditChainStore
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter
from agent_runtime_cockpit.workspace.entrypoint import resolve_python_entrypoint

from . import mapping  # noqa: F401
from .listener import ArcCrewAIListener


class CrewAIRunner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace
        self._audit_store = AuditChainStore(audit_dir=workspace / ".arc" / "audit")

    async def run(self, entrypoint: str, inputs: dict[str, Any]) -> str:
        require_dual_gate("CREWAI")
        run_id = uuid.uuid4().hex[:12]
        ctx = MappingContext(thread_id=f"th-{run_id}", run_id=run_id, runtime="crewai")

        traces = self.workspace / ".arc" / "traces" / f"{run_id}.jsonl"
        audit = self.workspace / ".arc" / "audit" / f"{run_id}.chain.jsonl"
        traces.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        listener = ArcCrewAIListener(queue)
        listener.attach()

        crew = resolve_python_entrypoint(self.workspace, entrypoint)
        runner = (
            crew.kickoff_async(inputs=inputs)
            if hasattr(crew, "kickoff_async")
            else asyncio.to_thread(crew.kickoff, inputs=inputs)
        )
        runner_task = asyncio.create_task(runner)  # type: ignore[arg-type]

        async with AuditSession(run_id=run_id, store=self._audit_store) as session:
            session.log_run_started(runtime="crewai", mode=RuntimeMode.gated_local)

            with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
                while not runner_task.done() or not queue.empty():
                    try:
                        native = await asyncio.wait_for(queue.get(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue
                    for ag in map_event("crewai", native, ctx):
                        t.write(ag)
                        a.append(ag)
                        log_agui_to_audit(session, ag)
                await runner_task

            session.log_run_completed(runtime="crewai")

        return run_id
