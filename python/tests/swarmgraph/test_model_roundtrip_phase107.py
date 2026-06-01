from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from agent_runtime_cockpit.swarmgraph import (
    NotificationConfig,
    NotificationDeliveryRecord,
    WebhookTargetConfig,
)
from agent_runtime_cockpit.swarmgraph.adaptive_consensus import AdaptiveRiskAssessment
from agent_runtime_cockpit.swarmgraph.config import ConsensusProtocol, SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.consensus import ConsensusResult
from agent_runtime_cockpit.swarmgraph.consensus_escrow import CommitRevealVote, VoteCommit
from agent_runtime_cockpit.swarmgraph.events import SwarmGraphEvent, SwarmGraphEventKind
from agent_runtime_cockpit.swarmgraph.models import (
    AgentSpec,
    AgentState,
    AgentVote,
    ApprovalDecision,
    QueenDirective,
    SwarmTask,
    WorkerResult,
)
from agent_runtime_cockpit.swarmgraph.nodes.consensus import ConsensusRoundOutcome
from agent_runtime_cockpit.swarmgraph.providers import (
    CostRates,
    ProviderCapability,
    ProviderMessage,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from agent_runtime_cockpit.swarmgraph.risk_assessment import (
    ProtocolSelection,
    RiskAssessment,
    RiskFixture,
)
from agent_runtime_cockpit.swarmgraph.runner import SwarmRunResult, SwarmRunTaskResult
from agent_runtime_cockpit.swarmgraph.state import SwarmCheckpoint, SwarmState


def _assert_json_round_trip(model: BaseModel) -> None:
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored.model_dump(mode="json") == model.model_dump(mode="json")


def test_swarmgraph_pydantic_models_round_trip_through_json() -> None:
    now = datetime.now(timezone.utc)
    config = SwarmGraphConfig(name="roundtrip")
    agent_spec = AgentSpec(name="Worker")
    agent_state = AgentState(agent_id=agent_spec.id)
    vote = AgentVote(agent_id=agent_spec.id, task_id="task-1", approved=True)
    approval = ApprovalDecision(approved=True, reason="ok")
    worker_result = WorkerResult(
        worker_id=agent_spec.id,
        task_id="task-1",
        output="ok",
        completed_at=now,
    )
    directive = QueenDirective(task_id="task-1", prompt="Do work")
    task = SwarmTask(
        id="task-1",
        prompt="Do work",
        assigned_agent_id=agent_spec.id,
        directive=directive,
        result=worker_result,
        votes=[vote],
        approval=approval,
        dependency_task_ids=["task-0"],
    )
    consensus = ConsensusResult(
        reached=True,
        approved=True,
        total_votes=1,
        approval_count=1,
        required=1,
        votes=[vote],
    )
    outcome = ConsensusRoundOutcome(
        task_id=task.id,
        decision=approval,
        consensus_result=consensus,
    )
    state = SwarmState(
        config=config,
        agents={agent_spec.id: agent_state},
        tasks={task.id: task},
        spec_map={agent_spec.id: agent_spec},
    )
    checkpoint = SwarmCheckpoint(
        config=config,
        agents=state.agents,
        tasks=state.tasks,
    )
    message = ProviderMessage(role="user", content="hello")
    request = ProviderRequest(model="model-a", messages=[message])
    usage = UsageRecord(input_tokens=1, output_tokens=2)
    response = ProviderResponse(
        call_id=request.call_id,
        model="model-a",
        content="ok",
        finish_reason="stop",
        usage=usage,
    )
    rates = CostRates(input_per_million=1.0, output_per_million=2.0)
    capability = ProviderCapability(
        provider_id="provider-a",
        provider_name="Provider A",
        supported_models=["model-a"],
        default_model="model-a",
        cost_rates={"model-a": rates},
    )
    event = SwarmGraphEvent(
        kind=SwarmGraphEventKind.audit,
        swarm_id=state.id,
        data={"ok": True},
    )
    risk = RiskAssessment(risk="low", score=0, rationale="ok")
    selection = ProtocolSelection(
        risk="low",
        protocol=ConsensusProtocol.majority,
        assessment=risk,
    )
    fixture = RiskFixture(
        id="fixture-1",
        prompt="Explain consensus.",
        expected_risk="low",
        expected_protocol=ConsensusProtocol.majority,
    )
    adaptive = AdaptiveRiskAssessment(
        risk_level="low",
        recommended_protocol=ConsensusProtocol.majority,
        base_assessment=risk,
    )
    commit_hash = "a" * 64
    vote_commit = VoteCommit(
        agent_id=vote.agent_id,
        task_id=vote.task_id,
        commit_hash=commit_hash,
        commit_timestamp=now,
    )
    reveal = CommitRevealVote(
        vote=vote,
        nonce="b" * 64,
        commit_hash=commit_hash,
        commit_timestamp=now,
    )
    run_task = SwarmRunTaskResult(task_id=task.id, output="ok", status="completed")
    run = SwarmRunResult(
        swarm_id=state.id,
        status="completed",
        rounds=1,
        total_tasks=1,
        completed_tasks=1,
        results=[run_task],
        events=[event.to_dict()],
    )
    target = WebhookTargetConfig(id="target-1", url="https://example.test/hook")
    notification_config = NotificationConfig(
        targets=[target],
        outbox_path=".arc/swarmgraph/outbox.jsonl",
    )
    delivery = NotificationDeliveryRecord(
        id="delivery-1",
        target_id=target.id,
        event_kind="audit",
        event=event.to_dict(),
        status="pending",
    )

    models = [
        config,
        agent_spec,
        agent_state,
        vote,
        approval,
        worker_result,
        directive,
        task,
        consensus,
        outcome,
        state,
        checkpoint,
        message,
        request,
        usage,
        response,
        rates,
        capability,
        event,
        risk,
        selection,
        fixture,
        adaptive,
        vote_commit,
        reveal,
        run_task,
        run,
        target,
        notification_config,
        delivery,
    ]

    assert len(models) == 30
    for model in models:
        _assert_json_round_trip(model)
