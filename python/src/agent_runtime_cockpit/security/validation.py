"""ARC input validation — prevents path traversal and unsafe inputs."""
from __future__ import annotations

import re
from pathlib import Path


def validate_workspace_path(path_str: str) -> Path:
    """Validate and resolve a workspace path. Raises ValueError on bad input."""
    if not path_str:
        raise ValueError("Workspace path must not be empty")

    # Prevent path traversal
    if ".." in path_str:
        raise ValueError(f"Path traversal not allowed: {path_str!r}")

    resolved = Path(path_str).resolve()

    # Must be an existing directory
    if not resolved.exists():
        raise ValueError(f"Workspace path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Workspace path is not a directory: {resolved}")

    return resolved


def validate_run_id(run_id: str) -> str:
    """Validate a run ID (alphanumeric + hyphens only)."""
    if not re.match(r'^[\w\-]{1,64}$', run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")
    return run_id


def validate_workflow_id(wf_id: str) -> str:
    """Validate a workflow ID."""
    if not re.match(r'^[\w\-\.]{1,128}$', wf_id):
        raise ValueError(f"Invalid workflow_id: {wf_id!r}")
    return wf_id
