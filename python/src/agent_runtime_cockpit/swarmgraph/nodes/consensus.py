from __future__ import annotations

from datetime import datetime, timezone

from ..consensus import run_consensus
from ..models import AgentVote, ApprovalDecision, SwarmTask, TaskStatus


def run_consensus_round(
    tasks: list[SwarmTask],
    protocol: str = "majority",
    quorum: int | None = None,
) -> list[ApprovalDecision]:
    from ..config import ConsensusProtocol
    proto = ConsensusProtocol(protocol) if isinstance(protocol, str) else protocol

    decisions: list[ApprovalDecision] = []
    for task in tasks:
        if task.result is None or task.result.error:
            decisions.append(ApprovalDecision(
                approved=False,
                reason="no result to approve",
                decided_by="system",
            ))
            continue

        votes: list[AgentVote] = []
        if task.approval is None:
            vote = AgentVote(
                agent_id=task.assigned_agent_id or "system",
                task_id=task.id,
                round=0,
                approved=True,
                confidence=1.0,
                reasoning="result present",
            )
            votes.append(vote)

        consensus = run_consensus(votes, protocol=proto, quorum=quorum)
        task.votes = votes

        if consensus.reached:
            decision = ApprovalDecision(
                approved=True,
                reason=consensus.details,
                decided_by="consensus",
            )
            task.status = TaskStatus.completed
        else:
            decision = ApprovalDecision(
                approved=False,
                reason=consensus.details,
                decided_by="consensus",
            )
            task.status = TaskStatus.failed

        task.approval = decision
        decisions.append(decision)

    return decisions
