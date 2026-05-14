"""AG2 adapter. Uses a_run_group_chat → async event iterator."""
from __future__ import annotations

import pathlib
import uuid
from typing import Any

from agent_runtime_cockpit.ag_ui import MappingContext, map_event
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.gating import require_dual_gate
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter
from agent_runtime_cockpit.workspace.entrypoint import resolve_python_entrypoint

from . import mapping  # noqa: F401


class AG2Runner:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace

    async def run(self, entrypoint: str, message: str) -> str:
        require_dual_gate("AG2")
        run_id = uuid.uuid4().hex[:12]
        ctx = MappingContext(thread_id=f"th-{run_id}", run_id=run_id, runtime="ag2")

        traces = self.workspace / ".arc" / "traces" / f"{run_id}.jsonl"
        audit = self.workspace / ".arc" / "audit" / f"{run_id}.chain.jsonl"
        traces.parent.mkdir(parents=True, exist_ok=True)
        audit.parent.mkdir(parents=True, exist_ok=True)

        team = resolve_python_entrypoint(self.workspace, entrypoint)

        with JsonlTraceWriter(traces) as t, AuditChainWriter(audit) as a:
            for ag in map_event("ag2", {"event": "run.start"}, ctx):
                t.write(ag); a.append(ag)
            try:
                async for native in self._stream(team, message):
                    for ag in map_event("ag2", native, ctx):
                        t.write(ag); a.append(ag)
            except Exception as exc:
                for ag in map_event("ag2", {"event": "run.error", "message": str(exc)}, ctx):
                    t.write(ag); a.append(ag)
            for ag in map_event("ag2", {"event": "run.finish"}, ctx):
                t.write(ag); a.append(ag)
        return run_id

    async def _stream(self, team: Any, message: str):
        if hasattr(team, "a_run_group_chat"):
            response = await team.a_run_group_chat(messages=[{"role": "user", "content": message}])
            async for ev in response.events:
                yield {
                    "event": "message",
                    "sender": getattr(ev, "sender", None),
                    "content": getattr(ev, "content", str(ev)),
                }
            return
        if hasattr(team, "run_stream"):
            async for ev in team.run_stream(task=message):
                yield {"event": "message",
                       "sender": getattr(ev, "source", None),
                       "content": getattr(ev, "content", str(ev))}
            return
        raise RuntimeError("AG2 entrypoint exposes neither a_run_group_chat nor run_stream")
