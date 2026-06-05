"""Isolation backend selection (ADR-006).

Maps the persisted ``execution.isolation`` choice
(``auto|none|subprocess|docker|microvm``) to a concrete
:class:`IsolationProvider`. ``auto`` resolves to the hardened ``subprocess``
provider (the safe default); an explicit ``--provider`` override wins. ``none``
is the explicit opt-out and disables isolation — it should only be set via
``arc isolation off`` with a typed confirmation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config.model import ArcConfig
from .base import IsolationProvider

#: Backend identifiers accepted by ``execution.isolation`` and ``--provider``.
BACKENDS = ("auto", "none", "subprocess", "docker", "microvm")
_CONCRETE = ("none", "subprocess", "docker", "microvm")
DEFAULT_BACKEND = "subprocess"


def resolve_isolation_backend(
    config: Optional[ArcConfig] = None,
    *,
    override: Optional[str] = None,
) -> str:
    """Resolve the concrete isolation backend name to use.

    Precedence: explicit ``override`` (e.g. CLI ``--provider``) > configured
    ``execution.isolation`` (when not ``auto``) > :data:`DEFAULT_BACKEND`.

    A malformed/unknown *configured* value fails safe to ``subprocess`` so a bad
    config can never silently disable isolation. An unknown *override* raises,
    because that is direct user input and should surface as an error.
    """
    if override is not None:
        name = override.strip().lower()
        if name not in BACKENDS:
            raise ValueError(
                f"Unknown isolation backend: {override!r} (valid: {', '.join(BACKENDS)})"
            )
        if name != "auto":
            return name
        # An explicit "auto" override defers to the configured/default backend.
    configured = (config.execution.isolation if config else "auto").strip().lower()
    if configured in ("", "auto"):
        return DEFAULT_BACKEND
    if configured not in _CONCRETE:
        return DEFAULT_BACKEND
    return configured


def build_isolation_provider(
    name: str,
    *,
    workspace_root: Optional[Path] = None,
) -> IsolationProvider:
    """Instantiate the :class:`IsolationProvider` for a concrete backend name.

    Providers are imported lazily so selecting ``subprocess``/``none`` never
    pulls in Docker or microVM dependencies.
    """
    key = name.strip().lower()
    if key == "none":
        from .none import NoneIsolationProvider

        return NoneIsolationProvider()
    if key == "subprocess":
        from .subprocess import SubprocessIsolationProvider

        return SubprocessIsolationProvider(workspace_root=workspace_root)
    if key == "docker":
        from .docker_provider import DockerIsolationProvider

        return DockerIsolationProvider()
    if key == "microvm":
        from .microvm import MicroVMIsolationProvider

        return MicroVMIsolationProvider()
    raise ValueError(f"Unknown isolation backend: {name!r} (valid: {', '.join(_CONCRETE)})")


def build_execution_provider(
    name: str,
    *,
    workspace_root: Path,
    env_allowlist: frozenset[str],
    max_output_bytes: int,
    read_write_workspace: bool = False,
) -> IsolationProvider:
    """Construct a policy-aware :class:`IsolationProvider` for command execution.

    Unlike :func:`build_isolation_provider` (which is for doctor/status probes),
    this threads the sandbox policy's env allowlist and output cap into the
    provider, so an executed command gets the same confinement regardless of
    which surface launched it (``arc sandbox run``, the agent shell tool, ...).

    ``docker`` maps to the subprocess-backed container provider used by the run
    command (the docker-CLI provider is reserved for availability probes).
    """
    key = name.strip().lower()
    if key == "none":
        from .none import NoneIsolationProvider

        return NoneIsolationProvider()
    if key == "microvm":
        from .microvm import MicroVMIsolationProvider

        return MicroVMIsolationProvider(
            workspace_root=workspace_root, max_output_bytes=max_output_bytes
        )
    if key in ("container", "docker"):
        from .docker_provider import SubprocessContainerProvider

        return SubprocessContainerProvider(
            workspace_root=workspace_root,
            max_output_bytes=max_output_bytes,
            read_write_workspace=read_write_workspace,
            safe_env_keys=env_allowlist,
        )
    from .subprocess import SubprocessIsolationProvider

    return SubprocessIsolationProvider(
        safe_env_keys=env_allowlist,
        workspace_root=workspace_root,
        max_output_bytes=max_output_bytes,
    )
