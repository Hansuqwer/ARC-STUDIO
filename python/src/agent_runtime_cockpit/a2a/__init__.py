"""A2A Local AgentCard Generator + Loopback Client.

Provides A2A v1.2 spec-compliant agent card generation, disk-based storage,
per-card approval, and a loopback-only outbound client.

NO inbound HTTP server — cards are written to .arc/a2a/agent-card.json only.
"""

from .models import (
    AgentCard,
    AgentCardCapability,
    AgentCardProvider,
    AgentCardSignature,
    AgentCardSkill,
)

__all__ = [
    "AgentCard",
    "AgentCardCapability",
    "AgentCardProvider",
    "AgentCardSignature",
    "AgentCardSkill",
]
