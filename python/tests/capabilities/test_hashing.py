"""Tests for CapabilityCard hashing."""

from __future__ import annotations


from agent_runtime_cockpit.capabilities import (
    card_hash,
    canonical_json,
    verify_hash,
    CapabilityCard,
    CapabilitySet,
    EntityType,
    CARD_SCHEMA_VERSION,
)


class TestCardHash:
    """Tests for card_hash function."""

    def test_same_card_produces_same_hash(self, minimal_card: CapabilityCard):
        """Identical cards produce identical hashes."""
        hash1 = card_hash(minimal_card)
        hash2 = card_hash(minimal_card)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_different_cards_produce_different_hashes(self, minimal_card: CapabilityCard):
        """Different cards produce different hashes."""
        card2 = CapabilityCard(
            id="different-card",
            name="Different Card",
            entity_type=EntityType.IR_GRAPH,
        )
        hash1 = card_hash(minimal_card)
        hash2 = card_hash(card2)
        assert hash1 != hash2

    def test_capability_change_changes_hash(self, minimal_card: CapabilityCard):
        """Changing capabilities changes the hash."""
        hash1 = card_hash(minimal_card)

        # Create a new card with different capabilities
        card2 = CapabilityCard(
            id=minimal_card.id,
            name=minimal_card.name,
            entity_type=minimal_card.entity_type,
            capabilities=CapabilitySet(can_write=True),
        )
        hash2 = card_hash(card2)

        assert hash1 != hash2

    def test_id_change_changes_hash(self, minimal_card: CapabilityCard):
        """Changing the ID changes the hash."""
        hash1 = card_hash(minimal_card)

        card2 = CapabilityCard(
            id="changed-id",
            name=minimal_card.name,
            entity_type=minimal_card.entity_type,
        )
        hash2 = card_hash(card2)

        assert hash1 != hash2

    def test_risk_change_changes_hash(self, minimal_card: CapabilityCard):
        """Changing risk level changes the hash."""
        from agent_runtime_cockpit.capabilities import RiskLevel

        hash1 = card_hash(minimal_card)

        card2 = CapabilityCard(
            id=minimal_card.id,
            name=minimal_card.name,
            entity_type=minimal_card.entity_type,
            risk_level=RiskLevel.HIGH,
        )
        hash2 = card_hash(card2)

        assert hash1 != hash2

    def test_dict_input_accepted(self):
        """card_hash accepts plain dict input."""
        card_dict = {
            "id": "test-dict",
            "name": "Test",
            "schema_version": CARD_SCHEMA_VERSION,
            "entity_type": "ir_node",
            "capabilities": {"can_read": True},
        }
        hash_result = card_hash(card_dict)
        assert len(hash_result) == 64


class TestCanonicalJson:
    """Tests for canonical_json function."""

    def test_sorted_keys(self):
        """Keys are sorted in canonical JSON."""
        data = {"z": 1, "a": 2, "m": 3}
        canonical = canonical_json(data)
        # Check that keys appear in sorted order
        z_pos = canonical.index('"z"')
        a_pos = canonical.index('"a"')
        m_pos = canonical.index('"m"')
        assert a_pos < m_pos < z_pos

    def test_strips_volatile_fields(self):
        """Volatile fields are stripped from canonical JSON."""
        data = {
            "id": "test",
            "name": "Test",
            "card_hash": "should_be_removed",
            "created_at": "2024-01-01T00:00:00Z",
            "compiled_at": "2024-01-01T00:00:00Z",
        }
        canonical = canonical_json(data)
        assert "card_hash" not in canonical
        assert "created_at" not in canonical
        assert "compiled_at" not in canonical
        assert '"id"' in canonical
        assert '"name"' in canonical

    def test_redacts_sensitive_fields(self):
        """Sensitive fields are redacted in canonical JSON."""
        data = {
            "id": "test",
            "api_key": "sk-abc123",
            "secret_token": "ghp_xyz789",
        }
        canonical = canonical_json(data)
        assert "sk-" not in canonical
        assert "ghp_" not in canonical
        assert "[REDACTED]" in canonical

    def test_deterministic_list_ordering(self):
        """Lists maintain deterministic ordering."""
        data = {
            "items": [{"z": 1}, {"a": 2}, {"m": 3}],
        }
        canonical1 = canonical_json(data)
        canonical2 = canonical_json(data)
        assert canonical1 == canonical2


class TestVerifyHash:
    """Tests for verify_hash function."""

    def test_valid_hash_passes(self, minimal_card: CapabilityCard):
        """Valid hash verification passes."""
        hash_value = card_hash(minimal_card)
        assert verify_hash(minimal_card, hash_value) is True

    def test_invalid_hash_fails(self, minimal_card: CapabilityCard):
        """Invalid hash verification fails."""
        wrong_hash = "0" * 64
        assert verify_hash(minimal_card, wrong_hash) is False

    def test_dict_input_accepted(self):
        """verify_hash accepts dict input."""
        card_dict = {
            "id": "test",
            "name": "Test",
            "schema_version": CARD_SCHEMA_VERSION,
            "entity_type": "ir_node",
        }
        hash_value = card_hash(card_dict)
        assert verify_hash(card_dict, hash_value) is True


class TestHashStability:
    """Tests for hash stability across operations."""

    def test_hash_not_affected_by_card_hash_field(self, minimal_card: CapabilityCard):
        """Setting card_hash field doesn't affect computed hash."""
        hash1 = card_hash(minimal_card)

        # Set the card_hash field
        minimal_card.card_hash = hash1
        hash2 = card_hash(minimal_card)

        assert hash1 == hash2

    def test_multiple_cards_with_same_content_produce_same_hash(self):
        """Cards with same content produce identical hashes."""
        card1 = CapabilityCard(
            id="same-id",
            name="Same Name",
            entity_type=EntityType.WORKFLOW,
        )
        card2 = CapabilityCard(
            id="same-id",
            name="Same Name",
            entity_type=EntityType.WORKFLOW,
        )
        assert card_hash(card1) == card_hash(card2)

    def test_nested_data_affects_hash(self):
        """Changes in nested data affect the hash."""
        card1 = CapabilityCard(
            id="test",
            name="Test",
            metadata={"nested": {"value": 1}},
        )
        card2 = CapabilityCard(
            id="test",
            name="Test",
            metadata={"nested": {"value": 2}},
        )
        assert card_hash(card1) != card_hash(card2)
