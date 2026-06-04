"""Eval-to-policy auto-apply loop — maps PolicyRecommendation.action → RunProfile mutations.

Append-only: writes versioned profiles to .arc/profiles/<id>.v<n>.yaml.
Never overwrites BUILTIN_PROFILES. Idempotent: applying twice yields same version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ..security.profiles import BUILTIN_PROFILES, RunProfile, resolve_profile

# ─── Action → Mutation Table ─────────────────────────────────────────────────

ACTION_MAP: dict[str, dict[str, Any]] = {
    "add_consensus_check=majority_voting": {"extra": {"consensus": "majority"}},
    "set_consensus=majority_plus_hitl": {"extra": {"consensus": "majority"}},
    "add_hitl_checkpoint=before_completion": {"extra": {"require_hitl": "True"}},
    "require_tool_approval=side_effect_tools": {
        "allow_shell": False,
        "extra": {"require_tool_approval": "True"},
    },
    "review_paid_call_gate=enabled": {
        "allow_paid_calls": False,
        "extra": {"review_required": "True"},
    },
}


class ProfileApplyResult(BaseModel):
    """Result of applying a recommendation to a profile."""

    new_path: str
    diff_summary: str
    correlation_id: str
    dry_run: bool = True
    profile_id: str = ""
    version: int = 0


def _profile_extra(profile: RunProfile) -> dict[str, str]:
    """Get extra dict from profile, defaulting to empty for v1 profiles."""
    return getattr(profile, "extra", {}) or {}


def _compute_fingerprint(profile_id: str, mutations: dict[str, Any]) -> str:
    """Deterministic hash for idempotency check."""
    raw = json.dumps({"id": profile_id, "mutations": mutations}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _next_version(profiles_dir: Path, profile_id: str) -> int:
    """Find next version number for a profile in the store."""
    if not profiles_dir.exists():
        return 1
    existing = sorted(profiles_dir.glob(f"{profile_id}.v*.yaml"))
    if not existing:
        return 1
    versions = []
    for p in existing:
        stem = p.stem  # e.g. "local-safe.v2"
        parts = stem.rsplit(".v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            versions.append(int(parts[1]))
    return max(versions, default=0) + 1


def _current_version_path(profiles_dir: Path, profile_id: str) -> Path | None:
    """Find the latest version file for a profile."""
    if not profiles_dir.exists():
        return None
    existing = sorted(profiles_dir.glob(f"{profile_id}.v*.yaml"))
    return existing[-1] if existing else None


def _profile_to_yaml_content(
    profile_id: str, profile: RunProfile, extra: dict[str, str], version: int
) -> str:
    """Serialize profile + extra to YAML-like content."""
    import yaml  # noqa: PLC0415

    data: dict[str, Any] = {
        "schema_version": 2,
        "version": version,
        "id": profile_id,
        "name": profile.name,
        "allow_paid_calls": profile.allow_paid_calls,
        "allow_network": profile.allow_network,
        "allow_shell": profile.allow_shell,
        "allow_secrets": profile.allow_secrets,
        "env_allowlist": list(profile.env_allowlist),
        "backend": profile.backend.value,
        "extra": extra,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=True)


def compute_mutations(actions: list[str]) -> dict[str, Any]:
    """Merge multiple action strings into a single mutation dict."""
    merged: dict[str, Any] = {}
    merged_extra: dict[str, str] = {}
    for action in actions:
        mapping = ACTION_MAP.get(action, {})
        for k, v in mapping.items():
            if k == "extra":
                merged_extra.update(v)
            else:
                merged[k] = v
    if merged_extra:
        merged["extra"] = merged_extra
    return merged


def apply_mutations(
    profile: RunProfile, mutations: dict[str, Any]
) -> tuple[RunProfile, dict[str, str]]:
    """Apply mutations to a profile, returning new profile and merged extra."""
    extra = dict(_profile_extra(profile))
    extra.update(mutations.pop("extra", {}))

    fields = asdict(profile)
    fields.update(mutations)
    # Rebuild with frozen dataclass
    new_profile = RunProfile(
        id=fields["id"],
        name=fields["name"],
        allow_paid_calls=fields["allow_paid_calls"],
        allow_network=fields["allow_network"],
        allow_shell=fields["allow_shell"],
        allow_secrets=fields["allow_secrets"],
        env_allowlist=tuple(fields.get("env_allowlist", ())),
        backend=fields["backend"],
    )
    return new_profile, extra


def _diff_summary(
    old_profile: RunProfile,
    new_profile: RunProfile,
    old_extra: dict[str, str],
    new_extra: dict[str, str],
) -> str:
    """Generate a human-readable diff summary."""
    changes: list[str] = []
    old_d = asdict(old_profile)
    new_d = asdict(new_profile)
    for key in ("allow_paid_calls", "allow_network", "allow_shell", "allow_secrets"):
        if old_d[key] != new_d[key]:
            changes.append(f"{key}: {old_d[key]} → {new_d[key]}")
    for k in sorted(set(list(old_extra.keys()) + list(new_extra.keys()))):
        ov = old_extra.get(k)
        nv = new_extra.get(k)
        if ov != nv:
            changes.append(f"extra.{k}: {ov!r} → {nv!r}")
    return "; ".join(changes) if changes else "no changes"


def apply_to_profile(
    profile_id: str,
    actions: list[str],
    *,
    workspace: Path | None = None,
    dry_run: bool = True,
) -> ProfileApplyResult:
    """Apply recommendation actions to a profile.

    Args:
        profile_id: Target profile ID.
        actions: List of action strings from PolicyRecommendation.action.
        workspace: Workspace root (defaults to cwd).
        dry_run: If True (default), compute result without writing.

    Returns:
        ProfileApplyResult with path, diff, and correlation_id.

    Raises:
        ValueError: If profile_id is a builtin that cannot be mutated.
    """
    if profile_id in BUILTIN_PROFILES:
        # Fork builtin into custom profile space
        base = BUILTIN_PROFILES[profile_id]
    else:
        base = resolve_profile(profile_id)

    ws = workspace or Path.cwd()
    profiles_dir = ws / ".arc" / "profiles"

    mutations = compute_mutations(actions)
    correlation_id = _compute_fingerprint(profile_id, mutations)

    old_extra = dict(_profile_extra(base))
    new_profile, new_extra = apply_mutations(base, dict(mutations))

    # Idempotency: check if latest version already has this content
    current = _current_version_path(profiles_dir, profile_id)
    if current is not None:
        try:
            import yaml  # noqa: PLC0415

            existing_data = yaml.safe_load(current.read_text()) or {}
            if (
                existing_data.get("extra") == new_extra
                and existing_data.get("allow_shell") == new_profile.allow_shell
                and existing_data.get("allow_paid_calls") == new_profile.allow_paid_calls
            ):
                # Already applied — idempotent
                parts = current.stem.rsplit(".v", 1)
                ver = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 1
                return ProfileApplyResult(
                    new_path=str(current),
                    diff_summary="no changes (already applied)",
                    correlation_id=correlation_id,
                    dry_run=dry_run,
                    profile_id=profile_id,
                    version=ver,
                )
        except Exception:
            pass

    version = _next_version(profiles_dir, profile_id)
    target_path = profiles_dir / f"{profile_id}.v{version}.yaml"
    diff = _diff_summary(base, new_profile, old_extra, new_extra)

    if not dry_run:
        profiles_dir.mkdir(parents=True, exist_ok=True)
        content = _profile_to_yaml_content(profile_id, new_profile, new_extra, version)
        target_path.write_text(content)

    return ProfileApplyResult(
        new_path=str(target_path),
        diff_summary=diff,
        correlation_id=correlation_id,
        dry_run=dry_run,
        profile_id=profile_id,
        version=version,
    )
