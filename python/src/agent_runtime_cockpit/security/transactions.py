"""ARC-owned file transaction log with safe undo/redo.

This intentionally does not call destructive git restore/reset operations. Git is
used only for repository metadata when present; file restoration is bounded to
the files ARC recorded in the transaction.
"""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..storage.atomic import write_text_atomic
from .sandbox import utc_now


class TransactionFile(BaseModel):
    path: str
    before_exists: bool
    before_hash: str
    before_content: str | None = None
    after_exists: bool
    after_hash: str
    after_content: str | None = None


class ArcTransaction(BaseModel):
    version: Literal[1] = 1
    transaction_id: str = Field(default_factory=lambda: f"txn-{uuid.uuid4().hex[:12]}")
    workspace_root: str
    source: str
    created_at: str = Field(default_factory=utc_now)
    git_head: str | None = None
    git_status_porcelain: str | None = None
    files: list[TransactionFile]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _store_dir(workspace_root: Path) -> Path:
    return workspace_root / ".arc" / "transactions"


def transaction_path(workspace_root: Path, transaction_id: str) -> Path:
    return _store_dir(workspace_root) / f"{transaction_id}.json"


def _workspace_file(workspace_root: Path, rel: str) -> Path:
    root = workspace_root.resolve()
    path = (root / rel).resolve(strict=False)
    if not path.is_relative_to(root):
        raise ValueError(f"transaction path escapes workspace: {rel}")
    return path


def _snapshot_file(
    workspace_root: Path, rel: str, *, after_content: str | None = None
) -> TransactionFile:
    path = _workspace_file(workspace_root, rel)
    before_exists = path.exists()
    before_content = path.read_text(encoding="utf-8") if before_exists else None
    before_hash = _sha256_text(before_content or "")
    planned = after_content if after_content is not None else (before_content or "")
    return TransactionFile(
        path=rel,
        before_exists=before_exists,
        before_hash=before_hash,
        before_content=before_content,
        after_exists=True,
        after_hash=_sha256_text(planned),
        after_content=planned,
    )


def _git_metadata(workspace_root: Path) -> tuple[str | None, str | None]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_root,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        return (
            head.stdout.strip() if head.returncode == 0 else None,
            status.stdout if status.returncode == 0 else None,
        )
    except Exception:
        return None, None


def create_transaction(
    workspace_root: Path,
    *,
    source: str,
    replacements: dict[str, str],
) -> ArcTransaction:
    root = workspace_root.resolve()
    git_head, git_status = _git_metadata(root)
    txn = ArcTransaction(
        workspace_root=str(root),
        source=source,
        git_head=git_head,
        git_status_porcelain=git_status,
        files=[
            _snapshot_file(root, rel, after_content=content)
            for rel, content in replacements.items()
        ],
    )
    path = transaction_path(root, txn.transaction_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(path, txn.model_dump_json(indent=2) + "\n", lock=True)
    return txn


def load_transaction(workspace_root: Path, transaction_id: str) -> ArcTransaction:
    if not transaction_id.startswith("txn-") or "/" in transaction_id or ".." in transaction_id:
        raise ValueError("invalid transaction id")
    path = transaction_path(workspace_root.resolve(), transaction_id)
    if not path.exists():
        raise ValueError(f"transaction not found: {transaction_id}")
    return ArcTransaction.model_validate_json(path.read_text(encoding="utf-8"))


def _current_hash(path: Path) -> str:
    if not path.exists():
        return _sha256_text("")
    if not path.is_file():
        raise ValueError(f"not a file: {path}")
    return _sha256_text(path.read_text(encoding="utf-8"))


def _restore_file(path: Path, *, exists: bool, content: str | None) -> None:
    if exists:
        write_text_atomic(path, content or "", lock=True)
    elif path.exists():
        path.unlink()


def undo_transaction(workspace_root: Path, transaction_id: str) -> dict[str, Any]:
    txn = load_transaction(workspace_root, transaction_id)
    root = workspace_root.resolve()
    for file in txn.files:
        path = _workspace_file(root, file.path)
        if _current_hash(path) != file.after_hash:
            return {
                "ok": False,
                "transaction_id": transaction_id,
                "reason": "current file differs from transaction after-state",
                "path": file.path,
            }
    for file in txn.files:
        _restore_file(
            _workspace_file(root, file.path), exists=file.before_exists, content=file.before_content
        )
    return {
        "ok": True,
        "transaction_id": transaction_id,
        "operation": "undo",
        "files": [f.path for f in txn.files],
    }


def redo_transaction(workspace_root: Path, transaction_id: str) -> dict[str, Any]:
    txn = load_transaction(workspace_root, transaction_id)
    root = workspace_root.resolve()
    for file in txn.files:
        path = _workspace_file(root, file.path)
        if _current_hash(path) != file.before_hash:
            return {
                "ok": False,
                "transaction_id": transaction_id,
                "reason": "current file differs from transaction before-state",
                "path": file.path,
            }
    for file in txn.files:
        _restore_file(
            _workspace_file(root, file.path), exists=file.after_exists, content=file.after_content
        )
    return {
        "ok": True,
        "transaction_id": transaction_id,
        "operation": "redo",
        "files": [f.path for f in txn.files],
    }
