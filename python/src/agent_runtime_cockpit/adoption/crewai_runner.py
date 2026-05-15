"""CrewAI + SwarmGraph adoption runner."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator

from .ag2_runner import AG2AdoptionRunner
from .langgraph_runner import _setup_swarmgraph_paths
from .protocol import AdoptionCapability, AdoptionMode, AdoptionRunner, AdoptionSpec, AdoptionStatus, ConsensusResult, WorkerProposal


class CrewAIAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.CREWAI

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            import crewai
            _setup_swarmgraph_paths()
            from swarm.nodes.consensus import consensus_node  # noqa: F401

            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason=f"CrewAI {getattr(crewai, '__version__', 'unknown')} and vendored SwarmGraph consensus detected",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="CrewAI not installed",
                doctor_actions=[{"id": "install_crewai", "label": "Install CrewAI", "description": "pip install crewai", "command": "pip install crewai"}],
            )

    async def run(self, spec: AdoptionSpec, run_id: str, emit_event) -> ConsensusResult:
        crew = spec.runtime_config.get("crew")
        if crew is None:
            raise ValueError("CrewAI adoption requires spec.runtime_config['crew']")
        inputs = spec.runtime_config.get("inputs", {})
        emit_event(run_id, "STEP_STARTED", {"step": "crewai_kickoff", "mode": self.mode.value})
        result = await self._kickoff(crew, inputs)
        proposals = self._proposals(result)
        emit_event(run_id, "STEP_COMPLETED", {"step": "crewai_kickoff", "proposals": len(proposals)})
        emit_event(run_id, "STEP_STARTED", {"step": "consensus", "swarmgraph": True})
        consensus = AG2AdoptionRunner()._consensus(proposals)
        emit_event(run_id, "STEP_COMPLETED", {"step": "consensus", "swarmgraph": True, "confidence": consensus.confidence})
        return consensus

    async def _kickoff(self, crew: Any, inputs: dict[str, Any]) -> Any:
        if hasattr(crew, "akickoff"):
            return await crew.akickoff(inputs=inputs)
        if hasattr(crew, "kickoff_async"):
            return await crew.kickoff_async(inputs=inputs)
        if hasattr(crew, "kickoff"):
            return await asyncio.to_thread(crew.kickoff, inputs=inputs)
        raise RuntimeError("CrewAI object exposes no kickoff method")

    def _proposals(self, result: Any) -> list[WorkerProposal]:
        tasks = getattr(result, "tasks_output", None)
        proposals: list[WorkerProposal] = []
        if tasks:
            for index, task in enumerate(tasks):
                output = getattr(task, "raw", None) or str(task)
                agent = getattr(task, "agent", None) or getattr(task, "agent_role", None) or f"crew-agent-{index + 1}"
                proposals.append(WorkerProposal(task_id=f"crew-task-{index + 1}", worker_id=str(agent), output=str(output), confidence=1.0, metadata={"runtime": "crewai", "swarmgraph_role": "coder"}))
        if not proposals:
            output = getattr(result, "raw", None) or str(result)
            proposals.append(WorkerProposal(task_id="crew-output", worker_id="crew", output=str(output), confidence=1.0, metadata={"runtime": "crewai", "swarmgraph_role": "coder"}))
        return proposals

    async def stream_worker_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
