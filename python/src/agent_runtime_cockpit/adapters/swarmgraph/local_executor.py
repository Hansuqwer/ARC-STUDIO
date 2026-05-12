"""Local in-process SwarmGraph executor. Real, not stub."""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator
import pathlib

from agent_runtime_cockpit.workspace.entrypoint import resolve_python_entrypoint


class LocalSwarmExecutor:
    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace

    async def execute(self, entrypoint: str, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        obj = resolve_python_entrypoint(self.workspace, entrypoint)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def emit(kind: str, **payload: Any) -> None:
            queue.put_nowait({"kind": kind, "ts": time.time(), **payload})

        emit("run.start")
        try:
            if hasattr(obj, "run_with_emit"):
                runner_task = asyncio.create_task(obj.run_with_emit(inputs, emit))
            else:
                async def _legacy() -> None:
                    result = await obj.run(inputs) if asyncio.iscoroutinefunction(obj.run) else obj.run(inputs)
                    emit("agent.text", agent="root", text=str(result))
                runner_task = asyncio.create_task(_legacy())

            while not runner_task.done() or not queue.empty():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield item
                except asyncio.TimeoutError:
                    continue
            await runner_task
        except Exception as exc:
            yield {"kind": "run.error", "ts": time.time(), "error": {"code": "LOCAL_EXC", "message": str(exc)}}
            return
        yield {"kind": "run.finish", "ts": time.time()}
