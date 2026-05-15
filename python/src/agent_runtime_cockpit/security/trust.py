"""
Workspace trust resolver — ADR-006 P2 enforcement mode.

Trust state is stored outside the workspace (``~/.arc/trusted-workspaces.json``).
A committed ``.arc/trusted`` file is explicitly ignored — the workspace must
not self-authorize.

``ensure_trusted()`` raises ``WorkspaceUntrusted`` for untrusted workspaces,
blocking execution. Use ``resolve_trust()`` for advisory inspection.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

TRUST_DB = Path.home() / ".arc" / "trusted-workspaces.json"


class TrustError(Exception):
    """Base exception for trust-related errors."""


class WorkspaceUntrusted(TrustError):
    """Raised when an untrusted workspace attempts to execute code.

    Attributes:
        workspace_path: Absolute path to the untrusted workspace.
        reason: Human-readable explanation of why it is untrusted.
    """

    def __init__(
        self,
        workspace_path: str,
        reason: str = "Workspace is not in external trust database",
    ) -> None:
        self.workspace_path = workspace_path
        self.reason = reason
        super().__init__(
            f"Workspace '{workspace_path}' is untrusted: {reason}. "
            f"Run 'arc workspace trust' to approve this workspace."
        )


class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    PARTIAL = "partial"
    TRUSTED = "trusted"


class TrustResolution(BaseModel):
    level: TrustLevel
    reason: str
    marker_path: str | None = None
    warning: str | None = None


def resolve_trust(
    workspace: Path,
    trust_db: Path = TRUST_DB,
) -> TrustResolution:
    """Resolve workspace trust level (advisory).

    Returns ``TRUSTED`` if the workspace path is in the external trust DB,
    ``UNTRUSTED`` otherwise. Does NOT block execution — use
    ``ensure_trusted()`` for enforcement.
    """
    workspace_path = str(workspace.resolve())
    try:
        trusted = json.loads(trust_db.read_text(encoding="utf-8"))
    except FileNotFoundError:
        trusted = {}

    entry = trusted.get(workspace_path, {})
    if entry.get("trusted") is True:
        return TrustResolution(
            level=TrustLevel.TRUSTED,
            reason="Workspace trusted in external trust database",
            marker_path=str(trust_db),
        )

    return TrustResolution(
        level=TrustLevel.UNTRUSTED,
        reason="Workspace not found in external trust database",
        warning=(
            "This workspace is not marked as trusted. "
            "Execution will proceed with subprocess isolation. "
            "Run 'arc workspace trust' to mark this workspace as trusted "
            "outside the repo."
        ),
    )


def trust_workspace(
    workspace: Path,
    note: str = "",
    trust_db: Path = TRUST_DB,
) -> TrustResolution:
    """Mark a workspace as trusted in the external trust database.

    The database lives outside the workspace at ``~/.arc/trusted-workspaces.json``
    so that a committed ``.arc/trusted`` file cannot self-authorize a repo.
    """
    trust_db.parent.mkdir(parents=True, exist_ok=True)
    try:
        trusted = json.loads(trust_db.read_text(encoding="utf-8"))
    except FileNotFoundError:
        trusted = {}

    workspace_path = str(workspace.resolve())
    trusted[workspace_path] = {
        "trusted": True,
        "note": note,
    }
    trust_db.write_text(
        json.dumps(trusted, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return TrustResolution(
        level=TrustLevel.TRUSTED,
        reason="Workspace added to external trust database",
        marker_path=str(trust_db),
    )


def untrust_workspace(
    workspace: Path,
    trust_db: Path = TRUST_DB,
) -> TrustResolution:
    """Remove a workspace from the external trust database."""
    try:
        trusted = json.loads(trust_db.read_text(encoding="utf-8"))
    except FileNotFoundError:
        trusted = {}

    workspace_path = str(workspace.resolve())
    trusted.pop(workspace_path, None)
    trust_db.write_text(
        json.dumps(trusted, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return TrustResolution(
        level=TrustLevel.UNTRUSTED,
        reason="Workspace removed from external trust database",
        marker_path=str(trust_db),
    )


def list_trusted(trust_db: Path = TRUST_DB) -> dict[str, dict]:
    """List all trusted workspaces from the external trust database."""
    try:
        return json.loads(trust_db.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def ensure_trusted(
    workspace: Path,
    trust_db: Path = TRUST_DB,
    allow_if_no_db: bool = False,
) -> TrustResolution:
    """Resolve workspace trust and raise if untrusted.

    P2 enforcement: unlike the advisory ``resolve_trust()``, this function
    raises ``WorkspaceUntrusted`` when the workspace is not in the external
    trust database. This is called by ``JobSupervisor.start_run()`` before
    execution begins.

    Args:
        workspace: Path to the workspace to check.
        trust_db: Path to the external trust database.
        allow_if_no_db: If True, allow execution when no trust DB exists
            (useful for first-run scenarios before the user has set up trust).

    Returns:
        TrustResolution if the workspace is trusted.

    Raises:
        WorkspaceUntrusted: If the workspace is untrusted.
    """
    resolution = resolve_trust(workspace, trust_db=trust_db)
    if resolution.level == TrustLevel.UNTRUSTED:
        if allow_if_no_db and not trust_db.exists():
            return resolution
        raise WorkspaceUntrusted(
            workspace_path=str(workspace.resolve()),
            reason=resolution.reason,
        )
    return resolution
