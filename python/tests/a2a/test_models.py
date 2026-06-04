"""Tests for A2A models."""

from agent_runtime_cockpit.a2a.models import (
    A2A_PROTOCOL_VERSION,
    AgentCard,
    AgentCardCapability,
    AgentCardProvider,
    AgentCardSignature,
    AgentCardSkill,
)


def test_agent_card_minimal():
    card = AgentCard(name="test-agent")
    assert card.name == "test-agent"
    assert card.protocolVersion == A2A_PROTOCOL_VERSION
    assert card.version == "1.0.0"
    assert card.skills == []
    assert card.signature is None


def test_agent_card_full():
    card = AgentCard(
        name="full",
        description="A full agent",
        version="2.0.0",
        url="http://127.0.0.1:9000/",
        provider=AgentCardProvider(name="acme", url="https://acme.test"),
        capabilities=AgentCardCapability(streaming=True),
        skills=[AgentCardSkill(id="s1", name="skill1", description="does stuff")],
        signature=AgentCardSignature(algorithm="hmac_sha256", signature="abc123"),
    )
    assert card.capabilities.streaming is True
    assert len(card.skills) == 1
    assert card.signature.algorithm == "hmac_sha256"


def test_agent_card_roundtrip_json():
    card = AgentCard(name="rt", version="0.1.0")
    data = card.model_dump(mode="json")
    restored = AgentCard.model_validate(data)
    assert restored.name == "rt"
    assert restored.protocolVersion == "1.2"


def test_extra_fields_ignored():
    data = {"name": "x", "unknownField": True, "protocolVersion": "1.2"}
    card = AgentCard.model_validate(data)
    assert card.name == "x"


def test_skill_model():
    s = AgentCardSkill(id="s1", name="Search", tags=["web"], examples=["find X"])
    assert s.id == "s1"
    assert s.tags == ["web"]
