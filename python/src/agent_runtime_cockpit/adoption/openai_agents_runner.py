"""OpenAI Agents + SwarmGraph adoption runner."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, AsyncIterator

from .ag2_runner import AG2AdoptionRunner
from .langgraph_runner import _setup_swarmgraph_paths
from .protocol import (
    AdoptionCapability,
    AdoptionMode,
    AdoptionRunner,
    AdoptionSpec,
    AdoptionStatus,
    ConsensusResult,
    WorkerProposal,
)


class OpenAIAgentsAdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.OPENAI_AGENTS

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            if importlib.util.find_spec("agents") is None:
                raise ImportError("agents")
            _setup_swarmgraph_paths()

            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason="OpenAI Agents SDK package detected; SwarmGraph adoption path is fake-tested/gated",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="OpenAI Agents SDK not installed",
                doctor_actions=[
                    {
                        "id": "install_agents",
                        "label": "Install OpenAI Agents SDK",
                        "description": "pip install openai-agents",
                        "command": "pip install openai-agents",
                    }
                ],
            )

    async def run(self, spec: AdoptionSpec, run_id: str, emit_event) -> ConsensusResult:
        agent = spec.runtime_config.get("agent")
        if agent is None:
            raise ValueError("OpenAI Agents adoption requires spec.runtime_config['agent']")
        prompt = str(spec.runtime_config.get("prompt") or spec.runtime_config.get("input") or "")
        if not prompt.strip():
            raise ValueError("OpenAI Agents adoption requires non-empty prompt/input")
        runner = spec.runtime_config.get("runner")

        emit_event(run_id, "STEP_STARTED", {"step": "openai_agents_run", "mode": self.mode.value})
        output = await self._run_agent(agent, prompt, runner)
        proposal = WorkerProposal(
            task_id="openai-agent",
            worker_id=getattr(agent, "name", "openai-agent"),
            output=output,
            confidence=1.0,
            metadata={"runtime": "openai-agents", "swarmgraph_role": "coder"},
        )
        emit_event(
            run_id,
            "WORKER_COMPLETED",
            {
                "task_id": proposal.task_id,
                "worker_id": proposal.worker_id,
                "output_length": len(output),
            },
        )
        emit_event(run_id, "STEP_COMPLETED", {"step": "openai_agents_run", "proposals": 1})
        emit_event(run_id, "STEP_STARTED", {"step": "consensus", "swarmgraph": True})
        consensus = AG2AdoptionRunner()._consensus([proposal])
        emit_event(
            run_id,
            "STEP_COMPLETED",
            {"step": "consensus", "swarmgraph": True, "confidence": consensus.confidence},
        )
        return consensus

    async def _run_agent(self, agent: Any, prompt: str, runner: Any | None) -> str:
        if runner is None:
            from agents import Runner

            runner = Runner
        run = getattr(runner, "run", None) or getattr(runner, "run_sync", None)
        if run is None:
            raise RuntimeError("OpenAI Agents Runner exposes no run/run_sync method")
        result = run(agent, prompt)
        if inspect.isawaitable(result):
            result = await result
        output = getattr(result, "final_output", None) or getattr(result, "output", None) or result
        return str(output)

    async def stream_worker_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}
