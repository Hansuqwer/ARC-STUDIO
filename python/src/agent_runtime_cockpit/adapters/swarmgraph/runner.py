"""Real SwarmGraph execution path with dual-gating, audit chain and AG-UI emission."""

from __future__ import annotations

import datetime as dt
import os
import pathlib
import uuid
from typing import Any, AsyncIterator

from agent_runtime_cockpit.ag_ui import map_event, MappingContext, AGUIEventType
from agent_runtime_cockpit.audit.chain import AuditChainWriter
from agent_runtime_cockpit.audit.runner_integration import log_agui_to_audit
from agent_runtime_cockpit.audit.session import AuditSession
from agent_runtime_cockpit.audit.schema import RuntimeMode
from agent_runtime_cockpit.audit.storage import AuditChainStore
from agent_runtime_cockpit.gating import require_dual_gate, BackendMode
from agent_runtime_cockpit.tracing.jsonl_writer import JsonlTraceWriter

import agent_runtime_cockpit.adapters.swarmgraph.mapping  # noqa: F401


class SwarmGraphRunner:
    """Provider-backed runner. Supports backends: stub | local | gateway."""

    def __init__(self, workspace: pathlib.Path) -> None:
        self.workspace = workspace
        self.traces_dir = workspace / ".arc" / "traces"
        self.audit_dir = workspace / ".arc" / "audit"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self._audit_store = AuditChainStore(audit_dir=self.audit_dir)

    async def run(self, entrypoint: str, inputs: dict[str, Any]) -> str:
        run_id = uuid.uuid4().hex[:12]
        thread_id = f"th-{run_id}"
        backend, allow_costs = require_dual_gate("SWARMGRAPH")

        # Map backend to RuntimeMode
        runtime_mode = RuntimeMode.gated_local  # default
        if backend == BackendMode.STUB:
            runtime_mode = RuntimeMode.fake
        elif backend == BackendMode.GATEWAY:
            runtime_mode = RuntimeMode.provider_backed

        trace_path = self.traces_dir / f"{run_id}.jsonl"
        audit_path = self.audit_dir / f"{run_id}.chain.jsonl"

        async with AuditSession(run_id=run_id, store=self._audit_store) as session:
            session.log_run_started(runtime="swarmgraph", mode=runtime_mode)

            with JsonlTraceWriter(trace_path) as trace, AuditChainWriter(audit_path) as audit:
                ctx = MappingContext(thread_id=thread_id, run_id=run_id, runtime="swarmgraph")

                if backend != BackendMode.STUB and allow_costs:
                    warning = {
                        "type": AGUIEventType.CUSTOM.value,
                        "name": "arc.cost_warning",
                        "value": {
                            "runtime": "swarmgraph",
                            "backend": backend.value,
                            "estimated_provider": os.environ.get(
                                "ARC_SWARMGRAPH_PROVIDER", "unknown"
                            ),
                            "gated_at": dt.datetime.now(dt.timezone.utc)
                            .isoformat()
                            .replace("+00:00", "Z"),
                        },
                    }
                    trace.write(warning)
                    audit.append(warning)

                async for native in self._produce(backend, entrypoint, inputs):
                    for ag in map_event("swarmgraph", native, ctx):
                        trace.write(ag)
                        audit.append(ag)
                        log_agui_to_audit(session, ag)

            session.log_run_completed(runtime="swarmgraph")

        return run_id

    async def _produce(
        self, backend: BackendMode, entrypoint: str, inputs: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        if backend is BackendMode.STUB:
            async for e in self._stub_events():
                yield e
            return
        if backend is BackendMode.LOCAL:
            async for e in self._local_events(entrypoint, inputs):
                yield e
            return
        if backend is BackendMode.GATEWAY:
            async for e in self._gateway_events(entrypoint, inputs):
                yield e
            return
        raise RuntimeError(f"unknown backend {backend!r}")

    async def _stub_events(self) -> AsyncIterator[dict[str, Any]]:
        yield {"kind": "run.start", "ts": 1}
        yield {"kind": "agent.text", "ts": 2, "agent": "queen", "text": "stub run"}
        yield {"kind": "run.finish", "ts": 3}

    async def _local_events(
        self, entrypoint: str, inputs: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        from agent_runtime_cockpit.adapters.swarmgraph.local_executor import LocalSwarmExecutor

        executor = LocalSwarmExecutor(self.workspace)
        async for native in executor.execute(entrypoint, inputs):
            yield native

    async def _gateway_events(
        self, entrypoint: str, inputs: dict[str, Any]
    ) -> AsyncIterator[dict[str, Any]]:
        from agent_runtime_cockpit.adapters.swarmgraph.gateway_client import GatewayClient

        async with GatewayClient.from_env() as client:
            async for native in client.run_stream(entrypoint, inputs):
                yield native
