"""Safety-gated edit-loop helpers for CLI and REPL."""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field

from ..storage.atomic import write_text_atomic
from .plan import build_plan, build_plan_apply_event, persist_plan_audit_event, persist_plan_event
from .sandbox import (
    SandboxPolicy,
    approval_token_hash,
    ensure_workspace_cwd,
    resolve_sandbox_policy,
    utc_now,
)


class EditFilePlan(BaseModel):
    """One file entry in an edit plan."""

    path: str
    command: list[str]
    original_exists: bool
    original_hash: str
    replacement_hash: str | None = None
    patch_hash: str | None = None
    allowed: bool
    reason: str
    classification: str
    diff: str = ""


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
    files: list[EditFilePlan] = Field(default_factory=list)


class EditPlanApproval(BaseModel):
    """Persisted approval scoped to exact edit-plan metadata."""

    version: Literal[1] = 1
    approval_id: str = Field(default_factory=lambda: f"edit-approval-{uuid.uuid4().hex}")
    plan_id: str
    token_hash: str
    plan_hash: str
    approved_at: str = Field(default_factory=utc_now)


def edit_plan_store_dir(workspace_root: Path) -> Path:
    return workspace_root / ".arc" / "edit-plans"


def edit_plan_record_path(workspace_root: Path, plan_id: str) -> Path:
    return edit_plan_store_dir(workspace_root) / f"{plan_id}.json"


def edit_plan_approval_path(workspace_root: Path, plan_id: str) -> Path:
    return edit_plan_store_dir(workspace_root) / f"{plan_id}.approval.json"


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


def _plan_hash(plan: EditPlan) -> str:
    payload = plan.model_dump(
        mode="json", exclude={"diff", "audit_path", "plan_path", "created_at"}
    )
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


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
    for file_plan in payload.get("files", []):
        file_plan.pop("diff", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_edit_plan_record(workspace_root: Path, plan_id: str) -> EditPlan:
    path = edit_plan_record_path(workspace_root, plan_id)
    if not path.exists():
        raise ValueError(f"edit plan record not found: {plan_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("diff", "")
    for file_plan in data.get("files", []):
        file_plan.setdefault("diff", "")
    data["plan_path"] = str(path)
    return EditPlan.model_validate(data)


def list_edit_plan_records(workspace_root: Path, limit: int = 50) -> list[EditPlan]:
    store = edit_plan_store_dir(workspace_root)
    if not store.exists():
        return []
    plans: list[EditPlan] = []
    for path in sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.name.endswith(".approval.json"):
            continue
        try:
            plans.append(load_edit_plan_record(workspace_root, path.stem))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if len(plans) >= limit:
            break
    return plans


def edit_plan_status(workspace_root: Path, plan: EditPlan) -> str:
    """Return present/stale/denied for a saved plan using current file hashes."""
    if not plan.allowed:
        return "denied"
    for file_plan in plan.files or [
        EditFilePlan(
            path=plan.path,
            command=plan.command,
            original_exists=plan.original_exists,
            original_hash=plan.original_hash,
            replacement_hash=plan.replacement_hash,
            allowed=plan.allowed,
            reason=plan.reason,
            classification=plan.classification,
        )
    ]:
        if (
            file_content_hash(_workspace_file(file_plan.path, workspace_root))
            != file_plan.original_hash
        ):
            return "stale"
    return "present"


def approve_edit_plan(workspace_root: Path, plan_id: str, token: str) -> EditPlanApproval:
    plan = load_edit_plan_record(workspace_root, plan_id)
    if not plan.allowed:
        raise ValueError("denied edit plans cannot be approved")
    approval = EditPlanApproval(
        plan_id=plan.plan_id,
        token_hash=approval_token_hash(token),
        plan_hash=_plan_hash(plan),
    )
    path = edit_plan_approval_path(workspace_root, plan.plan_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(approval.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return approval


def verify_edit_plan_approval(workspace_root: Path, plan: EditPlan, token: str | None) -> bool:
    if not token:
        return False
    path = edit_plan_approval_path(workspace_root, plan.plan_id)
    if not path.exists():
        return False
    approval = EditPlanApproval.model_validate_json(path.read_text(encoding="utf-8"))
    return approval.token_hash == approval_token_hash(token) and approval.plan_hash == _plan_hash(
        plan
    )


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _parse_hunk_range(value: str | None) -> int:
    return 1 if value is None else int(value)


def apply_unified_patch(old: str, patch: str, *, expected_path: str | None = None) -> str:
    """Apply a text-only single-file unified diff without shelling out."""
    if "\x00" in patch:
        raise ValueError("binary patch content is unsupported")
    lines = patch.splitlines()
    if len(lines) < 4 or not lines[0].startswith("--- ") or not lines[1].startswith("+++ "):
        raise ValueError("malformed unified diff header")
    patch_path = lines[1][4:].strip().split("\t", 1)[0].split(" ", 1)[0]
    if patch_path.startswith("b/"):
        patch_path = patch_path[2:]
    if expected_path and patch_path not in {expected_path, f"./{expected_path}"}:
        raise ValueError("patch target does not match --path")
    old_lines = old.splitlines()
    output: list[str] = []
    index = 0
    line_index = 2
    while line_index < len(lines):
        match = _HUNK_RE.match(lines[line_index])
        if not match:
            raise ValueError("malformed unified diff hunk")
        old_start = int(match.group(1))
        old_count = _parse_hunk_range(match.group(2))
        new_count = _parse_hunk_range(match.group(4))
        target_index = max(old_start - 1, 0)
        if target_index < index:
            raise ValueError("overlapping unified diff hunk")
        output.extend(old_lines[index:target_index])
        index = target_index
        old_seen = 0
        new_seen = 0
        line_index += 1
        while line_index < len(lines) and not lines[line_index].startswith("@@"):
            line = lines[line_index]
            if not line:
                raise ValueError("blank patch control line is unsupported")
            marker = line[0]
            text = line[1:]
            if marker == " ":
                if index >= len(old_lines) or old_lines[index] != text:
                    raise ValueError("patch context does not match current file")
                output.append(text)
                index += 1
                old_seen += 1
                new_seen += 1
            elif marker == "-":
                if index >= len(old_lines) or old_lines[index] != text:
                    raise ValueError("patch removal does not match current file")
                index += 1
                old_seen += 1
            elif marker == "+":
                output.append(text)
                new_seen += 1
            else:
                raise ValueError("unsupported unified diff line")
            line_index += 1
        if old_seen != old_count or new_seen != new_count:
            raise ValueError("unified diff hunk line count mismatch")
    output.extend(old_lines[index:])
    text = "\n".join(output)
    return text + ("\n" if old.endswith("\n") else "")


def _file_plan(
    *,
    path_arg: str,
    content: str,
    workspace_root: Path,
    policy: SandboxPolicy,
    patch: str | None = None,
) -> EditFilePlan:
    path = _workspace_file(path_arg, workspace_root)
    rel = str(path.relative_to(workspace_root))
    command = ["python", "-c", f"from pathlib import Path; Path({rel!r}).write_text(...)"]
    plan = build_plan([command], policy)
    step = plan.steps[0]
    original_exists = path.exists()
    old = path.read_text(encoding="utf-8") if original_exists else ""
    replacement = (
        apply_unified_patch(old, patch, expected_path=rel) if patch is not None else content
    )
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            replacement.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            lineterm="",
        )
    )
    return EditFilePlan(
        path=rel,
        command=command,
        original_exists=original_exists,
        original_hash=_sha256_text(old),
        replacement_hash=_sha256_text(replacement) if patch is None else None,
        patch_hash=_sha256_text(patch) if patch is not None else None,
        allowed=plan.overall_allowed,
        reason=plan.overall_reason if plan.overall_allowed else step.decision.reason,
        classification=step.classification.value,
        diff=diff,
    )


def build_edit_plan(
    *,
    path_arg: str,
    content: str,
    workspace_root: Path,
    policy_name: str = "local-safe",
) -> EditPlan:
    """Build a non-executing edit preview through sandbox plan policy."""
    return build_edit_bundle(
        edits=[{"path": path_arg, "content": content}],
        workspace_root=workspace_root,
        policy_name=policy_name,
    )


def build_edit_bundle(
    *,
    edits: list[dict[str, str]],
    workspace_root: Path,
    policy_name: str = "local-safe",
) -> EditPlan:
    ws = workspace_root.resolve()
    policy: SandboxPolicy = resolve_sandbox_policy(policy_name, ws)
    if not edits:
        raise ValueError("missing edit")
    files = [
        _file_plan(
            path_arg=item["path"],
            content=item.get("content", ""),
            patch=item.get("patch"),
            workspace_root=ws,
            policy=policy,
        )
        for item in edits
    ]
    if len({file.path for file in files}) != len(files):
        raise ValueError("duplicate edit path")
    commands = [file.command for file in files]
    plan = build_plan(commands, policy)
    audit_path = persist_plan_audit_event(plan, ws)
    first = files[0]
    allowed = all(file.allowed for file in files)
    reason = "all files allowed" if allowed else "one or more files denied"
    edit_plan = EditPlan(
        plan_id=plan.plan_id,
        workspace_root=str(ws),
        policy=policy.name,
        path=first.path,
        command=first.command,
        original_exists=first.original_exists,
        original_hash=first.original_hash,
        replacement_hash=first.replacement_hash or "",
        allowed=allowed,
        reason=reason,
        classification=first.classification,
        diff="\n".join(file.diff for file in files if file.diff),
        audit_path=str(audit_path),
        files=files,
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
    approval_token: str | None = None,
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
    if not approved and not verify_edit_plan_approval(ws, saved_plan or plan, approval_token):
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


def apply_edit_bundle(
    *,
    edits: list[dict[str, str]],
    workspace_root: Path,
    policy_name: str = "local-safe",
    approved: bool = False,
    plan_id: str | None = None,
    approval_token: str | None = None,
) -> dict[str, Any]:
    ws = workspace_root.resolve()
    ensure_workspace_cwd(ws, ws)
    saved_plan = load_edit_plan_record(ws, plan_id) if plan_id else None
    if saved_plan:
        policy_name = saved_plan.policy
        if len(edits) != len(saved_plan.files):
            return _edit_apply_denied(
                plan=saved_plan, workspace_root=ws, reason="edit count does not match edit plan"
            )
    plan = build_edit_bundle(edits=edits, workspace_root=ws, policy_name=policy_name)
    check_plan = saved_plan or plan
    if saved_plan:
        provided = {item["path"]: item for item in edits}
        for file_plan in saved_plan.files:
            item = provided.get(file_plan.path)
            if item is None:
                return _edit_apply_denied(
                    plan=saved_plan, workspace_root=ws, reason="edit path missing from saved plan"
                )
            if (
                file_plan.replacement_hash
                and _sha256_text(item.get("content", "")) != file_plan.replacement_hash
            ):
                return _edit_apply_denied(
                    plan=saved_plan,
                    workspace_root=ws,
                    reason="replacement content does not match edit plan",
                )
            if file_plan.patch_hash and _sha256_text(item.get("patch", "")) != file_plan.patch_hash:
                return _edit_apply_denied(
                    plan=saved_plan,
                    workspace_root=ws,
                    reason="patch content does not match edit plan",
                )
    if not plan.allowed:
        return _edit_apply_denied(plan=plan, workspace_root=ws, reason=plan.reason)
    if not approved and not verify_edit_plan_approval(ws, check_plan, approval_token):
        return _edit_apply_denied(plan=check_plan, workspace_root=ws, reason="approval required")
    current: dict[str, str] = {}
    expected = {file.path: file.original_hash for file in check_plan.files}
    for file_plan in plan.files:
        path = _workspace_file(file_plan.path, ws)
        current_hash = file_content_hash(path)
        current[file_plan.path] = current_hash
        if current_hash != expected[file_plan.path]:
            return _edit_apply_denied(
                plan=check_plan,
                workspace_root=ws,
                reason="file changed since preview",
                extra={"current_hashes": current, "expected_original_hashes": expected},
            )
    replacements = {item["path"]: item for item in edits}
    for file_plan in plan.files:
        path = _workspace_file(file_plan.path, ws)
        item = replacements[file_plan.path]
        if "patch" in item:
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            content = apply_unified_patch(old, item["patch"], expected_path=file_plan.path)
        else:
            content = item.get("content", "")
        write_text_atomic(path, content, lock=True)
    event = build_plan_apply_event(
        "edit_apply_applied",
        plan_id=check_plan.plan_id,
        policy=check_plan.policy,
        workspace_root=ws,
        reason="applied",
        command=[arg for file in check_plan.files for arg in file.command],
        exit_code=0,
    )
    audit_path = persist_plan_event(event, ws)
    return {
        "applied": True,
        "reason": "applied",
        "plan": check_plan.model_dump(mode="json"),
        "audit_events": [{**event, "audit_path": str(audit_path)}],
    }
