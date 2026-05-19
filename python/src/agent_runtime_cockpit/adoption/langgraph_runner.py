"""
LangGraph + SwarmGraph adoption runner baseline (P2).

Executes a compiled LangGraph graph as SwarmGraph-decomposed worker tasks,
then runs vendored SwarmGraph consensus over worker proposals. HMAC audit
remains separate; this runner does not claim signed adoption audit.
"""
from __future__ import annotations

import logging
import importlib.util
import os
import sys
import time
import warnings
from datetime import datetime, timezone
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

_LOCAL_REAL_MODE = "local-real"
_REAL_RUNTIME_SMOKE_ENV = "ARC_REAL_RUNTIME_SMOKE"
_LOCAL_REAL_GATE_ENV = "ARC_LANGGRAPH_SWARMGRAPH_REAL"

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
                if importlib.util.find_spec("langgraph") is None:
                    raise ImportError("langgraph")
                _setup_swarmgraph_paths()
                has_vendored_swarmgraph = _SWARM_SHARED_PATH.exists() and _HIVE_SWARM_PATH.exists()

            return AdoptionCapability(
                mode=self.mode,
                status=AdoptionStatus.RUNNABLE,
                reason=(
                    "LangGraph package detected; vendored SwarmGraph paths available; "
                    "adoption path is fake-tested/gated"
                    if has_vendored_swarmgraph
                    else "LangGraph package detected; SwarmGraph adoption path is fake-tested/gated"
                ),
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
        offline_deterministic = (
            spec.runtime_config.get("offline_deterministic") is True
            or (spec.runtime_config.get("offline") is True and spec.runtime_config.get("fake") is True)
        )
        local_real = self._is_local_real(spec)
        if local_real:
            emit_event = self._local_no_provider_emit(emit_event)
        if local_real and not self._local_real_gate_open():
            emit_event(run_id, "RUN_FAILED", {
                "error": (
                    "LangGraph+SwarmGraph local-real mode requires "
                    f"{_REAL_RUNTIME_SMOKE_ENV}=1 and {_LOCAL_REAL_GATE_ENV}=1; "
                    "no provider calls were made."
                ),
                "mode": self.mode.value,
                "runtime_mode": _LOCAL_REAL_MODE,
                "real_provider_call": False,
                "provider_backed": False,
            })
            raise PermissionError(
                "LangGraph+SwarmGraph local-real mode requires "
                f"{_REAL_RUNTIME_SMOKE_ENV}=1 and {_LOCAL_REAL_GATE_ENV}=1; "
                "no provider calls were made."
            )
        if not offline_deterministic:
            _setup_swarmgraph_paths()
        emit_event(run_id, "STEP_STARTED", {
            "step": "load_graph",
            "mode": self.mode.value,
            "runtime_mode": _LOCAL_REAL_MODE if local_real else None,
            "real_provider_call": False,
            "provider_backed": False,
        })

        graph = spec.runtime_config.get("graph")
        if graph is None and offline_deterministic:
            graph = _OfflineDeterministicLangGraph(
                spec.runtime_config.get("objective")
                or spec.runtime_config.get("prompt")
                or self.mode.value
            )
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

        objective = str(spec.runtime_config.get("objective") or graph_input or spec.mode.value)
        if offline_deterministic:
            tasks, swarm_state = self._offline_queen_decompose(objective, graph_input, max_workers)
        else:
            tasks, swarm_state = self._queen_decompose(
                objective=objective,
                graph_input=graph_input,
                max_workers=max_workers,
                run_id=run_id,
            )
        emit_event(run_id, "SWARMGRAPH_TOPOLOGY", self._topology_payload(tasks))
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
                metadata={
                    "runtime": "langgraph",
                    "swarmgraph_role": task.get("role", "worker"),
                    "runtime_mode": _LOCAL_REAL_MODE if local_real else "fake/offline" if offline_deterministic else "gated",
                    "real_provider_call": False,
                    "provider_backed": False,
                },
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

        result = (
            self._offline_consensus(worker_proposals)
            if offline_deterministic
            else self._swarmgraph_consensus(swarm_state, worker_proposals)
        )
        if local_real and (
            result.metadata.get("real_provider_call") is True
            or result.metadata.get("provider_backed") is True
        ):
            raise RuntimeError(
                "LangGraph+SwarmGraph local-real path cannot claim provider-backed calls"
            )
        result.metadata.update({
            "runtime_mode": _LOCAL_REAL_MODE if local_real else result.metadata.get("runtime_mode", "gated"),
            "real_provider_call": False,
            "provider_backed": False,
        })
        emit_event(run_id, "SWARMGRAPH_CONSENSUS", self._consensus_payload(result))
        cost_payload = self._measured_cost_payload(spec.runtime_config)
        if cost_payload is not None:
            emit_event(run_id, "SWARMGRAPH_COST", cost_payload)

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
            "runtime_mode": result.metadata.get("runtime_mode"),
            "real_provider_call": False,
            "provider_backed": False,
        })

        return result

    def _is_local_real(self, spec: AdoptionSpec) -> bool:
        return (
            spec.runtime_config.get("mode") == _LOCAL_REAL_MODE
            or spec.runtime_config.get("runtime_mode") == _LOCAL_REAL_MODE
            or spec.runtime_config.get("adoption_mode") == _LOCAL_REAL_MODE
        )

    def _local_real_gate_open(self) -> bool:
        return (
            os.environ.get(_REAL_RUNTIME_SMOKE_ENV) == "1"
            and os.environ.get(_LOCAL_REAL_GATE_ENV) == "1"
        )

    def _local_no_provider_emit(self, emit_event):
        def guarded_emit(run_id: str, event_type: str, payload: dict[str, Any]) -> None:
            if payload.get("real_provider_call") is True or payload.get("provider_backed") is True:
                raise RuntimeError(
                    "LangGraph+SwarmGraph local-real path cannot claim provider-backed calls"
                )
            payload = {
                **payload,
                "runtime_mode": payload.get("runtime_mode", _LOCAL_REAL_MODE),
                "real_provider_call": payload.get("real_provider_call", False),
                "provider_backed": payload.get("provider_backed", False),
            }
            emit_event(run_id, event_type, payload)

        return guarded_emit

    def _offline_queen_decompose(
        self,
        objective: str,
        graph_input: dict[str, Any],
        max_workers: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        tasks = []
        for index in range(max(1, max_workers)):
            worker_id = f"worker-{index + 1}"
            tasks.append({
                "task_id": f"task-{index + 1}",
                "worker_id": worker_id,
                "role": "worker",
                "input": {
                    **graph_input,
                    "swarmgraph_task": f"fake/offline deterministic task {index + 1}: {objective}",
                },
            })
        return tasks, {"objective": objective, "offline_deterministic": True}

    def _offline_consensus(self, proposals: list[WorkerProposal]) -> ConsensusResult:
        winning = proposals[0]
        votes = [
            Vote(
                task_id=proposal.task_id,
                voter_id=proposal.worker_id,
                proposal_id=f"{proposal.task_id}-{proposal.worker_id}",
                score=proposal.confidence,
                reason="Fake/offline deterministic SwarmGraph consensus vote",
            )
            for proposal in proposals
        ]
        return ConsensusResult(
            task_id=winning.task_id,
            winning_proposal=winning,
            votes=votes,
            consensus_reached=True,
            confidence=1.0,
            metadata={"runtime_mode": "fake/offline", "real_provider_call": False, "provider_backed": False},
        )

    def _topology_payload(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        nodes = [{"id": "queen", "role": "queen", "label": "SwarmGraph Queen"}]
        edges: list[dict[str, str]] = []
        seen_workers: set[str] = set()
        for task in tasks:
            worker_id = str(task["worker_id"])
            if worker_id not in seen_workers:
                seen_workers.add(worker_id)
                nodes.append({
                    "id": worker_id,
                    "role": str(task.get("role") or "worker"),
                    "label": worker_id,
                })
                edges.append({"source": "queen", "target": worker_id, "type": "assignment"})
        return {"nodes": nodes, "edges": edges, "source": "langgraph+swarmgraph"}

    def _consensus_payload(self, result: ConsensusResult) -> dict[str, Any]:
        return {
            "task_id": result.task_id,
            "consensus_reached": result.consensus_reached,
            "confidence": result.confidence,
            "winning_proposal_id": (
                f"{result.winning_proposal.task_id}-{result.winning_proposal.worker_id}"
            ),
            "votes": [vote.model_dump() for vote in result.votes],
            "source": "langgraph+swarmgraph",
            "real_provider_call": result.metadata.get("real_provider_call"),
            "provider_backed": result.metadata.get("provider_backed"),
            "runtime_mode": result.metadata.get("runtime_mode"),
        }

    def _measured_cost_payload(self, runtime_config: dict[str, Any]) -> dict[str, Any] | None:
        raw = runtime_config.get("measured_cost") or runtime_config.get("cost")
        if not isinstance(raw, dict) or raw.get("measured") is not True:
            return None

        payload: dict[str, Any] = {
            "source": "langgraph+swarmgraph",
            "runtime": "langgraph+swarmgraph",
            "measured": datetime.now(timezone.utc).isoformat(),
        }
        for source, target in (
            ("totalCost", "totalCost"),
            ("total_cost", "totalCost"),
            ("totalTokens", "totalTokens"),
            ("total_tokens", "totalTokens"),
            ("provider", "provider"),
            ("model", "model"),
            ("promptTokens", "promptTokens"),
            ("prompt_tokens", "promptTokens"),
            ("completionTokens", "completionTokens"),
            ("completion_tokens", "completionTokens"),
            ("currency", "currency"),
            ("items", "items"),
        ):
            if source in raw and raw[source] is not None:
                payload[target] = raw[source]

        if "totalCost" not in payload and "totalTokens" not in payload and "items" not in payload:
            return None
        return payload

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
            elif inspect.iscoroutinefunction(getattr(graph, "ainvoke", None)):
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


class _OfflineDeterministicLangGraph:
    def __init__(self, objective: Any) -> None:
        self.objective = str(objective)

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": "fake/offline",
            "objective": self.objective,
            "swarmgraph_task": input_data.get("swarmgraph_task"),
            "real_provider_call": False,
        }
