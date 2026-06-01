"""ARC input validation — prevents path traversal and unsafe inputs."""

from __future__ import annotations

import re
from pathlib import Path

# Canonical safe environment-variable allowlist.
#
# SINGLE source of truth shared by the isolation providers
# (isolation/subprocess.py) and the command-level policy
# (security/sandbox.py: SandboxPolicy.env_allowlist). Defined in this dependency
# leaf module so both layers can import it without a circular import, and so the
# effective allowlist can never diverge by call path.
#
# SHELL is intentionally excluded: sandboxed argv runs without a shell, so the
# child has no need for it (least-environment).
SAFE_ENV_KEYS: tuple[str, ...] = (
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_ALL",
    "TERM",
    "TMPDIR",
    "VIRTUAL_ENV",
    "PYTHONPATH",
    "PYTHONWARNINGS",
)


def validate_workspace_path(path_str: str) -> Path:
    """Validate and resolve a workspace path. Raises ValueError on bad input.

    Path-traversal safety comes from full resolution (``Path.resolve()``) plus
    existence/type checks, not from a substring scan for ``..``. A substring
    check both over-rejects legitimate paths (e.g. ``/srv/my..app``) and gives a
    false sense of security, since ``..`` is not the only way to traverse.
    Callers that must confine a path to a workspace root should additionally use
    :func:`agent_runtime_cockpit.security.sandbox.is_path_within_root`.
    """
    if not path_str:
        raise ValueError("Workspace path must not be empty")

    # Reject embedded NUL bytes outright (invalid on every supported OS and a
    # classic path-truncation trick).
    if "\x00" in path_str:
        raise ValueError("Workspace path must not contain NUL bytes")

    resolved = Path(path_str).resolve()

    # Must be an existing directory
    if not resolved.exists():
        raise ValueError(f"Workspace path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Workspace path is not a directory: {resolved}")

    return resolved


def validate_run_id(run_id: str) -> str:
    """Validate a run ID (alphanumeric + hyphens only)."""
    if not re.match(r"^[\w\-]{1,64}$", run_id):
        raise ValueError(f"Invalid run_id: {run_id!r}")
    return run_id


def validate_workflow_id(wf_id: str) -> str:
    """Validate a workflow ID."""
    if not re.match(r"^[\w\-\.]{1,128}$", wf_id):
        raise ValueError(f"Invalid workflow_id: {wf_id!r}")
    return wf_id
