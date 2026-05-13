"""CrewAI runner. Real execution gated; events come from listener."""
from __future__ import annotations

import asyncio
import pathlib
import uuid
from typing import Any

from agent_runtime_cockpit.ag_ui import MappingContext, map_event
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter
from agent_runtime_cockpit.workspace.entrypoint import resolve_python_entrypoint

from .listener import ArcCrewAIListener
from . import mapping  # noqa: F401


class CrewAIRunner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace

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
        runner = crew.kickoff_async(inputs=inputs) if hasattr(crew, "kickoff_async") \
            else asyncio.to_thread(crew.kickoff, inputs=inputs)
        runner_task = asyncio.create_task(runner)  # type: ignore[arg-type]

        with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
            while not runner_task.done() or not queue.empty():
                try:
                    native = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                for ag in map_event("crewai", native, ctx):
                    t.write(ag)
                    a.append(ag)
            await runner_task
        return run_id
