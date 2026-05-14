"""Run profiles and tool firewall — permission model for ARC runs."""
from __future__ import annotations

from dataclasses import dataclass

from ..gating import BackendMode, GatingError, require_dual_gate


@dataclass(frozen=True)
class RunProfile:
    id: str
    name: str
    allow_paid_calls: bool = False
    allow_network: bool = False
    allow_shell: bool = False
    allow_secrets: bool = False
    env_allowlist: tuple[str, ...] = ()
    backend: BackendMode = BackendMode.STUB


# Built-in profiles
BUILTIN_PROFILES: dict[str, RunProfile] = {
    "stub": RunProfile(
        id="stub", name="Stub (Safe)",
        backend=BackendMode.STUB,
    ),
    "local-safe": RunProfile(
        id="local-safe", name="Local Safe",
        allow_network=True,
        backend=BackendMode.STUB,
    ),
    "local-paid": RunProfile(
        id="local-paid", name="Local Paid",
        allow_paid_calls=True, allow_network=True,
        backend=BackendMode.LOCAL,
    ),
    "gateway": RunProfile(
        id="gateway", name="Gateway (Full Access)",
        allow_paid_calls=True, allow_network=True, allow_shell=True, allow_secrets=True,
        backend=BackendMode.GATEWAY,
    ),
}


def resolve_profile(profile_id: str) -> RunProfile:
    """Resolve a profile ID to a RunProfile. Falls back to stub."""
    if profile_id in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[profile_id]
    return BUILTIN_PROFILES["stub"]


def enforce_profile(profile: RunProfile, runtime: str) -> None:
    """Enforce profile constraints for a given runtime.

    Raises GatingError if the profile doesn't allow the requested backend/features.
    """
    backend, allow_costs = require_dual_gate(runtime)

    if profile.backend is BackendMode.STUB:
        if allow_costs:
            raise GatingError(
                f"Profile '{profile.id}' uses stub backend but ALLOW_COSTS is set. "
                f"Use 'local-paid' profile for paid calls."
            )
        return

    if profile.backend is BackendMode.LOCAL:
        if not profile.allow_network:
            raise GatingError(
                f"Profile '{profile.id}' does not allow network access "
                f"but backend is {profile.backend.value}"
            )
        if allow_costs and not profile.allow_paid_calls:
            raise GatingError(
                f"Profile '{profile.id}' does not allow paid calls "
                f"but costs are enabled"
            )
        return
