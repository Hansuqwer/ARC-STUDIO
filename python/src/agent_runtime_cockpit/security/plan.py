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
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field

from ..audit.chain import canonical_dumps, sha256_hex
from ..isolation.base import IsolationResult
from .sandbox import (
    CommandClassification,
    SandboxDecision,
    SandboxPathViolation,
    SandboxPolicy,
    SandboxResult,
    approval_token_hash,
    build_audit_event,
    classify_command,
    decide,
    persist_sandbox_audit_event,
    utc_now,
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


class PlanApproval(BaseModel):
    """Persisted approval bound to one exact plan record."""

    model_config = {"frozen": True}

    version: Literal[1] = 1
    approval_id: str
    plan_id: str
    plan_hash: str
    token_hash: str
    policy: str
    workspace_root: str
    approved_at: str = Field(default_factory=utc_now)


class PlanApplyResult(BaseModel):
    """Stable result for plan apply."""

    plan_id: str
    policy: str
    workspace_root: str
    approved: bool
    applied: bool
    reason: str
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    results: list[SandboxResult] = Field(default_factory=list)


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


def plan_store_dir(workspace_root: Path) -> Path:
    return workspace_root / ".arc" / "plans"


def plan_record_path(workspace_root: Path, plan_id: str) -> Path:
    return plan_store_dir(workspace_root) / f"{plan_id}.json"


def plan_approval_path(workspace_root: Path, plan_id: str) -> Path:
    return plan_store_dir(workspace_root) / f"{plan_id}.approval.json"


def plan_hash(plan: PlanDecision) -> str:
    payload = plan.model_dump(mode="json", exclude={"created_at"})
    return sha256_hex(canonical_dumps(payload))


def persist_plan_record(plan: PlanDecision, workspace_root: Path | None = None) -> Path:
    root = workspace_root or Path(plan.workspace_root)
    path = plan_record_path(root, plan.plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def load_plan_record(workspace_root: Path, plan_id: str) -> PlanDecision:
    path = plan_record_path(workspace_root, plan_id)
    if not path.exists():
        raise ValueError(f"plan record not found: {plan_id}")
    return PlanDecision.model_validate(json.loads(path.read_text(encoding="utf-8")))


def approve_plan(
    plan: PlanDecision, token: str, workspace_root: Path | None = None
) -> PlanApproval:
    if plan.has_destructive or plan.has_privileged:
        raise ValueError("destructive or privileged plans cannot be approved")
    approval = PlanApproval(
        approval_id=f"plan-approval-{uuid.uuid4().hex}",
        plan_id=plan.plan_id,
        plan_hash=plan_hash(plan),
        token_hash=approval_token_hash(token),
        policy=plan.policy,
        workspace_root=str(Path(plan.workspace_root).resolve()),
    )
    root = workspace_root or Path(plan.workspace_root)
    path = plan_approval_path(root, plan.plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(approval.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return approval


def load_plan_approval(workspace_root: Path, plan_id: str) -> PlanApproval:
    path = plan_approval_path(workspace_root, plan_id)
    if not path.exists():
        raise ValueError("approved plan token/record required")
    return PlanApproval.model_validate(json.loads(path.read_text(encoding="utf-8")))


def verify_plan_approval(
    plan: PlanDecision, token: str | None, workspace_root: Path
) -> PlanApproval:
    if not token:
        raise ValueError("approved plan token/record required")
    approval = load_plan_approval(workspace_root, plan.plan_id)
    if approval.plan_hash != plan_hash(plan):
        raise ValueError("plan record changed after approval")
    if approval.token_hash != approval_token_hash(token):
        raise ValueError("approval token does not match plan")
    if approval.policy != plan.policy:
        raise ValueError("approval policy does not match plan")
    if approval.workspace_root != str(workspace_root.resolve()):
        raise ValueError("approval workspace does not match plan")
    return approval


def build_plan_apply_event(
    event_type: str,
    *,
    plan_id: str,
    policy: str,
    workspace_root: Path,
    reason: str,
    approval_id: str | None = None,
    command: list[str] | None = None,
    exit_code: int | None = None,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "event_id": f"plan-{uuid.uuid4().hex}",
        "plan_id": plan_id,
        "policy": policy,
        "workspace_root": str(workspace_root),
        "approval_id": approval_id,
        "command": command or [],
        "reason": reason,
        "exit_code": exit_code,
        "created_at": utc_now(),
    }


def persist_plan_event(event: dict[str, Any], workspace_root: Path) -> Path:
    audit_path = workspace_root / ".arc" / "audit" / "plan.events.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.open("a", encoding="utf-8").write(
        json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    )
    return audit_path


def sandbox_result_from_isolation(
    *,
    command: list[str],
    cwd: Path,
    decision: SandboxDecision,
    provider: str,
    iso: IsolationResult,
    started_at: str,
    ended_at: str,
) -> SandboxResult:
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=iso.provider if iso.provider != "unknown" else provider,
        started_at=started_at,
        ended_at=ended_at,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    return SandboxResult(
        command=command,
        cwd=str(cwd),
        classification=decision.classification,
        decision=decision,
        provider=iso.provider if iso.provider != "unknown" else provider,
        exit_code=iso.exit_code,
        stdout=iso.stdout,
        stderr=iso.stderr,
        duration_ms=iso.duration_ms,
        timed_out=iso.killed and iso.kill_reason == "timeout",
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
        audit_event=audit,
    )
