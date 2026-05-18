"""
Tests: Adoption protocol skeleton (P1b) + LangGraph runner (P2).

Tests the Pydantic models, registry, and runner.
LangGraph runner is auto-registered and reports RUNNABLE when
LangGraph is installed.
"""
from __future__ import annotations

import os

import pytest

from agent_runtime_cockpit.adoption import (
    AdoptionMode,
    AdoptionSpec,
    WorkerTask,
    WorkerProposal,
    Vote,
    ConsensusResult,
    AdoptionStatus,
    AdoptionCapability,
    AdoptionRegistry,
)


def _langgraph_state_graph_or_skip():
    try:
        from langgraph.graph import StateGraph
    except ImportError:
        try:
            from langgraph.graph.state import StateGraph  # type: ignore[import-not-found]
        except ImportError:
            pytest.skip("installed langgraph package does not expose StateGraph")
    return StateGraph


class TestAdoptionModels:
    """Pydantic models serialize/deserialize correctly."""

    def test_adoption_mode_values(self):
        assert AdoptionMode.LANGGRAPH.value == "langgraph+swarmgraph"
        assert AdoptionMode.AG2.value == "ag2+swarmgraph"
        assert AdoptionMode.OPENAI_AGENTS.value == "openai_agents+swarmgraph"

    def test_adoption_spec_defaults(self):
        spec = AdoptionSpec(mode=AdoptionMode.LANGGRAPH)
        assert spec.max_workers == 3
        assert spec.consensus_threshold == 0.67
        assert spec.runtime_config == {}

    def test_worker_task_serialization(self):
        task = WorkerTask(task_id="t1", worker_id="w1", runtime="langgraph")
        d = task.model_dump()
        assert d["task_id"] == "t1"
        assert d["worker_id"] == "w1"
        assert d["input_data"] == {}

    def test_worker_proposal_defaults(self):
        p = WorkerProposal(task_id="t1", worker_id="w1", output="result")
        assert p.confidence == 1.0
        assert p.metadata == {}

    def test_vote_model(self):
        v = Vote(task_id="t1", voter_id="v1", proposal_id="p1", score=0.9)
        assert v.score == 0.9
        assert v.reason == ""

    def test_consensus_result(self):
        proposal = WorkerProposal(task_id="t1", worker_id="w1", output="ok")
        result = ConsensusResult(
            task_id="t1",
            winning_proposal=proposal,
            consensus_reached=True,
            confidence=0.95,
        )
        assert result.consensus_reached is True
        assert result.confidence == 0.95
        assert len(result.votes) == 0

    def test_adoption_status_enum(self):
        assert AdoptionStatus.NOT_IMPLEMENTED.value == "not_implemented"
        assert AdoptionStatus.NOT_RUNNABLE.value == "not_runnable"
        assert AdoptionStatus.RUNNABLE.value == "runnable"

    def test_adoption_capability(self):
        cap = AdoptionCapability(
            mode=AdoptionMode.LANGGRAPH,
            status=AdoptionStatus.NOT_IMPLEMENTED,
            reason="Not done yet",
        )
        assert cap.mode == AdoptionMode.LANGGRAPH
        assert cap.status == AdoptionStatus.NOT_IMPLEMENTED

    def test_full_serialization_roundtrip(self):
        spec = AdoptionSpec(
            mode=AdoptionMode.CREWAI,
            runtime_config={"key": "val"},
            max_workers=5,
            consensus_threshold=0.8,
        )
        json_str = spec.model_dump_json()
        restored = AdoptionSpec.model_validate_json(json_str)
        assert restored.mode == AdoptionMode.CREWAI
        assert restored.max_workers == 5


class TestAdoptionRegistry:
    """AdoptionRegistry auto-registers LangGraph; other modes are NOT_IMPLEMENTED."""

    def test_langgraph_is_auto_registered(self, tmp_path):
        """LangGraph runner should be auto-registered and report RUNNABLE."""
        caps = AdoptionRegistry.list_capabilities(tmp_path)
        lg_cap = next((c for c in caps if c.mode == AdoptionMode.LANGGRAPH), None)
        assert lg_cap is not None
        assert lg_cap.status == AdoptionStatus.RUNNABLE
        assert "LangGraph" in lg_cap.reason

    def test_other_modes_report_not_implemented(self, tmp_path):
        """Non-LangGraph modes should still report NOT_IMPLEMENTED."""
        caps = AdoptionRegistry.list_capabilities(tmp_path)
        other_modes = [
            c for c in caps
            if c.mode not in {
                AdoptionMode.LANGGRAPH,
                AdoptionMode.AG2,
                AdoptionMode.CREWAI,
                AdoptionMode.OPENAI_AGENTS,
                AdoptionMode.LLAMAINDEX,
            }
        ]
        for cap in other_modes:
            assert cap.status == AdoptionStatus.NOT_IMPLEMENTED, (
                f"{cap.mode} expected NOT_IMPLEMENTED, got {cap.status}"
            )
            assert "not yet implemented" in cap.reason

    def test_list_contains_all_modes(self, tmp_path):
        caps = AdoptionRegistry.list_capabilities(tmp_path)
        modes = {cap.mode for cap in caps}
        assert modes == set(AdoptionMode)

    def test_ag2_runner_registered(self, tmp_path):
        runner = AdoptionRegistry.get(AdoptionMode.AG2)
        assert runner is not None
        cap = runner.check_availability(tmp_path)
        assert cap.mode == AdoptionMode.AG2
        assert cap.status in {AdoptionStatus.RUNNABLE, AdoptionStatus.NOT_RUNNABLE}

    def test_crewai_runner_registered(self, tmp_path):
        runner = AdoptionRegistry.get(AdoptionMode.CREWAI)
        assert runner is not None
        cap = runner.check_availability(tmp_path)
        assert cap.mode == AdoptionMode.CREWAI
        assert cap.status in {AdoptionStatus.RUNNABLE, AdoptionStatus.NOT_RUNNABLE}

    def test_openai_agents_runner_registered(self, tmp_path):
        runner = AdoptionRegistry.get(AdoptionMode.OPENAI_AGENTS)
        assert runner is not None
        cap = runner.check_availability(tmp_path)
        assert cap.mode == AdoptionMode.OPENAI_AGENTS
        assert cap.status in {AdoptionStatus.RUNNABLE, AdoptionStatus.NOT_RUNNABLE}

    def test_llamaindex_runner_registered(self, tmp_path):
        runner = AdoptionRegistry.get(AdoptionMode.LLAMAINDEX)
        assert runner is not None
        cap = runner.check_availability(tmp_path)
        assert cap.mode == AdoptionMode.LLAMAINDEX
        assert cap.status in {AdoptionStatus.RUNNABLE, AdoptionStatus.NOT_RUNNABLE}

    def test_parse_runtime_id_standard(self):
        base, mode = AdoptionRegistry.parse_runtime_id("langgraph+swarmgraph")
        assert base == "langgraph"
        assert mode == AdoptionMode.LANGGRAPH

    def test_parse_runtime_id_unknown(self):
        base, mode = AdoptionRegistry.parse_runtime_id("unknown+swarmgraph")
        assert base == "unknown"
        assert mode is None

    def test_parse_runtime_id_standalone(self):
        base, mode = AdoptionRegistry.parse_runtime_id("swarmgraph")
        assert base == "swarmgraph"
        assert mode is None


class TestLangGraphRunner:
    """LangGraphAdoptionRunner integration tests."""

    def test_runner_reports_runnable(self, tmp_path):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()
        cap = runner.check_availability(tmp_path)
        assert cap.status == AdoptionStatus.RUNNABLE
        assert "LangGraph" in cap.reason
        assert "SwarmGraph" in cap.reason

    def test_runner_mode(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()
        assert runner.mode == AdoptionMode.LANGGRAPH

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("ARC_REAL_RUNTIME_SMOKE") != "1",
        reason="real LangGraph graph execution is covered by opt-in smoke tests",
    )
    async def test_runner_executes_langgraph_graph(self):
        """Run a simple LangGraph graph through the adoption runner."""
        StateGraph = _langgraph_state_graph_or_skip()
        from typing_extensions import TypedDict

        class SimpleState(TypedDict):
            messages: list[str]

        def add_message(state: SimpleState) -> dict:
            return {"messages": state["messages"] + ["processed"]}

        builder = StateGraph(SimpleState)
        builder.add_node("process", add_message)
        builder.set_entry_point("process")
        builder.set_finish_point("process")
        graph = builder.compile()

        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()

        events: list[tuple[str, dict]] = []

        def emit(run_id: str, etype: str, data: dict) -> None:
            events.append((etype, data))

        spec = AdoptionSpec(
            mode=AdoptionMode.LANGGRAPH,
            runtime_config={
                "graph": graph,
                "input": {"messages": ["hello"]},
            },
        )

        result = await runner.run(spec, "test-run", emit)

        assert result.consensus_reached is True
        assert result.confidence > 0
        assert len(result.votes) >= 1
        assert result.winning_proposal.output is not None
        assert "hello" in result.winning_proposal.output
        assert "processed" in result.winning_proposal.output

        # Verify event flow
        event_types = [e[0] for e in events]
        assert "STEP_STARTED" in event_types
        assert "STEP_COMPLETED" in event_types
        assert "WORKER_RUNNING" in event_types
        assert "WORKER_COMPLETED" in event_types
        assert "RUN_COMPLETED" in event_types
        consensus_events = [
            data for event_type, data in events
            if event_type == "STEP_COMPLETED" and data.get("step") == "consensus"
        ]
        assert consensus_events[-1]["swarmgraph"] is True

    def test_runner_run_without_graph_raises(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()
        import asyncio

        async def _run():
            await runner.run(
                AdoptionSpec(mode=AdoptionMode.LANGGRAPH),
                "run-id",
                lambda *a: None,
            )

        with pytest.raises(ValueError, match="No LangGraph graph provided"):
            asyncio.run(_run())

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.environ.get("ARC_REAL_RUNTIME_SMOKE") != "1",
        reason="real LangGraph graph execution is covered by opt-in smoke tests",
    )
    async def test_runner_run_with_custom_input(self):
        """Test that custom input is passed through to the graph."""
        StateGraph = _langgraph_state_graph_or_skip()
        from typing_extensions import TypedDict

        class SimpleState(TypedDict):
            value: str

        def echo(state: SimpleState) -> dict:
            return {"value": f"echo: {state['value']}"}

        builder = StateGraph(SimpleState)
        builder.add_node("echo", echo)
        builder.set_entry_point("echo")
        builder.set_finish_point("echo")
        graph = builder.compile()

        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()

        spec = AdoptionSpec(
            mode=AdoptionMode.LANGGRAPH,
            runtime_config={
                "graph": graph,
                "input": {"value": "test-input"},
            },
        )

        result = await runner.run(spec, "run-custom", lambda *a: None)
        assert "echo: test-input" in result.winning_proposal.output

    @pytest.mark.asyncio
    async def test_runner_emits_swarmgraph_topology_consensus_without_cost(self, monkeypatch):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        class _Graph:
            ainvoke = None

            def invoke(self, input_data):
                return {"answer": input_data["swarmgraph_task"]}

        runner = LangGraphAdoptionRunner()

        def fake_decompose(objective, graph_input, max_workers, run_id):
            return ([
                {
                    "task_id": "task-1",
                    "worker_id": "worker-1",
                    "role": "analyst",
                    "input": {**graph_input, "swarmgraph_task": "analyze"},
                },
                {
                    "task_id": "task-2",
                    "worker_id": "worker-2",
                    "role": "reviewer",
                    "input": {**graph_input, "swarmgraph_task": "review"},
                },
            ], object())

        monkeypatch.setattr(runner, "_queen_decompose", fake_decompose)

        def fake_consensus(swarm_state, proposals):
            return ConsensusResult(
                task_id=proposals[0].task_id,
                winning_proposal=proposals[0],
                votes=[
                    Vote(
                        task_id=proposal.task_id,
                        voter_id=proposal.worker_id,
                        proposal_id=f"{proposal.task_id}-{proposal.worker_id}",
                        score=proposal.confidence,
                        reason="test vote",
                    )
                    for proposal in proposals
                ],
                consensus_reached=True,
                confidence=1.0,
            )

        monkeypatch.setattr(runner, "_swarmgraph_consensus", fake_consensus)

        events: list[tuple[str, dict]] = []
        result = await runner.run(
            AdoptionSpec(
                mode=AdoptionMode.LANGGRAPH,
                runtime_config={"graph": _Graph(), "input": {"topic": "x"}},
                max_workers=2,
            ),
            "lg-sg-run",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        topology = [data for event_type, data in events if event_type == "SWARMGRAPH_TOPOLOGY"]
        consensus = [data for event_type, data in events if event_type == "SWARMGRAPH_CONSENSUS"]

        assert result.consensus_reached is True
        assert len(topology) == 1
        assert len(topology[0]["nodes"]) == 3
        assert {node["id"] for node in topology[0]["nodes"]} == {"queen", "worker-1", "worker-2"}
        assert topology[0]["edges"] == [
            {"source": "queen", "target": "worker-1", "type": "assignment"},
            {"source": "queen", "target": "worker-2", "type": "assignment"},
        ]
        assert len(consensus) == 1
        assert len(consensus[0]["votes"]) == 2
        assert {vote["voter_id"] for vote in consensus[0]["votes"]} == {"worker-1", "worker-2"}
        assert consensus[0]["consensus_reached"] is True
        assert "SWARMGRAPH_COST" not in [event_type for event_type, data in events]

    @pytest.mark.asyncio
    async def test_runner_emits_swarmgraph_cost_from_measured_metadata_only(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        events: list[tuple[str, dict]] = []
        await LangGraphAdoptionRunner().run(
            AdoptionSpec(
                mode=AdoptionMode.LANGGRAPH,
                runtime_config={
                    "offline": True,
                    "fake": True,
                    "prompt": "cost metadata",
                    "measured_cost": {
                        "measured": True,
                        "total_cost": 0.025,
                        "total_tokens": 2500,
                        "currency": "USD",
                        "provider": "test-provider",
                        "items": [{"tokens": 2500, "cost": 0.025}],
                    },
                },
            ),
            "lg-sg-measured-cost",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        cost_events = [data for event_type, data in events if event_type == "SWARMGRAPH_COST"]
        assert cost_events == [{
            "runtime": "langgraph+swarmgraph",
            "measured": True,
            "totalCost": 0.025,
            "totalTokens": 2500,
            "currency": "USD",
            "provider": "test-provider",
            "items": [{"tokens": 2500, "cost": 0.025}],
        }]

    @pytest.mark.asyncio
    async def test_runner_ignores_unmeasured_swarmgraph_cost_metadata(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        events: list[tuple[str, dict]] = []
        await LangGraphAdoptionRunner().run(
            AdoptionSpec(
                mode=AdoptionMode.LANGGRAPH,
                runtime_config={
                    "offline": True,
                    "fake": True,
                    "prompt": "cost metadata",
                    "measured_cost": {"total_cost": 0.025, "total_tokens": 2500},
                },
            ),
            "lg-sg-unmeasured-cost",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert "SWARMGRAPH_COST" not in [event_type for event_type, data in events]

    @pytest.mark.asyncio
    async def test_runner_offline_fake_branch_is_deterministic(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        async def run_once():
            events: list[tuple[str, dict]] = []
            result = await LangGraphAdoptionRunner().run(
                AdoptionSpec(
                    mode=AdoptionMode.LANGGRAPH,
                    runtime_config={
                        "offline": True,
                        "fake": True,
                        "prompt": "deterministic prompt",
                    },
                    max_workers=2,
                ),
                "lg-sg-offline",
                lambda run_id, event_type, data: events.append((event_type, data)),
            )
            comparable_events = [
                (event_type, data)
                for event_type, data in events
                if event_type in {"SWARMGRAPH_TOPOLOGY", "SWARMGRAPH_CONSENSUS"}
            ]
            return result, comparable_events

        first_result, first_events = await run_once()
        second_result, second_events = await run_once()

        assert first_result.model_dump() == second_result.model_dump()
        assert first_events == second_events
        assert first_result.consensus_reached is True
        assert first_result.metadata["runtime_mode"] == "fake/offline"
        assert first_result.metadata["real_provider_call"] is False
        assert [event_type for event_type, data in first_events] == [
            "SWARMGRAPH_TOPOLOGY",
            "SWARMGRAPH_CONSENSUS",
        ]
        consensus = first_events[-1][1]
        assert consensus["consensus_reached"] is True
        assert consensus["real_provider_call"] is False
        assert consensus["provider_backed"] is False
        assert first_result.metadata["provider_backed"] is False

    @pytest.mark.asyncio
    async def test_runner_offline_fake_is_default_even_when_real_gate_set(self, monkeypatch):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
        monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")

        result = await LangGraphAdoptionRunner().run(
            AdoptionSpec(
                mode=AdoptionMode.LANGGRAPH,
                runtime_config={"offline": True, "fake": True, "prompt": "default remains offline"},
            ),
            "lg-sg-default-offline",
            lambda *args: None,
        )

        assert result.metadata["runtime_mode"] == "fake/offline"
        assert result.metadata["real_provider_call"] is False
        assert result.metadata["provider_backed"] is False

    @pytest.mark.asyncio
    async def test_runner_local_real_blocked_without_gate(self, monkeypatch):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
        monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
        events: list[tuple[str, dict]] = []

        with pytest.raises(PermissionError, match="ARC_REAL_RUNTIME_SMOKE=1.*ARC_LANGGRAPH_SWARMGRAPH_REAL=1"):
            await LangGraphAdoptionRunner().run(
                AdoptionSpec(
                    mode=AdoptionMode.LANGGRAPH,
                    runtime_config={"mode": "local-real", "graph": object()},
                ),
                "lg-sg-local-real-blocked",
                lambda run_id, event_type, data: events.append((event_type, data)),
            )

        assert events == [(
            "RUN_FAILED",
            {
                "error": (
                    "LangGraph+SwarmGraph local-real mode requires "
                    "ARC_REAL_RUNTIME_SMOKE=1 and ARC_LANGGRAPH_SWARMGRAPH_REAL=1; "
                    "no provider calls were made."
                ),
                "mode": "langgraph+swarmgraph",
                "runtime_mode": "local-real",
                "real_provider_call": False,
                "provider_backed": False,
            },
        )]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("real_runtime_smoke", "langgraph_swarmgraph_real"),
        [("1", None), (None, "1")],
    )
    async def test_runner_local_real_blocked_with_partial_gate(
        self,
        monkeypatch,
        real_runtime_smoke,
        langgraph_swarmgraph_real,
    ):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        if real_runtime_smoke is None:
            monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
        else:
            monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", real_runtime_smoke)
        if langgraph_swarmgraph_real is None:
            monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
        else:
            monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", langgraph_swarmgraph_real)

        with pytest.raises(PermissionError, match="ARC_REAL_RUNTIME_SMOKE=1.*ARC_LANGGRAPH_SWARMGRAPH_REAL=1"):
            await LangGraphAdoptionRunner().run(
                AdoptionSpec(
                    mode=AdoptionMode.LANGGRAPH,
                    runtime_config={"runtime_mode": "local-real", "graph": object()},
                ),
                "lg-sg-local-real-partial-gate",
                lambda *args: None,
            )

    @pytest.mark.asyncio
    async def test_runner_local_real_gate_metadata_no_provider_calls(self, monkeypatch):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        class _Graph:
            ainvoke = None

            def invoke(self, input_data):
                return {"answer": input_data["swarmgraph_task"]}

        runner = LangGraphAdoptionRunner()
        monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
        monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")
        monkeypatch.setattr(
            runner,
            "_queen_decompose",
            lambda objective, graph_input, max_workers, run_id: ([{
                "task_id": "task-1",
                "worker_id": "worker-1",
                "role": "worker",
                "input": {**graph_input, "swarmgraph_task": "local task"},
            }], object()),
        )
        monkeypatch.setattr(
            runner,
            "_swarmgraph_consensus",
            lambda swarm_state, proposals: ConsensusResult(
                task_id=proposals[0].task_id,
                winning_proposal=proposals[0],
                votes=[Vote(
                    task_id=proposals[0].task_id,
                    voter_id=proposals[0].worker_id,
                    proposal_id="task-1-worker-1",
                    score=1.0,
                    reason="local test vote",
                )],
                consensus_reached=True,
                confidence=1.0,
            ),
        )

        events: list[tuple[str, dict]] = []
        result = await runner.run(
            AdoptionSpec(
                mode=AdoptionMode.LANGGRAPH,
                runtime_config={
                    "mode": "local-real",
                    "graph": _Graph(),
                    "input": {"topic": "local"},
                },
            ),
            "lg-sg-local-real",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert result.metadata["runtime_mode"] == "local-real"
        assert result.metadata["real_provider_call"] is False
        assert result.metadata["provider_backed"] is False
        assert result.winning_proposal.metadata["runtime_mode"] == "local-real"
        assert result.winning_proposal.metadata["real_provider_call"] is False
        assert result.winning_proposal.metadata["provider_backed"] is False
        consensus = [data for event_type, data in events if event_type == "SWARMGRAPH_CONSENSUS"][-1]
        completed = [data for event_type, data in events if event_type == "RUN_COMPLETED"][-1]
        assert consensus["runtime_mode"] == "local-real"
        assert consensus["real_provider_call"] is False
        assert consensus["provider_backed"] is False
        assert completed["runtime_mode"] == "local-real"
        assert completed["real_provider_call"] is False
        assert completed["provider_backed"] is False
        for event_type, payload in events:
            assert payload.get("real_provider_call") is not True, event_type
            assert payload.get("provider_backed") is not True, event_type

    @pytest.mark.asyncio
    async def test_runner_local_real_rejects_provider_backed_event_claims(self, monkeypatch):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )

        class _Graph:
            ainvoke = None

            def invoke(self, input_data):
                return {"answer": input_data["swarmgraph_task"]}

        runner = LangGraphAdoptionRunner()
        monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
        monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")
        monkeypatch.setattr(
            runner,
            "_queen_decompose",
            lambda objective, graph_input, max_workers, run_id: ([{
                "task_id": "task-1",
                "worker_id": "worker-1",
                "role": "worker",
                "input": {**graph_input, "swarmgraph_task": "local task"},
            }], object()),
        )

        def provider_backed_consensus(swarm_state, proposals):
            return ConsensusResult(
                task_id=proposals[0].task_id,
                winning_proposal=proposals[0],
                votes=[],
                consensus_reached=True,
                confidence=1.0,
                metadata={"provider_backed": True},
            )

        monkeypatch.setattr(runner, "_swarmgraph_consensus", provider_backed_consensus)

        with pytest.raises(RuntimeError, match="cannot claim provider-backed calls"):
            await runner.run(
                AdoptionSpec(
                    mode=AdoptionMode.LANGGRAPH,
                    runtime_config={
                        "runtime_mode": "local-real",
                        "graph": _Graph(),
                        "input": {"topic": "local"},
                    },
                ),
                "lg-sg-local-real-provider-claim",
                lambda *args: None,
            )


class TestAG2Runner:
    @pytest.mark.asyncio
    async def test_ag2_runner_fake_team_consensus(self):
        from agent_runtime_cockpit.adoption.ag2_runner import AG2AdoptionRunner

        class _Event:
            def __init__(self, sender: str, content: str) -> None:
                self.sender = sender
                self.content = content

        class _Resp:
            def __aiter__(self):
                self._events = iter([_Event("agent-a", "proposal one"), _Event("agent-b", "proposal one")])
                return self

            async def __anext__(self):
                try:
                    return next(self._events)
                except StopIteration:
                    raise StopAsyncIteration

            @property
            def events(self):
                return self

        class _Team:
            async def a_run_group_chat(self, messages):
                return _Resp()

        events: list[tuple[str, dict]] = []
        runner = AG2AdoptionRunner()
        result = await runner.run(
            AdoptionSpec(
                mode=AdoptionMode.AG2,
                runtime_config={"team": _Team(), "message": "decide"},
            ),
            "ag2-run",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert result.consensus_reached is True
        assert result.confidence > 0
        assert len(result.votes) == 2
        assert result.winning_proposal.output == "proposal one"
        assert any(data.get("swarmgraph") is True for event_type, data in events if event_type == "STEP_COMPLETED")

    @pytest.mark.asyncio
    async def test_ag2_runner_requires_team(self):
        from agent_runtime_cockpit.adoption.ag2_runner import AG2AdoptionRunner

        with pytest.raises(ValueError, match="team"):
            await AG2AdoptionRunner().run(
                AdoptionSpec(mode=AdoptionMode.AG2, runtime_config={"message": "x"}),
                "ag2-run",
                lambda *args: None,
            )


class TestCrewAIRunner:
    @pytest.mark.asyncio
    async def test_crewai_runner_fake_crew_consensus(self):
        from agent_runtime_cockpit.adoption.crewai_runner import CrewAIAdoptionRunner

        class _Task:
            raw = "crew task result"
            agent = "crew-agent"

        class _Result:
            tasks_output = [_Task()]

        class _Crew:
            def kickoff(self, inputs):
                return _Result()

        events: list[tuple[str, dict]] = []
        result = await CrewAIAdoptionRunner().run(
            AdoptionSpec(mode=AdoptionMode.CREWAI, runtime_config={"crew": _Crew(), "inputs": {"topic": "x"}}),
            "crew-run",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert result.consensus_reached is True
        assert result.winning_proposal.output == "crew task result"
        assert any(data.get("swarmgraph") is True for event_type, data in events if event_type == "STEP_COMPLETED")

    @pytest.mark.asyncio
    async def test_crewai_runner_requires_crew(self):
        from agent_runtime_cockpit.adoption.crewai_runner import CrewAIAdoptionRunner

        with pytest.raises(ValueError, match="crew"):
            await CrewAIAdoptionRunner().run(
                AdoptionSpec(mode=AdoptionMode.CREWAI),
                "crew-run",
                lambda *args: None,
            )


class TestOpenAIAgentsRunner:
    @pytest.mark.asyncio
    async def test_openai_agents_runner_fake_agent_consensus(self):
        from agent_runtime_cockpit.adoption.openai_agents_runner import OpenAIAgentsAdoptionRunner

        class _Agent:
            name = "agent-a"

        class _Result:
            final_output = "agent result"

        class _Runner:
            @staticmethod
            async def run(agent, prompt):
                return _Result()

        events: list[tuple[str, dict]] = []
        result = await OpenAIAgentsAdoptionRunner().run(
            AdoptionSpec(mode=AdoptionMode.OPENAI_AGENTS, runtime_config={"agent": _Agent(), "prompt": "x", "runner": _Runner}),
            "oa-run",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert result.consensus_reached is True
        assert result.winning_proposal.output == "agent result"
        assert any(data.get("swarmgraph") is True for event_type, data in events if event_type == "STEP_COMPLETED")

    @pytest.mark.asyncio
    async def test_openai_agents_runner_requires_agent(self):
        from agent_runtime_cockpit.adoption.openai_agents_runner import OpenAIAgentsAdoptionRunner

        with pytest.raises(ValueError, match="agent"):
            await OpenAIAgentsAdoptionRunner().run(
                AdoptionSpec(mode=AdoptionMode.OPENAI_AGENTS, runtime_config={"prompt": "x"}),
                "oa-run",
                lambda *args: None,
            )


class TestLlamaIndexRunner:
    @pytest.mark.asyncio
    async def test_llamaindex_runner_fake_query_engine_consensus(self):
        from agent_runtime_cockpit.adoption.llamaindex_runner import LlamaIndexAdoptionRunner

        class _Response:
            response = "llama answer"

        class _QueryEngine:
            async def aquery(self, query):
                return _Response()

        events: list[tuple[str, dict]] = []
        result = await LlamaIndexAdoptionRunner().run(
            AdoptionSpec(mode=AdoptionMode.LLAMAINDEX, runtime_config={"query_engine": _QueryEngine(), "query": "x"}),
            "li-run",
            lambda run_id, event_type, data: events.append((event_type, data)),
        )

        assert result.consensus_reached is True
        assert result.winning_proposal.output == "llama answer"
        assert any(data.get("swarmgraph") is True for event_type, data in events if event_type == "STEP_COMPLETED")

    @pytest.mark.asyncio
    async def test_llamaindex_runner_requires_target(self):
        from agent_runtime_cockpit.adoption.llamaindex_runner import LlamaIndexAdoptionRunner

        with pytest.raises(ValueError, match="workflow/query_engine/agent"):
            await LlamaIndexAdoptionRunner().run(
                AdoptionSpec(mode=AdoptionMode.LLAMAINDEX, runtime_config={"query": "x"}),
                "li-run",
                lambda *args: None,
            )
