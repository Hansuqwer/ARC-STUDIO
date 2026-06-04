"""A2A AgentCard generator — writes .arc/a2a/agent-card.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from .models import (
    AgentCard,
    AgentCardCapability,
    AgentCardProvider,
    AgentCardSignature,
    AgentCardSkill,
)


def _canonicalize(card: AgentCard) -> bytes:
    """Deterministic JSON for signing (excludes signature field)."""
    d = card.model_dump(mode="json", exclude={"signature"})
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign_card_hmac(
    card: AgentCard, secret_key: str, signer_id: str = "arc-runtime"
) -> AgentCardSignature:
    import base64
    import hmac as _hmac

    data = _canonicalize(card)
    sig = _hmac.new(secret_key.encode(), data, hashlib.sha256).digest()
    return AgentCardSignature(
        algorithm="hmac_sha256",
        signature=base64.b64encode(sig).decode("ascii"),
        signer_id=signer_id,
    )


def generate_agent_card(
    *,
    name: str = "arc-studio",
    description: str = "ARC Studio local agent",
    version: str = "1.0.0",
    url: str = "",
    provider_name: str = "arc-studio",
    provider_url: str = "",
    capabilities: Optional[AgentCardCapability] = None,
    skills: Optional[list[AgentCardSkill]] = None,
    secret_key: Optional[str] = None,
    signer_id: str = "arc-runtime",
) -> AgentCard:
    """Generate a deterministic AgentCard. Optionally sign with HMAC."""
    card = AgentCard(
        name=name,
        description=description,
        version=version,
        url=url,
        provider=AgentCardProvider(name=provider_name, url=provider_url),
        capabilities=capabilities or AgentCardCapability(),
        skills=skills or [],
    )
    if secret_key:
        card.signature = _sign_card_hmac(card, secret_key, signer_id)
    return card


def write_agent_card(card: AgentCard, arc_dir: Optional[Path] = None) -> Path:
    """Write AgentCard to .arc/a2a/agent-card.json. Returns path written."""
    base = arc_dir or Path.home() / ".arc"
    out_dir = base / "a2a"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "agent-card.json"
    out_path.write_text(json.dumps(card.model_dump(mode="json"), indent=2, sort_keys=True) + "\n")
    return out_path


def load_agent_card(arc_dir: Optional[Path] = None) -> Optional[AgentCard]:
    """Load AgentCard from disk, or None if not present."""
    base = arc_dir or Path.home() / ".arc"
    path = base / "a2a" / "agent-card.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return AgentCard.model_validate(data)


def verify_agent_card(card: AgentCard, secret_key: str) -> bool:
    """Verify HMAC signature on an AgentCard."""
    if not card.signature or card.signature.algorithm != "hmac_sha256":
        return False
    import base64
    import hmac as _hmac

    data = _canonicalize(card)
    expected = _hmac.new(secret_key.encode(), data, hashlib.sha256).digest()
    expected_b64 = base64.b64encode(expected).decode("ascii")
    return _hmac.compare_digest(expected_b64, card.signature.signature)
