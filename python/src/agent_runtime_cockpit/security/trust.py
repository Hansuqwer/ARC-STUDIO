"""
Workspace trust resolver — ADR-006 P1a advisory mode.

Trust state is stored outside the workspace (``~/.arc/trusted-workspaces.json``).
A committed ``.arc/trusted`` file is explicitly ignored — the workspace must
not self-authorize.
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

TRUST_DB = Path.home() / ".arc" / "trusted-workspaces.json"


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
    """Resolve workspace trust level.

    P1a: advisory only — does not block execution.
    Returns ``TRUSTED`` if the workspace path is in the external trust DB,
    ``UNTRUSTED`` otherwise.
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
