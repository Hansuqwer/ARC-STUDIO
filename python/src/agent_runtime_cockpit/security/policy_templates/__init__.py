"""ARC Policies — sandbox policy template library (R97).

A curated library of sandbox policy templates per use case (data science,
open-source, regulated-industry profiles) as YAML with tests and docs.
Compliance profiles are **aspirational targets, not certifications**.

All policies are deterministic. No LLM allow/deny decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from ..profiles import RunProfile
from ...gating import BackendMode

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class PolicyTemplate:
    id: str
    name: str
    description: str
    category: str
    profile: RunProfile
    tags: tuple[str, ...] = ()
    compliance_note: str = "Aspirational target, not a certification."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": list(self.tags),
            "compliance_note": self.compliance_note,
            "profile": {
                "id": self.profile.id,
                "name": self.profile.name,
                "allow_paid_calls": self.profile.allow_paid_calls,
                "allow_network": self.profile.allow_network,
                "allow_shell": self.profile.allow_shell,
                "allow_secrets": self.profile.allow_secrets,
                "env_allowlist": list(self.profile.env_allowlist),
                "backend": self.profile.backend.value,
            },
        }


def load_template(template_id: str) -> PolicyTemplate:
    """Load a policy template by ID from YAML files."""
    template_file = TEMPLATES_DIR / f"{template_id}.yaml"
    if not template_file.exists():
        raise FileNotFoundError(f"Policy template not found: {template_id}")

    with open(template_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    profile_data = data.get("profile", {})
    backend_str = profile_data.get("backend", "stub")
    try:
        backend = BackendMode(backend_str)
    except ValueError:
        backend = BackendMode.STUB

    profile = RunProfile(
        id=profile_data.get("id", template_id),
        name=profile_data.get("name", data.get("name", template_id)),
        allow_paid_calls=profile_data.get("allow_paid_calls", False),
        allow_network=profile_data.get("allow_network", False),
        allow_shell=profile_data.get("allow_shell", False),
        allow_secrets=profile_data.get("allow_secrets", False),
        env_allowlist=tuple(profile_data.get("env_allowlist", [])),
        backend=backend,
    )

    return PolicyTemplate(
        id=data.get("id", template_id),
        name=data.get("name", template_id),
        description=data.get("description", ""),
        category=data.get("category", "general"),
        profile=profile,
        tags=tuple(data.get("tags", [])),
        compliance_note=data.get("compliance_note", "Aspirational target, not a certification."),
    )


def list_templates(category: Optional[str] = None) -> list[PolicyTemplate]:
    """List all available policy templates, optionally filtered by category."""
    templates = []
    if not TEMPLATES_DIR.exists():
        return templates

    for template_file in sorted(TEMPLATES_DIR.glob("*.yaml")):
        try:
            template = load_template(template_file.stem)
            if category is None or template.category == category:
                templates.append(template)
        except Exception as e:
            log.debug("Failed to load template %s: %s", template_file.stem, e)
            continue

    return templates


def validate_template(template_id: str) -> dict[str, Any]:
    """Validate a policy template against the policy linter rules."""
    try:
        template = load_template(template_id)
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "template_id": template_id}

    profile = template.profile
    issues = []

    if profile.allow_shell and not profile.allow_secrets:
        issues.append(
            {
                "rule": "shell_without_secrets",
                "severity": "warning",
                "message": "Shell access enabled but secrets access disabled",
            }
        )

    if profile.allow_network and not profile.allow_paid_calls:
        issues.append(
            {
                "rule": "network_without_paid",
                "severity": "info",
                "message": "Network access enabled but paid calls disabled",
            }
        )

    return {
        "ok": True,
        "template_id": template_id,
        "name": template.name,
        "category": template.category,
        "issues": issues,
        "issue_count": len(issues),
    }


def apply_template(template_id: str, workspace: Path) -> dict[str, Any]:
    """Apply a policy template to a workspace by writing the profile config.

    This writes a .arc/profile.yaml file in the workspace.
    Does NOT execute any code or modify runtime state.
    """
    try:
        template = load_template(template_id)
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}

    arc_dir = workspace / ".arc"
    arc_dir.mkdir(parents=True, exist_ok=True)
    profile_file = arc_dir / "profile.yaml"

    profile_data = {
        "profile_id": template.profile.id,
        "template_id": template.id,
        "template_name": template.name,
        "allow_paid_calls": template.profile.allow_paid_calls,
        "allow_network": template.profile.allow_network,
        "allow_shell": template.profile.allow_shell,
        "allow_secrets": template.profile.allow_secrets,
        "env_allowlist": list(template.profile.env_allowlist),
        "backend": template.profile.backend.value,
        "compliance_note": template.compliance_note,
    }

    with open(profile_file, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False)

    return {
        "ok": True,
        "template_id": template_id,
        "profile_file": str(profile_file),
        "profile_id": template.profile.id,
    }


__all__ = [
    "PolicyTemplate",
    "load_template",
    "list_templates",
    "validate_template",
    "apply_template",
    "TEMPLATES_DIR",
]
