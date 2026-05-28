"""Safety-gated edit-loop helpers for CLI and REPL."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field

from ..storage.atomic import write_text_atomic
from .plan import build_plan, build_plan_apply_event, persist_plan_audit_event, persist_plan_event
from .sandbox import SandboxPolicy, ensure_workspace_cwd, resolve_sandbox_policy, utc_now


class EditPlan(BaseModel):
    """Stable preview for one workspace file replacement."""

    version: Literal[1] = 1
    plan_id: str = Field(default_factory=lambda: f"edit-{uuid.uuid4().hex[:12]}")
    workspace_root: str
    policy: str
    path: str
    command: list[str]
    allowed: bool
    reason: str
    classification: str
    diff: str
    audit_path: str | None = None
    created_at: str = Field(default_factory=utc_now)


def _workspace_file(path_arg: str, workspace_root: Path) -> Path:
    if not path_arg:
        raise ValueError("missing path")
    root = workspace_root.resolve()
    raw = Path(path_arg).expanduser()
    candidate = raw if raw.is_absolute() else root / raw
    resolved = candidate.resolve(strict=False)
    if candidate.exists() and candidate.is_symlink():
        raise ValueError(f"path is a symlink: {path_arg}")
    if not resolved.is_relative_to(root):
        raise ValueError(f"path escapes workspace: {path_arg}")
    return resolved


def build_edit_plan(
    *,
    path_arg: str,
    content: str,
    workspace_root: Path,
    policy_name: str = "local-safe",
) -> EditPlan:
    """Build a non-executing edit preview through sandbox plan policy."""
    ws = workspace_root.resolve()
    policy: SandboxPolicy = resolve_sandbox_policy(policy_name, ws)
    path = _workspace_file(path_arg, ws)
    rel = str(path.relative_to(ws))
    command = ["python", "-c", f"from pathlib import Path; Path({rel!r}).write_text(...)"]
    plan = build_plan([command], policy)
    audit_path = persist_plan_audit_event(plan, ws)
    step = plan.steps[0]
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
    )
    return EditPlan(
        plan_id=plan.plan_id,
        workspace_root=str(ws),
        policy=policy.name,
        path=rel,
        command=command,
        allowed=plan.overall_allowed,
        reason=plan.overall_reason if plan.overall_allowed else step.decision.reason,
        classification=step.classification.value,
        diff=diff,
        audit_path=str(audit_path),
    )


def apply_edit_plan(
    *,
    path_arg: str,
    content: str,
    workspace_root: Path,
    policy_name: str = "local-safe",
    approved: bool = False,
) -> dict[str, Any]:
    """Apply an edit only after sandbox policy allows it and caller approves."""
    ws = workspace_root.resolve()
    ensure_workspace_cwd(ws, ws)
    plan = build_edit_plan(
        path_arg=path_arg,
        content=content,
        workspace_root=ws,
        policy_name=policy_name,
    )
    if not plan.allowed:
        event = build_plan_apply_event(
            "edit_apply_denied",
            plan_id=plan.plan_id,
            policy=plan.policy,
            workspace_root=ws,
            reason=plan.reason,
            command=plan.command,
        )
        audit_path = persist_plan_event(event, ws)
        return {
            "applied": False,
            "reason": plan.reason,
            "plan": plan.model_dump(mode="json"),
            "audit_events": [{**event, "audit_path": str(audit_path)}],
        }
    if not approved:
        event = build_plan_apply_event(
            "edit_apply_denied",
            plan_id=plan.plan_id,
            policy=plan.policy,
            workspace_root=ws,
            reason="approval required",
            command=plan.command,
        )
        audit_path = persist_plan_event(event, ws)
        return {
            "applied": False,
            "reason": "approval required",
            "plan": plan.model_dump(mode="json"),
            "audit_events": [{**event, "audit_path": str(audit_path)}],
        }
    path = _workspace_file(path_arg, ws)
    write_text_atomic(path, content, lock=True)
    event = build_plan_apply_event(
        "edit_apply_applied",
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=ws,
        reason="applied",
        command=plan.command,
        exit_code=0,
    )
    audit_path = persist_plan_event(event, ws)
    return {
        "applied": True,
        "reason": "applied",
        "plan": plan.model_dump(mode="json"),
        "audit_events": [{**event, "audit_path": str(audit_path)}],
    }
