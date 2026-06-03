"""Tests for Capability Card signing and verification."""

from __future__ import annotations

import json

import pytest

from agent_runtime_cockpit.capabilities import (
    CapabilityCard,
    CapabilitySet,
    EntityType,
    sign_card,
    verify_card,
    sign_card_file,
    verify_card_file,
    generate_secret_key,
    generate_ecdsa_keypair,
    SignatureAlgorithm,
    CardSignature,
    SignedCapabilityCard,
)


class TestSignCard:
    """Tests for sign_card function."""

    def test_sign_card_hmac(self):
        """Signing with HMAC-SHA256 works correctly."""
        card = CapabilityCard(
            id="test-card-1",
            name="Test Card",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read=True),
        )
        secret_key = "my-secret-key-123"

        signed = sign_card(card, signer_id="test-signer", secret_key=secret_key)

        assert signed.signature.algorithm == SignatureAlgorithm.HMAC_SHA256
        assert signed.signature.signer_id == "test-signer"
        assert signed.signature.signature is not None
        assert len(signed.signature.signature) > 0

    def test_verify_hmac_signature(self):
        """HMAC signature verification works."""
        card = CapabilityCard(
            id="test-card-2",
            name="Test Card 2",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_write=True),
        )
        secret_key = "another-secret-key"

        signed = sign_card(card, secret_key=secret_key)
        is_valid = verify_card(signed, secret_key=secret_key)

        assert is_valid is True

    def test_verify_wrong_key_fails(self):
        """Verification with wrong key fails."""
        card = CapabilityCard(
            id="test-card-3",
            name="Test Card 3",
            entity_type=EntityType.IR_NODE,
        )
        secret_key = "correct-key"
        wrong_key = "wrong-key"

        signed = sign_card(card, secret_key=secret_key)
        is_valid = verify_card(signed, secret_key=wrong_key)

        assert is_valid is False

    def test_tampered_card_fails_verification(self):
        """Tampering with card content invalidates signature."""
        card = CapabilityCard(
            id="test-card-4",
            name="Original Name",
            entity_type=EntityType.IR_NODE,
        )
        secret_key = "secret-key"

        signed = sign_card(card, secret_key=secret_key)

        # Tamper with the card
        signed.card.name = "Tampered Name"

        is_valid = verify_card(signed, secret_key=secret_key)
        assert is_valid is False

    def test_sign_card_ECDSA(self):
        """Signing with ECDSA-P256 works when cryptography is available."""
        pytest.importorskip("cryptography")

        card = CapabilityCard(
            id="test-card-ecdsa",
            name="ECDSA Test Card",
            entity_type=EntityType.IR_NODE,
        )
        private_key, public_key = generate_ecdsa_keypair()

        signed = sign_card(card, signer_id="ecdsa-signer", private_key_pem=private_key)

        assert signed.signature.algorithm == SignatureAlgorithm.ECDSA_P256
        assert signed.signature.public_key_pem is not None

    def test_verify_ECDSA_signature(self):
        """ECDSA signature verification works."""
        pytest.importorskip("cryptography")

        card = CapabilityCard(
            id="test-card-ecdsa-verify",
            name="ECDSA Verify Test",
            entity_type=EntityType.IR_NODE,
        )
        private_key, public_key = generate_ecdsa_keypair()

        signed = sign_card(card, private_key_pem=private_key)
        is_valid = verify_card(signed, public_key_pem=public_key)

        assert is_valid is True

    def test_ECDSA_signature_uses_embedded_key(self):
        """ECDSA verification uses embedded public key by default."""
        pytest.importorskip("cryptography")

        card = CapabilityCard(
            id="test-card-embedded-key",
            name="Embedded Key Test",
            entity_type=EntityType.IR_NODE,
        )
        private_key, _ = generate_ecdsa_keypair()

        signed = sign_card(card, private_key_pem=private_key)

        # Verify without providing public_key_pem (should use embedded)
        is_valid = verify_card(signed)
        assert is_valid is True

    def test_wrong_private_key_fails_verification(self):
        """ECDSA verification with wrong key fails."""
        pytest.importorskip("cryptography")

        card = CapabilityCard(
            id="test-card-wrong-key",
            name="Wrong Key Test",
            entity_type=EntityType.IR_NODE,
        )
        private_key1, _ = generate_ecdsa_keypair()
        _, public_key2 = generate_ecdsa_keypair()

        signed = sign_card(card, private_key_pem=private_key1)
        is_valid = verify_card(signed, public_key_pem=public_key2)

        assert is_valid is False

    def test_sign_requires_exactly_one_key(self):
        """sign_card requires exactly one of secret_key or private_key_pem."""
        card = CapabilityCard(
            id="test-card-no-key",
            name="No Key Test",
            entity_type=EntityType.IR_NODE,
        )

        with pytest.raises(ValueError, match="Provide exactly one"):
            sign_card(card)

        with pytest.raises(ValueError, match="Provide exactly one"):
            sign_card(card, secret_key="key", private_key_pem="key")

    def test_verify_requires_key_for_hmac(self):
        """verify_card requires secret_key for HMAC verification."""
        card = CapabilityCard(
            id="test-card-verify-key",
            name="Verify Key Test",
            entity_type=EntityType.IR_NODE,
        )
        signed = sign_card(card, secret_key="secret")

        with pytest.raises(ValueError, match="secret_key required"):
            verify_card(signed)

    def test_signature_includes_timestamp(self):
        """Signature includes signed_at timestamp."""
        card = CapabilityCard(
            id="test-card-timestamp",
            name="Timestamp Test",
            entity_type=EntityType.IR_NODE,
        )
        signed = sign_card(card, secret_key="secret")

        assert signed.signature.signed_at is not None
        assert "T" in signed.signature.signed_at  # ISO format


class TestSignCardFile:
    """Tests for file-based signing."""

    def test_sign_and_verify_file(self, tmp_path):
        """Signing and verifying a file works."""
        # Create a card file
        card = CapabilityCard(
            id="test-file-card",
            name="File Test Card",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read=True),
        )
        card_path = tmp_path / "card.json"
        with open(card_path, "w") as f:
            f.write(card.model_dump_json())

        secret_key = "file-secret-key"
        signed_path = sign_card_file(card_path, signer_id="file-signer", secret_key=secret_key)

        # Verify the signed file
        is_valid = verify_card_file(signed_path, secret_key=secret_key)
        assert is_valid is True

    def test_signed_file_format(self, tmp_path):
        """Signed file contains card and signature sections."""
        card = CapabilityCard(
            id="test-format-card",
            name="Format Test",
            entity_type=EntityType.IR_NODE,
        )
        card_path = tmp_path / "card.json"
        with open(card_path, "w") as f:
            f.write(card.model_dump_json())

        signed_path = sign_card_file(card_path, secret_key="secret")

        with open(signed_path) as f:
            data = json.load(f)

        assert "card" in data
        assert "signature" in data
        assert data["signature"]["algorithm"] == "hmac_sha256"

    def test_verify_wrong_key_fails_on_file(self, tmp_path):
        """File verification with wrong key fails."""
        card = CapabilityCard(
            id="test-wrong-key-file",
            name="Wrong Key File Test",
            entity_type=EntityType.IR_NODE,
        )
        card_path = tmp_path / "card.json"
        with open(card_path, "w") as f:
            f.write(card.model_dump_json())

        signed_path = sign_card_file(card_path, secret_key="correct-key")

        is_valid = verify_card_file(signed_path, secret_key="wrong-key")
        assert is_valid is False


class TestGenerateKeys:
    """Tests for key generation functions."""

    def test_generate_secret_key_length(self):
        """Generated secret key has expected length."""
        key = generate_secret_key()
        assert len(key) == 64  # 32 bytes as hex = 64 chars

    def test_generate_secret_key_uniqueness(self):
        """Generated keys are unique."""
        keys = [generate_secret_key() for _ in range(10)]
        assert len(set(keys)) == 10

    def test_generate_ecdsa_keypair(self):
        """ECDSA keypair generation works."""
        pytest.importorskip("cryptography")

        private_key, public_key = generate_ecdsa_keypair()

        assert "-----BEGIN PRIVATE KEY-----" in private_key
        assert "-----BEGIN PUBLIC KEY-----" in public_key

    def test_ecdsa_keypair_roundtrip(self):
        """Signing with generated keypair and verifying works."""
        pytest.importorskip("cryptography")

        private_key, public_key = generate_ecdsa_keypair()

        card = CapabilityCard(
            id="test-roundtrip",
            name="Roundtrip Test",
            entity_type=EntityType.IR_NODE,
        )

        signed = sign_card(card, private_key_pem=private_key)
        is_valid = verify_card(signed, public_key_pem=public_key)

        assert is_valid is True


class TestSignatureModels:
    """Tests for signature model structures."""

    def test_card_signature_model(self):
        """CardSignature model works correctly."""
        sig = CardSignature(
            algorithm=SignatureAlgorithm.HMAC_SHA256,
            signature="base64signature",
            signer_id="test",
        )

        assert sig.algorithm == SignatureAlgorithm.HMAC_SHA256
        assert sig.signature == "base64signature"
        assert sig.signer_id == "test"

    def test_signed_capability_card_model(self):
        """SignedCapabilityCard model works correctly."""
        card = CapabilityCard(
            id="test-signed",
            name="Signed Test",
            entity_type=EntityType.IR_NODE,
        )
        sig = CardSignature(
            algorithm=SignatureAlgorithm.HMAC_SHA256,
            signature="sig",
        )

        signed = SignedCapabilityCard(card=card, signature=sig)

        assert signed.card.id == "test-signed"
        assert signed.signature.algorithm == SignatureAlgorithm.HMAC_SHA256

    def test_signature_serialization(self):
        """Signatures serialize to JSON correctly."""
        sig = CardSignature(
            algorithm=SignatureAlgorithm.ECDSA_P256,
            signature="sigdata",
            signer_id="signer",
            public_key_pem="-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----",
        )

        json_str = sig.model_dump_json()
        restored = CardSignature.model_validate_json(json_str)

        assert restored.algorithm == SignatureAlgorithm.ECDSA_P256
        assert restored.public_key_pem == sig.public_key_pem


class TestCanonicalization:
    """Tests for signing canonicalization (indirectly via sign/verify)."""

    def test_identical_cards_produce_different_signatures(self):
        """Different cards produce different signatures."""
        card1 = CapabilityCard(
            id="card-1",
            name="Card 1",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read=True),
        )
        card2 = CapabilityCard(
            id="card-2",
            name="Card 2",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read=True),
        )
        secret = "shared-secret"

        signed1 = sign_card(card1, secret_key=secret)
        signed2 = sign_card(card2, secret_key=secret)

        assert signed1.signature.signature != signed2.signature.signature

    def test_same_card_same_secret_deterministic(self):
        """Same card with same key produces same signature."""
        card = CapabilityCard(
            id="deterministic-card",
            name="Deterministic Test",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(can_read=True),
        )
        secret = "deterministic-secret"

        signed1 = sign_card(card, secret_key=secret)
        signed2 = sign_card(card, secret_key=secret)

        # Signatures should be identical for same input
        assert signed1.signature.signature == signed2.signature.signature

    def test_different_secrets_produce_different_signatures(self):
        """Different secrets produce different signatures."""
        card = CapabilityCard(
            id="diff-secrets-card",
            name="Different Secrets Test",
            entity_type=EntityType.IR_NODE,
        )

        signed1 = sign_card(card, secret_key="secret-1")
        signed2 = sign_card(card, secret_key="secret-2")

        assert signed1.signature.signature != signed2.signature.signature

    def test_complex_card_signing(self):
        """Complex cards with all fields sign correctly."""
        from agent_runtime_cockpit.capabilities import RiskLevel

        card = CapabilityCard(
            id="complex-card",
            name="Complex Test Card",
            entity_type=EntityType.IR_NODE,
            capabilities=CapabilitySet(
                can_read=True,
                can_write=True,
                can_network=True,
            ),
            risk_level=RiskLevel.MEDIUM,
            metadata={"key": "value", "nested": {"data": 123}},
        )
        secret = "complex-secret"

        signed = sign_card(card, secret_key=secret)
        is_valid = verify_card(signed, secret_key=secret)

        assert is_valid is True
