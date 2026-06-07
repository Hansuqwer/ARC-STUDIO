"""Run profiles and tool firewall — permission model for ARC runs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from ..gating import BackendMode, GatingError, require_dual_gate


PROFILE_SCHEMA_VERSION = 2


class ProfileNotFound(KeyError):
    """Raised when a strict profile lookup cannot resolve an id."""


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
    extra: dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.extra is None:
            object.__setattr__(self, "extra", {})


# Built-in profiles
BUILTIN_PROFILES: dict[str, RunProfile] = {
    "stub": RunProfile(
        id="stub",
        name="Stub (Safe)",
        backend=BackendMode.STUB,
    ),
    "local-safe": RunProfile(
        id="local-safe",
        name="Local Safe",
        backend=BackendMode.STUB,
    ),
    "local-paid": RunProfile(
        id="local-paid",
        name="Local Paid",
        allow_paid_calls=True,
        allow_network=True,
        backend=BackendMode.LOCAL,
    ),
    "gateway": RunProfile(
        id="gateway",
        name="Gateway (Full Access)",
        allow_paid_calls=True,
        allow_network=True,
        allow_shell=True,
        allow_secrets=True,
        backend=BackendMode.GATEWAY,
    ),
}


def resolve_profile(profile_id: str) -> RunProfile:
    """Resolve a profile ID to a RunProfile. Falls back to stub."""
    if profile_id in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[profile_id]
    custom = load_custom_profiles()
    if profile_id in custom:
        return custom[profile_id]
    return BUILTIN_PROFILES["stub"]


def resolve_profile_strict(profile_id: str) -> RunProfile:
    """Resolve a profile ID without fallback for execution/preflight paths."""
    if profile_id in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[profile_id]
    custom = load_custom_profiles()
    if profile_id in custom:
        return custom[profile_id]
    raise ProfileNotFound(profile_id)


def profile_store_path() -> Path:
    """Return external profile store path; tests may override with ARC_PROFILE_CONFIG."""
    override = os.environ.get("ARC_PROFILE_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arc" / "profiles.json"


def load_custom_profiles(path: Path | None = None) -> dict[str, RunProfile]:
    store_path = path or profile_store_path()
    if not store_path.exists():
        return {}
    raw = json.loads(store_path.read_text())
    # Schema-version guard. v1 → v2 is additive (new optional fields default-fill
    # below), so older stores load unchanged. An unknown *future* version is
    # rejected fail-closed rather than silently mis-read.
    version = int(raw.get("version", 1))
    if version > PROFILE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported profile schema version {version}; this build supports up to "
            f"{PROFILE_SCHEMA_VERSION}. Upgrade ARC to read this profile store."
        )
    profiles: dict[str, RunProfile] = {}
    for item in raw.get("profiles", []):
        backend = BackendMode(item.get("backend", BackendMode.STUB.value))
        profiles[item["id"]] = RunProfile(
            id=item["id"],
            name=item.get("name") or item["id"],
            allow_paid_calls=bool(item.get("allow_paid_calls", False)),
            allow_network=bool(item.get("allow_network", False)),
            allow_shell=bool(item.get("allow_shell", False)),
            allow_secrets=bool(item.get("allow_secrets", False)),
            env_allowlist=tuple(item.get("env_allowlist", ())),
            backend=backend,
            extra=dict(item.get("extra", {})),
        )
    return profiles


def list_profiles() -> dict[str, RunProfile]:
    return {**BUILTIN_PROFILES, **load_custom_profiles()}


def save_custom_profile(profile: RunProfile, path: Path | None = None) -> Path:
    if profile.id in BUILTIN_PROFILES:
        raise ValueError(f"Profile '{profile.id}' is built in and cannot be overwritten")
    store_path = path or profile_store_path()
    profiles = load_custom_profiles(store_path)
    profiles[profile.id] = profile
    payload = {
        "version": PROFILE_SCHEMA_VERSION,
        "profiles": [_profile_to_json(p) for p in profiles.values()],
    }
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return store_path


def _profile_to_json(profile: RunProfile) -> dict[str, object]:
    payload = asdict(profile)
    payload["backend"] = profile.backend.value
    payload["env_allowlist"] = list(profile.env_allowlist)
    payload["extra"] = dict(profile.extra) if profile.extra else {}
    return payload


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
        if allow_costs and not profile.allow_paid_calls:
            raise GatingError(
                f"Profile '{profile.id}' does not allow paid calls but costs are enabled"
            )
        return
