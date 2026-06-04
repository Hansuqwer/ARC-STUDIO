"""Generate Capability Cards from workspace AGENTS.md and SKILL.md files.

Design rules:
- card_from_agents_md produces entity_type=AGENTS_MD, audit_level=ARC_SHA256,
  requires_workspace_trust=True.
- card_from_skill produces entity_type=SKILL, read-only.
- Neither function executes anything.
"""

from __future__ import annotations

from pathlib import Path

from ..context.agents_md import AgentsMdEntry
from ..context.skill_md import SkillEntry
from .hashing import card_hash
from .models import (
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
    EntityType,
    RiskLevel,
    TrustLevel,
    TrustProfile,
)


def card_from_agents_md(
    entry: AgentsMdEntry,
    workspace: Path,
) -> CapabilityCard:
    """Build a CapabilityCard from an AGENTS.md entry."""
    rel_path = str(entry.path.relative_to(workspace))

    card = CapabilityCard(
        id=f"agents-md-{entry.sha256[:12]}",
        name=f"AGENTS.md ({rel_path})",
        entity_type=EntityType.AGENTS_MD,
        description=f"Workspace agent instructions at {rel_path}",
        capabilities=CapabilitySet(can_read=True),
        trust=TrustProfile(
            requires_workspace_trust=True,
            trust_level=TrustLevel.WORKSPACE,
        ),
        audit=AuditProfile(
            audit_required=True,
            audit_level=AuditLevel.ARC_SHA256,
        ),
        risk_level=RiskLevel.MEDIUM if entry.likely_llm_generated else RiskLevel.LOW,
        risk_signals=["likely_llm_generated"] if entry.likely_llm_generated else [],
        provenance=CapabilityProvenance(
            source_type="workspace",
            source_file=rel_path,
        ),
        metadata={
            "sha256": entry.sha256,
            "size_bytes": entry.size_bytes,
            "over_cap": entry.over_cap,
            "is_override": entry.is_override,
            "likely_llm_generated": entry.likely_llm_generated,
        },
    )
    card.card_hash = card_hash(card)
    return card


def card_from_skill(
    entry: SkillEntry,
    workspace: Path,
) -> CapabilityCard:
    """Build a CapabilityCard from a SKILL.md entry."""
    rel_path = str(entry.path.relative_to(workspace))

    card = CapabilityCard(
        id=f"skill-{entry.sha256[:12]}",
        name=f"SKILL: {entry.name}",
        entity_type=EntityType.SKILL,
        description=entry.description or f"Skill definition at {rel_path}",
        capabilities=CapabilitySet(can_read=True),
        trust=TrustProfile(
            requires_workspace_trust=True,
            trust_level=TrustLevel.WORKSPACE,
        ),
        audit=AuditProfile(
            audit_required=False,
            audit_level=AuditLevel.NONE,
        ),
        risk_level=RiskLevel.LOW,
        provenance=CapabilityProvenance(
            source_type="workspace",
            source_file=rel_path,
        ),
        metadata={
            "sha256": entry.sha256,
            "size_bytes": entry.size_bytes,
            "frontmatter": entry.frontmatter,
            "skill_name": entry.name,
        },
    )
    card.card_hash = card_hash(card)
    return card
