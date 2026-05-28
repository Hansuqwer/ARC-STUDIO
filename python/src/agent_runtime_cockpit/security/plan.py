"""Plan/Apply/Review models for deterministic plan-before-execution (Phase 75).

A Plan represents a sequence of commands with their classifications,
sandbox decisions, approval requirements, and known/unknown cost/risk
estimates. Apply requires an approved plan or explicit direct command.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from .sandbox import (
    CommandClassification,
    SandboxDecision,
    SandboxPathViolation,
    SandboxPolicy,
    classify_command,
    decide,
    validate_command_paths,
)


class PlanStepStatus(str, Enum):
    """Status of a plan step."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    APPLIED = "applied"
    FAILED = "failed"


class PlanStep(BaseModel):
    """One command in a plan with its classification and decision."""

    model_config = {"frozen": True}

    step_index: int
    command: list[str]
    classification: CommandClassification
    decision: SandboxDecision
    file_intents: list[str] = Field(default_factory=list)
    approval_required: bool = False
    status: PlanStepStatus = PlanStepStatus.PENDING
    cost_estimate: str | None = None
    risk_estimate: str | None = None
    detail: str | None = None


class PlanDecision(BaseModel):
    """Overall plan decision with all steps and metadata."""

    model_config = {"frozen": True}

    plan_id: str
    policy: str
    workspace_root: str
    steps: list[PlanStep] = Field(default_factory=list)
    total_steps: int = 0
    approved_steps: int = 0
    denied_steps: int = 0
    pending_approval_steps: int = 0
    has_destructive: bool = False
    has_privileged: bool = False
    has_network: bool = False
    has_install: bool = False
    overall_allowed: bool = False
    overall_reason: str = ""
    cost_summary: str | None = None
    risk_summary: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def build_plan(
    commands: list[list[str]],
    policy: SandboxPolicy,
    *,
    plan_id: str | None = None,
) -> PlanDecision:
    """Build a PlanDecision from a list of commands.

    Each command is classified and evaluated against the sandbox policy.
    Cost/risk estimates are marked as known/unknown - never fabricated.
    """
    import uuid

    pid = plan_id or f"plan-{uuid.uuid4().hex[:12]}"
    steps: list[PlanStep] = []
    has_destructive = False
    has_privileged = False
    has_network = False
    has_install = False

    for idx, cmd in enumerate(commands):
        if not cmd:
            continue
        classification = classify_command(cmd)
        decision = decide(cmd, policy)
        path_violation: str | None = None
        try:
            validate_command_paths(cmd, policy)
        except SandboxPathViolation as exc:
            path_violation = str(exc)
            decision = SandboxDecision(
                allowed=False,
                classification=classification,
                reason=path_violation,
                policy=policy.name,
                approval_required=False,
            )

        if classification == CommandClassification.DESTRUCTIVE:
            has_destructive = True
        if classification == CommandClassification.PRIVILEGED:
            has_privileged = True
        if classification == CommandClassification.NETWORK:
            has_network = True
        if classification == CommandClassification.INSTALL:
            has_install = True

        file_intents: list[str] = []
        try:
            from .sandbox import _extract_path_intents

            file_intents = _extract_path_intents(cmd)
        except Exception:
            pass

        cost_estimate: str | None = None
        risk_estimate: str | None = None
        if classification == CommandClassification.READ_ONLY:
            cost_estimate = "none"
            risk_estimate = "low"
        elif classification == CommandClassification.WRITES_WORKSPACE:
            cost_estimate = "none"
            risk_estimate = "medium"
        elif classification == CommandClassification.NETWORK:
            cost_estimate = "unknown"
            risk_estimate = "medium"
        elif classification == CommandClassification.INSTALL:
            cost_estimate = "unknown"
            risk_estimate = "high"
        elif classification == CommandClassification.DESTRUCTIVE:
            cost_estimate = "none"
            risk_estimate = "critical"
        elif classification == CommandClassification.PRIVILEGED:
            cost_estimate = "none"
            risk_estimate = "critical"
        else:
            cost_estimate = "unknown"
            risk_estimate = "unknown"

        steps.append(
            PlanStep(
                step_index=idx,
                command=cmd,
                classification=classification,
                decision=decision,
                file_intents=file_intents,
                approval_required=decision.approval_required,
                cost_estimate=cost_estimate,
                risk_estimate=risk_estimate,
                detail=path_violation,
            )
        )

    denied_steps = sum(1 for s in steps if not s.decision.allowed)
    pending_steps = sum(
        1 for s in steps if s.decision.approval_required and s.decision.allowed is False
    )
    approved_steps = sum(1 for s in steps if s.decision.allowed)

    overall_allowed = denied_steps == 0 and pending_steps == 0
    if has_destructive or has_privileged:
        overall_allowed = False
        overall_reason = "destructive or privileged commands denied"
    elif pending_steps > 0:
        overall_reason = f"{pending_steps} step(s) require approval"
    elif denied_steps > 0:
        overall_reason = f"{denied_steps} step(s) denied by policy"
    else:
        overall_reason = "all steps allowed"

    risk_summary: str | None = None
    if has_destructive or has_privileged:
        risk_summary = "critical"
    elif has_install:
        risk_summary = "high"
    elif has_network:
        risk_summary = "medium"
    elif any(s.classification == CommandClassification.WRITES_WORKSPACE for s in steps):
        risk_summary = "medium"
    elif steps:
        risk_summary = "low"

    return PlanDecision(
        plan_id=pid,
        policy=policy.name,
        workspace_root=str(policy.workspace_root),
        steps=steps,
        total_steps=len(steps),
        approved_steps=approved_steps,
        denied_steps=denied_steps,
        pending_approval_steps=pending_steps,
        has_destructive=has_destructive,
        has_privileged=has_privileged,
        has_network=has_network,
        has_install=has_install,
        overall_allowed=overall_allowed,
        overall_reason=overall_reason,
        cost_summary="unknown" if any(s.cost_estimate == "unknown" for s in steps) else "none",
        risk_summary=risk_summary,
    )


def build_plan_audit_event(plan: PlanDecision) -> dict[str, object]:
    """Build a stable local audit event for plan explanation/decision."""
    return {
        "type": "plan_decision",
        "plan_id": plan.plan_id,
        "policy": plan.policy,
        "workspace_root": plan.workspace_root,
        "created_at": plan.created_at,
        "overall_allowed": plan.overall_allowed,
        "overall_reason": plan.overall_reason,
        "total_steps": plan.total_steps,
        "approved_steps": plan.approved_steps,
        "denied_steps": plan.denied_steps,
        "pending_approval_steps": plan.pending_approval_steps,
        "has_destructive": plan.has_destructive,
        "has_privileged": plan.has_privileged,
        "has_network": plan.has_network,
        "has_install": plan.has_install,
        "steps": [
            {
                "step_index": step.step_index,
                "command": step.command,
                "classification": step.classification.value,
                "allowed": step.decision.allowed,
                "approval_required": step.approval_required,
                "reason": step.decision.reason,
            }
            for step in plan.steps
        ],
    }


def persist_plan_audit_event(plan: PlanDecision, workspace_root: Path | None = None) -> Path:
    """Persist a best-effort local plan audit event under `.arc/audit`."""
    root = workspace_root or Path(plan.workspace_root)
    audit_path = root / ".arc" / "audit" / "plan.events.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = build_plan_audit_event(plan)
    audit_path.open("a", encoding="utf-8").write(json.dumps(event, sort_keys=True) + "\n")
    return audit_path
