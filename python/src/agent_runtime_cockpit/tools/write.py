"""Workspace-bound write tools for provider-backed coding agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.security.sandbox import (
    is_path_within_root,
    persist_sandbox_audit_event,
    utc_now,
)
from agent_runtime_cockpit.security.trust import TRUST_DB, ensure_trusted
from agent_runtime_cockpit.tools.protocol import ToolResult


class WriteFileArgs(BaseModel):
    path: str = Field(description="Workspace-relative or absolute file path to write")
    content: str = Field(description="Complete file content")


class EditFileArgs(BaseModel):
    path: str = Field(description="Workspace-relative or absolute file path to edit")
    old_string: str = Field(description="Exact string to replace; must occur exactly once")
    new_string: str = Field(description="Replacement string")


class CreateFileArgs(BaseModel):
    path: str = Field(description="Workspace-relative or absolute file path to create")
    content: str = Field(description="Complete file content")


def _resolve_workspace_path(raw_path: str, workspace_root: Path) -> Path:
    root = workspace_root.resolve()
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    if not is_path_within_root(resolved, root):
        raise ValueError(f"path escapes workspace: {raw_path}")
    parent = resolved.parent.resolve(strict=False)
    if not is_path_within_root(parent, root):
        raise ValueError(f"parent path escapes workspace: {raw_path}")
    if (
        candidate.exists()
        and candidate.is_symlink()
        and not is_path_within_root(candidate.resolve(), root)
    ):
        raise ValueError(f"symlink escapes workspace: {raw_path}")
    return resolved


def _persist_write_audit(tool: str, path: Path, allowed: bool, reason: str = "") -> None:
    now = utc_now()
    event: dict[str, Any] = {
        "audit_id": f"tool-write-{path.name}-{now}",
        "type": "TOOL_WRITE" if allowed else "TOOL_WRITE_DENIED",
        "tool": tool,
        "path": str(path),
        "allowed": allowed,
        "reason": reason,
        "started_at": now,
        "ended_at": now,
    }
    try:
        persist_sandbox_audit_event(event)
    except Exception:
        return


class WriteFileTool:
    """Write complete content to a workspace file."""

    name = "write_file"
    description = "Write complete content to a file inside the trusted workspace"
    output_trust_level = "untrusted"
    args_schema = WriteFileArgs
    output_byte_limit = 65536

    def __init__(self, workspace_root: Path | None = None, trust_db: Path = TRUST_DB) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.trust_db = trust_db

    def execute(self, args: WriteFileArgs, cancellation_token: CancellationToken) -> ToolResult:
        cancellation_token.raise_if_cancelled()
        try:
            ensure_trusted(self.workspace_root, trust_db=self.trust_db, allow_if_no_db=True)
            path = _resolve_workspace_path(args.path, self.workspace_root)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = args.content.encode("utf-8")
            path.write_bytes(data)
            _persist_write_audit(self.name, path, True)
            return ToolResult(content={"path": str(path), "bytes_written": len(data)})
        except Exception as exc:  # noqa: BLE001 - tool errors are returned to model.
            _persist_write_audit(self.name, self.workspace_root / args.path, False, str(exc))
            return ToolResult(content={"error": str(exc), "path": args.path})


class EditFileTool:
    """Apply a targeted exact string replacement inside a workspace file."""

    name = "edit_file"
    description = "Replace one exact string occurrence in a file inside the trusted workspace"
    output_trust_level = "untrusted"
    args_schema = EditFileArgs
    output_byte_limit = 65536

    def __init__(self, workspace_root: Path | None = None, trust_db: Path = TRUST_DB) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.trust_db = trust_db

    def execute(self, args: EditFileArgs, cancellation_token: CancellationToken) -> ToolResult:
        cancellation_token.raise_if_cancelled()
        try:
            ensure_trusted(self.workspace_root, trust_db=self.trust_db, allow_if_no_db=True)
            if not args.old_string:
                raise ValueError("old_string must not be empty")
            path = _resolve_workspace_path(args.path, self.workspace_root)
            text = path.read_text(encoding="utf-8")
            count = text.count(args.old_string)
            if count != 1:
                raise ValueError(f"old_string must occur exactly once; found {count}")
            path.write_text(text.replace(args.old_string, args.new_string, 1), encoding="utf-8")
            _persist_write_audit(self.name, path, True)
            return ToolResult(content={"path": str(path), "applied": True})
        except Exception as exc:  # noqa: BLE001
            _persist_write_audit(self.name, self.workspace_root / args.path, False, str(exc))
            return ToolResult(content={"error": str(exc), "path": args.path, "applied": False})


class CreateFileTool:
    """Create a new workspace file; fails if it already exists."""

    name = "create_file"
    description = "Create a new file inside the trusted workspace; fails if it exists"
    output_trust_level = "untrusted"
    args_schema = CreateFileArgs
    output_byte_limit = 65536

    def __init__(self, workspace_root: Path | None = None, trust_db: Path = TRUST_DB) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.trust_db = trust_db

    def execute(self, args: CreateFileArgs, cancellation_token: CancellationToken) -> ToolResult:
        cancellation_token.raise_if_cancelled()
        try:
            ensure_trusted(self.workspace_root, trust_db=self.trust_db, allow_if_no_db=True)
            path = _resolve_workspace_path(args.path, self.workspace_root)
            if path.exists():
                raise ValueError(f"file already exists: {args.path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args.content, encoding="utf-8")
            _persist_write_audit(self.name, path, True)
            return ToolResult(content={"path": str(path), "created": True})
        except Exception as exc:  # noqa: BLE001
            _persist_write_audit(self.name, self.workspace_root / args.path, False, str(exc))
            return ToolResult(content={"error": str(exc), "path": args.path, "created": False})
