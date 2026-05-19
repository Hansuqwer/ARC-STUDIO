from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_runtime_cockpit.swarmgraph import (
    SwarmGraphRunner,
    SwarmGraphConfig,
    SwarmGraphEvent,
    ConsensusResult,
    AgentSpec,
    AgentVote,
    SwarmTask,
    SwarmState,
    SwarmCheckpoint,
    majority_consensus,
    quorum_consensus,
    run_consensus,
    run_deterministic_swarm,
)
from agent_runtime_cockpit.swarmgraph.config import (
    ConsensusProtocol,
    ExecutionMode,
    SwarmStrategy,
    SwarmTopology,
)
from agent_runtime_cockpit.swarmgraph.models import (
    AgentRole,
    AgentStatus,
    ApprovalDecision,
    SwarmStatus,
    TaskStatus,
    WorkerResult,
    TaskPriority,
    SwarmFailureCause,
)
from agent_runtime_cockpit.swarmgraph.graph import (
    build_swarm_graph,
    SwarmGraphTopology,
    GraphNode,
    GraphEdge,
)
from agent_runtime_cockpit.swarmgraph.events import (
    SwarmGraphEventKind,
    emit_topology_event,
    emit_worker_event,
    emit_consensus_event,
    emit_budget_event,
)
from agent_runtime_cockpit.swarmgraph.nodes.queen import (
    queen_decompose,
    queen_assign,
    queen_prepare_agents,
)
from agent_runtime_cockpit.swarmgraph.nodes.worker import worker_execute, process_worker_results
from agent_runtime_cockpit.swarmgraph.nodes.consensus import run_consensus_round
from agent_runtime_cockpit.swarmgraph.nodes.approval import require_hitl_approval, approve_hitl, reject_hitl


class TestSwarmGraphConfig:
    def test_default_config(self):
        cfg = SwarmGraphConfig()
        assert cfg.num_workers == 3
        assert cfg.consensus_protocol == ConsensusProtocol.majority
        assert cfg.execution_mode == ExecutionMode.fake_offline
        assert cfg.allow_paid_calls is False

    def test_effective_quorum_explicit(self):
        cfg = SwarmGraphConfig(quorum_size=2)
        assert cfg.effective_quorum(10) == 2

    def test_effective_quorum_default(self):
        cfg = SwarmGraphConfig()
        assert cfg.effective_quorum(5) == 3

    def test_config_frozen(self):
        cfg = SwarmGraphConfig()
        with pytest.raises(ValidationError):
            cfg.num_workers = 5

    def test_config_rejects_extra(self):
        with pytest.raises(ValidationError):
            SwarmGraphConfig(unknown_field=True)


class TestAgentSpec:
    def test_defaults(self):
        spec = AgentSpec(name="test-agent")
        assert spec.role == AgentRole.worker
        assert spec.model == "fake-stub"

    def test_frozen(self):
        spec = AgentSpec(name="test")
        with pytest.raises(ValidationError):
            spec.name = "new"


class TestConsensus:
    def test_majority_approves(self):
        votes = [
            AgentVote(agent_id="a1", task_id="t1", approved=True),
            AgentVote(agent_id="a2", task_id="t1", approved=True),
            AgentVote(agent_id="a3", task_id="t1", approved=False),
        ]
        result = majority_consensus(votes)
        assert result.reached is True
        assert result.approved is True
        assert result.approval_count == 2

    def test_majority_rejects(self):
        votes = [
            AgentVote(agent_id="a1", task_id="t1", approved=False),
            AgentVote(agent_id="a2", task_id="t1", approved=False),
            AgentVote(agent_id="a3", task_id="t1", approved=True),
        ]
        result = majority_consensus(votes)
        assert result.reached is False
        assert result.approved is False

    def test_majority_tie_needs_more(self):
        votes = [
            AgentVote(agent_id="a1", task_id="t1", approved=True),
            AgentVote(agent_id="a2", task_id="t1", approved=False),
        ]
        result = majority_consensus(votes)
        assert result.reached is False

    def test_majority_no_votes(self):
        result = majority_consensus([])
        assert result.reached is False

    def test_quorum_approves(self):
        votes = [
            AgentVote(agent_id="a1", task_id="t1", approved=True),
            AgentVote(agent_id="a2", task_id="t1", approved=True),
            AgentVote(agent_id="a3", task_id="t1", approved=False),
        ]
        result = quorum_consensus(votes, quorum=2)
        assert result.reached is True

    def test_quorum_not_met(self):
        votes = [AgentVote(agent_id="a1", task_id="t1", approved=True)]
        result = quorum_consensus(votes, quorum=3)
        assert result.reached is False

    def test_run_consensus_dispatch(self):
        votes = [AgentVote(agent_id="a1", task_id="t1", approved=True)]
        result = run_consensus(votes, protocol=ConsensusProtocol.majority)
        assert result.protocol == ConsensusProtocol.majority

    def test_consensus_result_frozen(self):
        result = ConsensusResult(reached=True, approved=True, total_votes=1, approval_count=1, rejection_count=0, required=1)
        with pytest.raises(ValidationError):
            result.reached = False


class TestSwarmState:
    def test_initial_state(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        assert state.status.value == "pending"
        assert state.current_round == 0

    def test_checkpoint_save_restore(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        ckpt = state.save_checkpoint()
        assert len(state.checkpoint_history) == 1
        state.current_round = 5
        restored = state.restore_checkpoint(ckpt.id)
        assert restored is True
        assert state.current_round == 0

    def test_fork(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        state.current_round = 3
        forked = state.fork()
        assert forked.status.value == "pending"
        assert forked.current_round == 0

    def test_get_pending_tasks_empty(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        assert state.get_pending_tasks() == []

    def test_all_tasks_completed_empty(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        assert state.all_tasks_completed() is False


class TestGraphBuilder:
    def test_build_star_topology(self):
        cfg = SwarmGraphConfig(num_workers=2, topology=SwarmTopology.star)
        state = SwarmState(config=cfg)
        queen_prepare_agents(state, 2)
        topology = build_swarm_graph(state)
        assert len(topology.nodes) == 3
        assert len(topology.edges) >= 2

    def test_build_chain_topology(self):
        cfg = SwarmGraphConfig(num_workers=2, topology=SwarmTopology.chain)
        state = SwarmState(config=cfg)
        queen_prepare_agents(state, 2)
        topology = build_swarm_graph(state)
        assert len(topology.nodes) == 3

    def test_topology_dict(self):
        g = SwarmGraphTopology(
            nodes=[GraphNode(id="n1", label="Node1", role=AgentRole.queen)],
            edges=[GraphEdge(source="q1", target="w1", label="edge")],
        )
        d = g.to_dict()
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1


class TestEvents:
    def test_event_defaults(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        event = emit_topology_event(state, {"foo": "bar"})
        assert event.kind == SwarmGraphEventKind.topology
        assert event.swarm_id == state.id

    def test_event_to_dict(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        evt = emit_topology_event(state, {"test": True})
        d = evt.to_dict()
        assert d["kind"] == "topology"
        assert "timestamp" in d

    def test_event_frozen(self):
        with pytest.raises(Exception):
            evt = SwarmGraphEvent(
                kind=SwarmGraphEventKind.error,
                swarm_id="test",
                data={},
            )
            evt.kind = SwarmGraphEventKind.topology

    def test_worker_event(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        result = WorkerResult(worker_id="w1", task_id="t1", output="ok")
        evt = emit_worker_event(state, result)
        assert evt.kind == SwarmGraphEventKind.worker
        assert evt.data["worker_id"] == "w1"

    def test_consensus_event(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        decision = ApprovalDecision(approved=True, reason="test")
        evt = emit_consensus_event(state, "t1", decision)
        assert evt.kind == SwarmGraphEventKind.consensus
        assert evt.data["approved"] is True

    def test_budget_event(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        state.accumulated_cost_usd = 0.5
        evt = emit_budget_event(state, 0.5, 1.0)
        assert evt.kind == SwarmGraphEventKind.budget
        assert evt.data["exhausted"] is False


class TestQueenNode:
    def test_prepare_agents(self):
        cfg = SwarmGraphConfig(num_workers=2)
        state = SwarmState(config=cfg)
        queen_prepare_agents(state, 2)
        assert "queen-1" in state.agents
        assert "worker-1" in state.agents
        assert "worker-2" in state.agents

    def test_decompose_star(self):
        cfg = SwarmGraphConfig(num_workers=3)
        state = SwarmState(config=cfg)
        tasks = queen_decompose(state, "test prompt")
        assert len(tasks) == 3

    def test_decompose_chain(self):
        cfg = SwarmGraphConfig(num_workers=2, topology=SwarmTopology.chain)
        state = SwarmState(config=cfg)
        tasks = queen_decompose(state, "test prompt")
        assert len(tasks) == 2
        if len(tasks) >= 2:
            assert tasks[1].parent_task_id == tasks[0].id

    def test_assign(self):
        cfg = SwarmGraphConfig(num_workers=2)
        state = SwarmState(config=cfg)
        queen_prepare_agents(state, 2)
        tasks = [SwarmTask(prompt="task1"), SwarmTask(prompt="task2")]
        for t in tasks:
            state.tasks[t.id] = t
        assignment = queen_assign(state, tasks)
        assert len(assignment) == 2


class TestWorkerNode:
    def test_fake_offline_execution(self):
        task = SwarmTask(prompt="hello")
        task.assigned_agent_id = "worker-1"
        result = worker_execute(task, mode=ExecutionMode.fake_offline)
        assert result.error is None
        assert "hello" in result.output

    def test_worker_result_timeout(self):
        import time
        task = SwarmTask(prompt="timeout")
        task.assigned_agent_id = "worker-1"
        result = worker_execute(task, mode=ExecutionMode.fake_offline, timeout=0.001)
        assert result.duration_seconds < 30

    def test_process_results(self):
        task = SwarmTask(prompt="test")
        results = [WorkerResult(worker_id="w1", task_id=task.id, output="done")]
        processed = process_worker_results([task], results)
        assert processed[0].status == TaskStatus.completed
        assert processed[0].result is not None


class TestConsensusNode:
    def test_consensus_approves_good_task(self):
        task = SwarmTask(prompt="test")
        task.assigned_agent_id = "w1"
        task.result = WorkerResult(worker_id="w1", task_id=task.id, output="ok")
        decisions = run_consensus_round([task], protocol="majority")
        assert len(decisions) == 1
        assert decisions[0].approved is True

    def test_consensus_rejects_empty_result(self):
        task = SwarmTask(prompt="test")
        decisions = run_consensus_round([task], protocol="majority")
        assert len(decisions) == 1
        assert decisions[0].approved is False


class TestApprovalNode:
    def test_require_hitl(self):
        task = SwarmTask(prompt="test")
        decision = require_hitl_approval(task)
        assert decision.approved is False
        assert decision.token_id is not None

    def test_approve_hitl(self):
        task = SwarmTask(prompt="test")
        first = require_hitl_approval(task)
        token = first.token_id
        decision = approve_hitl(task, token)
        assert decision.approved is True

    def test_approve_hitl_wrong_token(self):
        task = SwarmTask(prompt="test")
        require_hitl_approval(task)
        decision = approve_hitl(task, "wrong-token")
        assert decision.approved is False

    def test_reject_hitl(self):
        task = SwarmTask(prompt="test")
        first = require_hitl_approval(task)
        decision = reject_hitl(task, first.token_id)
        assert decision.approved is False
        assert task.status == TaskStatus.failed


class TestRunner:
    def test_deterministic_run_default(self):
        result = run_deterministic_swarm(prompt="test run")
        assert result["status"] == "completed"
        assert result["total_tasks"] > 0
        assert result["completed_tasks"] > 0
        assert len(result["events"]) > 0

    def test_runner_basic(self):
        cfg = SwarmGraphConfig(num_workers=2, max_rounds=1)
        runner = SwarmGraphRunner(config=cfg)
        result = runner.run(prompt="hello")
        assert result["status"] == "completed"
        assert "swarm_id" in result

    def test_runner_events(self):
        cfg = SwarmGraphConfig(num_workers=2, max_rounds=1)
        runner = SwarmGraphRunner(config=cfg)
        runner.run(prompt="events test")
        events = runner.get_events()
        assert len(events) > 0
        kinds = {e.kind.value for e in events}
        assert "topology" in kinds
        assert "worker" in kinds or "consensus" in kinds

    def test_runner_state(self):
        cfg = SwarmGraphConfig(num_workers=2, max_rounds=1)
        runner = SwarmGraphRunner(config=cfg)
        runner.run(prompt="state test")
        state = runner.get_state()
        assert state is not None
        assert state.status.value == "completed"

    def test_runner_topology_events(self):
        cfg = SwarmGraphConfig(num_workers=3)
        runner = SwarmGraphRunner(config=cfg)
        result = runner.run(prompt="topology")
        topology_events = [e for e in result["events"] if e["kind"] == "topology"]
        assert len(topology_events) >= 1
        topo = topology_events[0]["data"]["topology"]
        assert "nodes" in topo
        assert "edges" in topo

    def test_runner_hitl_mode(self):
        from agent_runtime_cockpit.swarmgraph.fixtures import run_hitl_swarm
        result, runner = run_hitl_swarm()
        state = runner.get_state()
        assert state is not None
        assert state.status.value == "completed"
        pending = [t for t in state.tasks.values() if t.status == TaskStatus.pending]
        assert len(pending) > 0
        assert any(t.approval is not None and t.approval.token_id is not None for t in pending)

    def test_runner_budget_mode(self):
        from agent_runtime_cockpit.swarmgraph.fixtures import run_budget_swarm
        result = run_budget_swarm(prompt="budget", budget_limit=100.0)
        assert result["status"] == "completed"

    def test_runner_different_worker_counts(self):
        for n in [1, 3, 5]:
            cfg = SwarmGraphConfig(num_workers=n, max_rounds=1)
            runner = SwarmGraphRunner(config=cfg)
            result = runner.run(prompt=f"test {n} workers")
            assert result["status"] == "completed", f"failed for {n} workers"

    def test_run_default_prompt(self):
        result = run_deterministic_swarm()
        assert result["status"] == "completed"


class TestSwarmTask:
    def test_defaults(self):
        task = SwarmTask(prompt="test")
        assert task.status == TaskStatus.pending
        assert task.priority == TaskPriority.medium
        assert task.votes == []

    def test_mutable_fields(self):
        task = SwarmTask(prompt="test")
        task.status = TaskStatus.assigned
        assert task.status == TaskStatus.assigned


class TestBudgetEdgeCases:
    def test_budget_exhausted(self):
        cfg = SwarmGraphConfig(
            num_workers=1,
            max_rounds=3,
            enable_budget=True,
            budget_limit_usd=0.0,
        )
        runner = SwarmGraphRunner(config=cfg)
        result = runner.run(prompt="exhaust")
        assert result["status"] == "failed"

    def test_budget_negative(self):
        with pytest.raises(ValidationError):
            SwarmGraphConfig(budget_limit_usd=-1)


class TestStatusTransition:
    def test_pending_to_running(self):
        cfg = SwarmGraphConfig()
        state = SwarmState(config=cfg)
        assert state.status.value == "pending"
        state.status = SwarmStatus.running
        assert state.status.value == "running"

    def test_all_task_statuses(self):
        statuses = [s.value for s in TaskStatus]
        expected = ["pending", "assigned", "in_progress", "completed", "failed", "cancelled"]
        assert statuses == expected
