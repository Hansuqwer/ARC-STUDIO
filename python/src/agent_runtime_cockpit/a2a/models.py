"""A2A v1.2 spec models — AgentCard, skills, capabilities, signature."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

A2A_PROTOCOL_VERSION = "1.2"


class AgentCardSkill(BaseModel):
    """A2A skill descriptor."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class AgentCardCapability(BaseModel):
    """A2A agent capabilities."""

    model_config = ConfigDict(extra="ignore")

    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False


class AgentCardProvider(BaseModel):
    """A2A provider info."""

    model_config = ConfigDict(extra="ignore")

    name: str
    url: str = ""


class AgentCardSignature(BaseModel):
    """Cryptographic signature for an AgentCard."""

    model_config = ConfigDict(extra="ignore")

    algorithm: str  # e.g. "hmac_sha256", "ecdsa_p256"
    signature: str  # Base64-encoded
    signer_id: str = "arc-runtime"
    public_key_pem: Optional[str] = None


class AgentCard(BaseModel):
    """A2A v1.2 AgentCard — disk-only, no inbound HTTP."""

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str = ""
    version: str = "1.0.0"
    protocolVersion: str = A2A_PROTOCOL_VERSION
    url: str = ""  # loopback URL or empty
    provider: AgentCardProvider = Field(
        default_factory=lambda: AgentCardProvider(name="arc-studio")
    )
    capabilities: AgentCardCapability = Field(default_factory=AgentCardCapability)
    skills: list[AgentCardSkill] = Field(default_factory=list)
    signature: Optional[AgentCardSignature] = None
