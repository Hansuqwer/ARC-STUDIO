"""Safety-gated edit-loop helpers for CLI and REPL."""

from __future__ import annotations

import difflib
import hashlib
import json
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
    original_exists: bool
    original_hash: str
    replacement_hash: str
    allowed: bool
    reason: str
    classification: str
    diff: str
    audit_path: str | None = None
    plan_path: str | None = None
    created_at: str = Field(default_factory=utc_now)


def edit_plan_store_dir(workspace_root: Path) -> Path:
    return workspace_root / ".arc" / "edit-plans"


def edit_plan_record_path(workspace_root: Path, plan_id: str) -> Path:
    return edit_plan_store_dir(workspace_root) / f"{plan_id}.json"


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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_content_hash(path: Path) -> str:
    """Return stable hash for current file content, or empty-file hash if absent."""
    if not path.exists():
        return _sha256_text("")
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    return _sha256_text(path.read_text(encoding="utf-8"))


def persist_edit_plan_record(plan: EditPlan, workspace_root: Path | None = None) -> Path:
    """Persist safe edit-plan metadata without replacement content or diff."""
    root = workspace_root or Path(plan.workspace_root)
    path = edit_plan_record_path(root, plan.plan_id)
    payload = plan.model_dump(mode="json", exclude={"diff", "audit_path", "plan_path"})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_edit_plan_record(workspace_root: Path, plan_id: str) -> EditPlan:
    path = edit_plan_record_path(workspace_root, plan_id)
    if not path.exists():
        raise ValueError(f"edit plan record not found: {plan_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("diff", "")
    data["plan_path"] = str(path)
    return EditPlan.model_validate(data)


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
    original_exists = path.exists()
    old = path.read_text(encoding="utf-8") if original_exists else ""
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
    )
    edit_plan = EditPlan(
        plan_id=plan.plan_id,
        workspace_root=str(ws),
        policy=policy.name,
        path=rel,
        command=command,
        original_exists=original_exists,
        original_hash=_sha256_text(old),
        replacement_hash=_sha256_text(content),
        allowed=plan.overall_allowed,
        reason=plan.overall_reason if plan.overall_allowed else step.decision.reason,
        classification=step.classification.value,
        diff=diff,
        audit_path=str(audit_path),
    )
    plan_path = persist_edit_plan_record(edit_plan, ws)
    return edit_plan.model_copy(update={"plan_path": str(plan_path)})


def _edit_apply_denied(
    *,
    plan: EditPlan,
    workspace_root: Path,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = build_plan_apply_event(
        "edit_apply_denied",
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=workspace_root,
        reason=reason,
        command=plan.command,
    )
    audit_path = persist_plan_event(event, workspace_root)
    return {
        "applied": False,
        "reason": reason,
        "plan": plan.model_dump(mode="json"),
        "audit_events": [{**event, "audit_path": str(audit_path)}],
        **(extra or {}),
    }


def apply_edit_plan(
    *,
    path_arg: str,
    content: str,
    workspace_root: Path,
    policy_name: str = "local-safe",
    approved: bool = False,
    expected_original_hash: str | None = None,
    plan_id: str | None = None,
) -> dict[str, Any]:
    """Apply an edit only after sandbox policy allows it and caller approves."""
    ws = workspace_root.resolve()
    ensure_workspace_cwd(ws, ws)
    saved_plan: EditPlan | None = None
    if plan_id:
        saved_plan = load_edit_plan_record(ws, plan_id)
        path_arg = saved_plan.path
        policy_name = saved_plan.policy
        expected_original_hash = expected_original_hash or saved_plan.original_hash
        replacement_hash = _sha256_text(content)
        if replacement_hash != saved_plan.replacement_hash:
            return _edit_apply_denied(
                plan=saved_plan,
                workspace_root=ws,
                reason="replacement content does not match edit plan",
                extra={
                    "replacement_hash": replacement_hash,
                    "expected_replacement_hash": saved_plan.replacement_hash,
                },
            )
    plan = build_edit_plan(
        path_arg=path_arg,
        content=content,
        workspace_root=ws,
        policy_name=policy_name,
    )
    if not plan.allowed:
        return _edit_apply_denied(plan=plan, workspace_root=ws, reason=plan.reason)
    if not approved:
        return _edit_apply_denied(plan=plan, workspace_root=ws, reason="approval required")
    path = _workspace_file(path_arg, ws)
    current_hash = file_content_hash(path)
    if expected_original_hash and current_hash != expected_original_hash:
        return _edit_apply_denied(
            plan=saved_plan or plan,
            workspace_root=ws,
            reason="file changed since preview",
            extra={
                "current_hash": current_hash,
                "expected_original_hash": expected_original_hash,
            },
        )
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
