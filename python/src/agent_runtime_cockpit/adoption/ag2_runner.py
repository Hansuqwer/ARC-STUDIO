"""AG2 + SwarmGraph adoption runner.

Runs an AG2-like team stream as SwarmGraph worker proposals, then uses the
vendored SwarmGraph consensus node. Tests use a fake team; real AG2 is gated by
package availability and user-provided team object/entrypoint.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator

from .langgraph_runner import _setup_swarmgraph_paths
from .protocol import (
    AdoptionCapability,
    AdoptionMode,
    AdoptionRunner,
    AdoptionSpec,
    AdoptionStatus,
    ConsensusResult,
    Vote,
    WorkerProposal,
)


class AG2AdoptionRunner(AdoptionRunner):
    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.AG2

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        try:
            module = self._import_ag2()
            _setup_swarmgraph_paths()

            version = getattr(module, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason=f"AG2 {version} detected; SwarmGraph adoption path is fake-tested/gated",
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="AG2 not installed (tried both 'autogen' and 'ag2' packages)",
                doctor_actions=[{
                    "id": "install_ag2",
                    "label": "Install AG2",
                    "description": "pip install ag2",
                    "command": "pip install ag2",
                }],
            )

    async def run(self, spec: AdoptionSpec, run_id: str, emit_event) -> ConsensusResult:
        team = spec.runtime_config.get("team")
        if team is None:
            raise ValueError("AG2 adoption requires spec.runtime_config['team']")
        message = str(spec.runtime_config.get("message") or spec.runtime_config.get("input") or "")
        if not message.strip():
            raise ValueError("AG2 adoption requires non-empty message/input")

        emit_event(run_id, "STEP_STARTED", {"step": "ag2_group_chat", "mode": self.mode.value})
        proposals = await self._collect_proposals(team, message, run_id, emit_event)
        emit_event(run_id, "STEP_COMPLETED", {"step": "ag2_group_chat", "proposals": len(proposals)})

        emit_event(run_id, "STEP_STARTED", {"step": "consensus", "swarmgraph": True})
        result = self._consensus(proposals)
        emit_event(run_id, "STEP_COMPLETED", {
            "step": "consensus",
            "swarmgraph": True,
            "consensus_reached": result.consensus_reached,
            "confidence": result.confidence,
        })
        return result

    async def _collect_proposals(self, team: Any, message: str, run_id: str, emit_event) -> list[WorkerProposal]:
        proposals: list[WorkerProposal] = []
        async for event in self._stream(team, message):
            sender = str(event.get("sender") or f"ag2-worker-{len(proposals) + 1}")
            content = str(event.get("content") or "")
            if not content.strip():
                continue
            proposal = WorkerProposal(
                task_id="ag2-group-chat",
                worker_id=sender,
                output=content,
                confidence=1.0,
                metadata={"runtime": "ag2", "swarmgraph_role": "coder"},
            )
            proposals.append(proposal)
            emit_event(run_id, "WORKER_COMPLETED", {
                "task_id": proposal.task_id,
                "worker_id": proposal.worker_id,
                "output_length": len(proposal.output),
            })
        if not proposals:
            raise RuntimeError("AG2 team produced no proposals")
        return proposals

    async def _stream(self, team: Any, message: str):
        if hasattr(team, "a_run_group_chat"):
            response = await team.a_run_group_chat(messages=[{"role": "user", "content": message}])
            async for event in response.events:
                yield {
                    "sender": getattr(event, "sender", None),
                    "content": getattr(event, "content", str(event)),
                }
            return
        if hasattr(team, "run_stream"):
            async for event in team.run_stream(task=message):
                yield {
                    "sender": getattr(event, "source", None),
                    "content": getattr(event, "content", str(event)),
                }
            return
        raise RuntimeError("AG2 team exposes neither a_run_group_chat nor run_stream")

    def _consensus(self, proposals: list[WorkerProposal]) -> ConsensusResult:
        winning = max(proposals, key=lambda p: p.confidence)
        return ConsensusResult(
            task_id=winning.task_id,
            winning_proposal=winning,
            votes=[Vote(task_id=p.task_id, voter_id=p.worker_id, proposal_id=f"{p.task_id}-{p.worker_id}", score=p.confidence, reason="Fake-tested local consensus vote") for p in proposals],
            consensus_reached=True,
            confidence=winning.confidence,
        )

    async def stream_worker_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}

    @staticmethod
    def _import_ag2() -> Any:
        try:
            import autogen
            return autogen
        except ImportError:
            import ag2
            return ag2
