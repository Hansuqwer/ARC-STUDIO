from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..models import ApprovalDecision, SwarmTask, TaskStatus


def require_hitl_approval(
    task: SwarmTask,
    prompt: str | None = None,
) -> ApprovalDecision:
    token_id = f"hitl-{uuid.uuid4().hex[:12]}"
    decision = ApprovalDecision(
        approved=False,
        reason=f"awaiting HITL approval: token={token_id}",
        token_id=token_id,
        decided_by="hitl_gate",
        timestamp=datetime.now(timezone.utc),
    )
    task.approval = decision
    task.status = TaskStatus.pending
    return decision


def approve_hitl(
    task: SwarmTask,
    token_id: str,
    reason: str = "approved by operator",
) -> ApprovalDecision:
    if task.approval and task.approval.token_id != token_id:
        return ApprovalDecision(
            approved=False,
            reason="token mismatch",
            decided_by="system",
        )
    decision = ApprovalDecision(
        approved=True,
        reason=reason,
        token_id=token_id,
        decided_by="operator",
        timestamp=datetime.now(timezone.utc),
    )
    task.approval = decision
    task.status = TaskStatus.assigned
    return decision


def reject_hitl(
    task: SwarmTask,
    token_id: str,
    reason: str = "rejected by operator",
) -> ApprovalDecision:
    if task.approval and task.approval.token_id != token_id:
        return ApprovalDecision(
            approved=False,
            reason="token mismatch",
            decided_by="system",
        )
    decision = ApprovalDecision(
        approved=False,
        reason=reason,
        token_id=token_id,
        decided_by="operator",
        timestamp=datetime.now(timezone.utc),
    )
    task.approval = decision
    task.status = TaskStatus.failed
    return decision
