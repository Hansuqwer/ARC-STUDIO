"""LlamaIndex + SwarmGraph adoption runner."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, AsyncIterator

from .ag2_runner import AG2AdoptionRunner
from .langgraph_runner import _setup_swarmgraph_paths
from .protocol import AdoptionCapability, AdoptionMode, AdoptionRunner, AdoptionSpec, AdoptionStatus, ConsensusResult, WorkerProposal


class LlamaIndexAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.LLAMAINDEX

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            import llama_index
            _setup_swarmgraph_paths()
            from swarm.nodes.consensus import consensus_node  # noqa: F401

            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason=f"LlamaIndex {getattr(llama_index, '__version__', 'unknown')} and vendored SwarmGraph consensus detected",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="LlamaIndex not installed",
                doctor_actions=[{"id": "install_llamaindex", "label": "Install LlamaIndex", "description": "pip install llama-index", "command": "pip install llama-index"}],
            )

    async def run(self, spec: AdoptionSpec, run_id: str, emit_event) -> ConsensusResult:
        target = spec.runtime_config.get("workflow") or spec.runtime_config.get("query_engine") or spec.runtime_config.get("agent")
        if target is None:
            raise ValueError("LlamaIndex adoption requires workflow/query_engine/agent in runtime_config")
        query = str(spec.runtime_config.get("query") or spec.runtime_config.get("input") or "")
        if not query.strip():
            raise ValueError("LlamaIndex adoption requires non-empty query/input")
        emit_event(run_id, "STEP_STARTED", {"step": "llamaindex_run", "mode": self.mode.value})
        output = await self._run_target(target, query)
        proposal = WorkerProposal(task_id="llamaindex-query", worker_id="llamaindex", output=output, confidence=1.0, metadata={"runtime": "llamaindex", "swarmgraph_role": "researcher"})
        emit_event(run_id, "WORKER_COMPLETED", {"task_id": proposal.task_id, "worker_id": proposal.worker_id, "output_length": len(output)})
        emit_event(run_id, "STEP_COMPLETED", {"step": "llamaindex_run", "proposals": 1})
        emit_event(run_id, "STEP_STARTED", {"step": "consensus", "swarmgraph": True})
        consensus = AG2AdoptionRunner()._consensus([proposal])
        emit_event(run_id, "STEP_COMPLETED", {"step": "consensus", "swarmgraph": True, "confidence": consensus.confidence})
        return consensus

    async def _run_target(self, target: Any, query: str) -> str:
        method = None
        for name in ("aquery", "query", "achat", "chat", "arun", "run"):
            candidate = getattr(target, name, None)
            if candidate is not None:
                method = candidate
                break
        if method is None:
            raise RuntimeError("LlamaIndex target exposes no query/chat/run method")
        result = method(query)
        if inspect.isawaitable(result):
            result = await result
        return str(getattr(result, "response", None) or result)

    async def stream_worker_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
