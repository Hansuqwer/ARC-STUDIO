"""
LangGraph + SwarmGraph adoption runner baseline (P2).

Executes a compiled LangGraph graph as SwarmGraph-decomposed worker tasks,
then runs vendored SwarmGraph consensus over worker proposals. HMAC audit
remains separate; this runner does not claim signed adoption audit.
"""
from __future__ import annotations

import logging
import sys
import time
import warnings
from pathlib import Path
from typing import Any, AsyncIterator

from .protocol import (
    AdoptionMode,
    AdoptionSpec,
    AdoptionCapability,
    AdoptionStatus,
    AdoptionRunner,
    ConsensusResult,
    WorkerProposal,
    Vote,
)

log = logging.getLogger(__name__)

# SwarmGraph vendored packages path
_SWARM_SHARED_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "runtimes" / "swarmgraph" / "packages" / "swarm-shared"
)
_HIVE_SWARM_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "runtimes" / "swarmgraph" / "packages" / "hive-swarm"
)


def _setup_swarmgraph_paths() -> None:
    """Add vendored SwarmGraph packages to sys.path if available."""
    for p in (_SWARM_SHARED_PATH, _HIVE_SWARM_PATH):
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))


class LangGraphAdoptionRunner(AdoptionRunner):
    """Adoption runner baseline for LangGraph + SwarmGraph.

    Executes a LangGraph ``CompiledStateGraph`` within the ARC adoption
    framework. The graph is invoked once and its final output becomes the
    winning proposal. SwarmGraph queen/worker orchestration remains future work.
    """

    @property
    def mode(self) -> AdoptionMode:
        return AdoptionMode.LANGGRAPH

    def check_availability(self, workspace: Path) -> AdoptionCapability:
        """Report RUNNABLE when LangGraph and vendored SwarmGraph imports work."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import langgraph  # noqa: F401
                _setup_swarmgraph_paths()
                from swarm.models.config import SwarmConfig  # noqa: F401
                from swarm.models.state import SwarmState  # noqa: F401
                from swarm.nodes.consensus import consensus_node  # noqa: F401
                from swarm.nodes.queen import queen_decompose_node  # noqa: F401

            version = getattr(langgraph, "__version__", "unknown")
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason=f"LangGraph {version} and vendored SwarmGraph queen/consensus detected",
                doctor_actions=[],
            )
        except ImportError:
            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.NOT_RUNNABLE,
                reason="LangGraph package not installed.",
                doctor_actions=[{
                    "id": "install-langgraph",
                    "label": "Install LangGraph",
                    "description": "Install LangGraph with: pip install langgraph",
                }],
            )

    async def run(
        self,
        spec: AdoptionSpec,
        run_id: str,
        emit_event,
    ) -> ConsensusResult:
        """Execute a LangGraph graph and return SwarmGraph-backed consensus.

        The graph must be provided via ``spec.runtime_config["graph"]``
        as an already-compiled ``CompiledStateGraph`` instance.
        Input is taken from ``spec.runtime_config.get("input", {})``.

        Flow:
        1. Load the compiled graph from the spec.
        2. Invoke the graph with the provided input.
        3. Use vendored SwarmGraph queen decomposition to create worker tasks.
        4. Invoke the LangGraph graph once per assigned task.
        5. Use vendored SwarmGraph consensus over worker votes.
        """
        _setup_swarmgraph_paths()
        emit_event(run_id, "STEP_STARTED", {
            "step": "load_graph",
            "mode": self.mode.value,
        })

        graph = spec.runtime_config.get("graph")
        if graph is None:
            emit_event(run_id, "RUN_FAILED", {
                "error": "No LangGraph graph provided. "
                         "Pass a compiled graph via spec.runtime_config['graph'].",
                "mode": self.mode.value,
            })
            raise ValueError(
                "No LangGraph graph provided. "
                "Pass a compiled graph via spec.runtime_config['graph']."
            )

        graph_input = spec.runtime_config.get("input", {})
        max_workers = spec.max_workers
        emit_event(run_id, "STEP_COMPLETED", {
            "step": "load_graph",
            "graph_type": type(graph).__name__,
            "max_workers": max_workers,
        })

        # ── Queen plan ────────────────────────────────────────────────
        emit_event(run_id, "STEP_STARTED", {
            "step": "queen_plan",
            "description": "Using vendored SwarmGraph queen decomposition",
        })

        tasks, swarm_state = self._queen_decompose(
            objective=str(spec.runtime_config.get("objective") or graph_input or spec.mode.value),
            graph_input=graph_input,
            max_workers=max_workers,
            run_id=run_id,
        )
        emit_event(run_id, "STEP_COMPLETED", {
            "step": "queen_plan",
            "num_tasks": len(tasks),
            "swarmgraph": True,
        })

        # ── Execute ────────────────────────────────────────────────────
        worker_proposals: list[WorkerProposal] = []
        for task in tasks:
            emit_event(run_id, "WORKER_RUNNING", {
                "task_id": task["task_id"],
                "worker_id": task["worker_id"],
            })

            worker_output = await self._run_graph(graph, task["input"], run_id, emit_event)

            proposal = WorkerProposal(
                task_id=task["task_id"],
                worker_id=task["worker_id"],
                output=worker_output,
                confidence=1.0,
                metadata={"runtime": "langgraph", "swarmgraph_role": task.get("role", "worker")},
            )
            worker_proposals.append(proposal)

            emit_event(run_id, "WORKER_COMPLETED", {
                "task_id": task["task_id"],
                "worker_id": task["worker_id"],
                "output_length": len(worker_output),
            })

        # ── SwarmGraph consensus ───────────────────────────────────────
        emit_event(run_id, "STEP_STARTED", {
            "step": "consensus",
            "num_proposals": len(worker_proposals),
            "swarmgraph": True,
        })

        result = self._swarmgraph_consensus(swarm_state, worker_proposals)

        emit_event(run_id, "STEP_COMPLETED", {
            "step": "consensus",
            "consensus_reached": True,
            "confidence": result.confidence,
            "votes": len(result.votes),
            "swarmgraph": True,
        })

        emit_event(run_id, "RUN_COMPLETED", {
            "task_id": result.task_id,
            "consensus_reached": result.consensus_reached,
            "confidence": result.confidence,
        })

        return result

    def _queen_decompose(
        self,
        objective: str,
        graph_input: dict[str, Any],
        max_workers: int,
        run_id: str,
    ) -> tuple[list[dict[str, Any]], Any]:
        """Use vendored SwarmGraph queen node to create worker tasks."""
        from swarm.models.config import SwarmConfig
        from swarm.models.state import SwarmState
        from swarm.nodes.queen import queen_decompose_node

        config = SwarmConfig(max_agents=max(1, max_workers), topology="hierarchical")
        state = SwarmState(swarm_id=run_id.replace(":", "-"), objective=objective, config=config)
        decomposed = queen_decompose_node(state.to_json_dict())
        swarm_state = SwarmState.from_json_dict(decomposed)
        tasks: list[dict[str, Any]] = []
        for task in swarm_state.tasks:
            assigned = task.assigned_to or task.task_id
            agent = next((item for item in swarm_state.agents if item.agent_id == assigned), None)
            tasks.append({
                "task_id": task.task_id,
                "worker_id": assigned,
                "role": agent.role if agent else "worker",
                "input": {**graph_input, "swarmgraph_task": task.description},
            })
        if not tasks:
            tasks.append({"task_id": "task-1", "worker_id": "worker-1", "role": "worker", "input": graph_input})
        return tasks, swarm_state

    def _swarmgraph_consensus(
        self,
        swarm_state: Any,
        proposals: list[WorkerProposal],
    ) -> ConsensusResult:
        """Run vendored SwarmGraph consensus over proposal votes."""
        from swarm.models.agent import AgentVote
        from swarm.models.state import SwarmState
        from swarm.nodes.consensus import consensus_node

        for proposal in proposals:
            swarm_state.pending_votes.append(AgentVote(
                agent_id=proposal.worker_id,
                agent_role=proposal.metadata.get("swarmgraph_role", "coder"),
                proposed_action=proposal.output[:2048] or "No output",
                confidence=proposal.confidence,
                rationale="LangGraph adoption worker proposal",
            ))
        final = SwarmState.from_json_dict(consensus_node(swarm_state.to_json_dict()))
        winning = proposals[0]
        if final.consensus_result and final.consensus_result.action:
            winning = next(
                (proposal for proposal in proposals if proposal.output[:2048] == final.consensus_result.action),
                winning,
            )
        votes = [
            Vote(
                task_id=proposal.task_id,
                voter_id=proposal.worker_id,
                proposal_id=f"{proposal.task_id}-{proposal.worker_id}",
                score=proposal.confidence,
                reason="Vendored SwarmGraph consensus vote",
            )
            for proposal in proposals
        ]
        agreement = (
            final.consensus_result.agreement_fraction
            if final.consensus_result is not None else 0.0
        )
        return ConsensusResult(
            task_id=winning.task_id,
            winning_proposal=winning,
            votes=votes,
            consensus_reached=final.status != "failed",
            confidence=agreement,
        )

    async def _run_graph(
        self,
        graph: Any,
        input_data: dict[str, Any],
        run_id: str,
        emit_event,
    ) -> str:
        """Invoke a compiled LangGraph graph and return the string output.

        Handles both sync and async graphs.  Attempts to use
        ``astream_events`` (v2) when available for fine-grained events.
        """
        emit_event(run_id, "WORKER_EVENT", {
            "message": "Invoking LangGraph graph",
        })

        t0 = time.time()

        try:
            # Try async invocation first
            import inspect
            if inspect.isasyncgenfunction(getattr(graph, "astream_events", None)):
                output = await self._run_async_stream(graph, input_data, run_id, emit_event)
            elif inspect.iscoroutinefunction(graph.ainvoke):
                result = await graph.ainvoke(input_data)
                output = str(result) if result is not None else ""
            else:
                result = graph.invoke(input_data)
                output = str(result) if result is not None else ""
        except Exception as exc:
            emit_event(run_id, "RUN_FAILED", {
                "error": f"LangGraph execution error: {exc}",
            })
            raise

        elapsed = time.time() - t0
        emit_event(run_id, "WORKER_EVENT", {
            "message": f"Graph completed in {elapsed:.2f}s",
            "output_length": len(output),
        })

        return output

    async def _run_async_stream(
        self,
        graph: Any,
        input_data: dict[str, Any],
        run_id: str,
        emit_event,
    ) -> str:
        """Run graph via ``astream_events`` (v2) for structured event output."""
        output_parts: list[str] = []
        try:
            async for event in graph.astream_events(input_data, version="v2"):
                kind = event.get("event", "")
                if kind == "on_chain_end":
                    data = event.get("data", {})
                    output = data.get("output", "")
                    if output:
                        output_parts.append(str(output))
                elif kind in ("on_chain_start", "on_chat_model_start"):
                    metadata = event.get("metadata", {})
                    langgraph_node = metadata.get("langgraph_node", "")
                    if langgraph_node:
                        emit_event(run_id, "WORKER_EVENT", {
                            "message": f"Node: {langgraph_node}",
                            "node": langgraph_node,
                        })
        except Exception:
            # Fallback to simple invoke if streaming fails
            result = await graph.ainvoke(input_data)
            if result is not None:
                output_parts.append(str(result))

        return "\n".join(output_parts) if output_parts else ""

    async def stream_worker_events(
        self,
        run_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield stored worker events for the given run (future use)."""
        if False:
            yield {}
        raise NotImplementedError(
            "Worker event streaming not yet implemented for LangGraph adoption"
        )
