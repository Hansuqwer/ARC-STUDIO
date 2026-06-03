"""Cryptographic signing and verification for Capability Cards.

Provides HMAC-SHA256 and ECDSA-P256 signature schemes for signing Capability Cards.
Signed cards can be verified to ensure they haven't been tampered with.

Usage:
    from agent_runtime_cockpit.capabilities.signing import sign_card, verify_card
    from agent_runtime_cockpit.capabilities import CapabilityCard

    # Sign a card with HMAC
    signed_card = sign_card(card, secret_key="my-secret-key")

    # Verify a signed card
    is_valid = verify_card(signed_card, secret_key="my-secret-key")

    # Sign with ECDSA (requires cryptography package)
    signed_card = sign_card(card, private_key_pem=private_key_pem)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .models import CapabilityCard


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""

    HMAC_SHA256 = "hmac_sha256"
    ECDSA_P256 = "ecdsa_p256"


class CardSignature(BaseModel):
    """A cryptographic signature for a Capability Card."""

    model_config = {"extra": "ignore"}

    algorithm: SignatureAlgorithm
    signature: str  # Base64-encoded signature
    signer_id: str = "unknown"  # Identity of the signer
    signed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # For ECDSA
    public_key_pem: Optional[str] = None
    # For HMAC - we store only the hash of the secret for verification
    secret_hash: Optional[str] = None


class SignedCapabilityCard(BaseModel):
    """A Capability Card with its signature attached."""

    card: CapabilityCard
    signature: CardSignature


def _canonicalize_for_signing(card: CapabilityCard) -> bytes:
    """Create a canonical JSON representation of the card for signing.

    This excludes the signature-related fields to ensure signing is deterministic.
    The card_hash field is included as it represents the card's content hash.
    """
    # Create a copy without signature-related fields
    signing_data = {
        "schema_version": card.schema_version,
        "id": card.id,
        "name": card.name,
        "entity_type": card.entity_type.value,
        "version": card.version,
        "description": card.description,
        "capabilities": card.capabilities.model_dump(),
        "permissions": [p.model_dump() for p in card.permissions],
        "data_access": card.data_access.model_dump() if card.data_access else None,
        "side_effects": [s.model_dump() for s in card.side_effects],
        "mcp": card.mcp.model_dump() if card.mcp else None,
        "cost": card.cost.model_dump() if card.cost else None,
        "trust": card.trust.model_dump(),
        "audit": card.audit.model_dump(),
        "replay": card.replay.model_dump(),
        "risk_level": card.risk_level.value,
        "risk_signals": card.risk_signals,
        "risk_rationale": card.risk_rationale,
        "provenance": card.provenance.model_dump(),
        "metadata": card.metadata,
        "opaque": card.opaque,
        "requires_review": card.requires_review,
        "card_hash": card.card_hash,
    }

    return json.dumps(signing_data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hmac_sha256_sign(data: bytes, secret_key: str) -> str:
    """Sign data using HMAC-SHA256."""
    key = secret_key.encode("utf-8")
    signature = hmac.new(key, data, hashlib.sha256).digest()
    import base64

    return base64.b64encode(signature).decode("ascii")


def _hmac_sha256_verify(data: bytes, signature_b64: str, secret_key: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = _hmac_sha256_sign(data, secret_key)
    return hmac.compare_digest(expected, signature_b64)


def _ecdsa_p256_sign(data: bytes, private_key_pem: str) -> tuple[str, str]:
    """Sign data using ECDSA-P256.

    Returns (signature_base64, public_key_pem).
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
    except ImportError as e:
        raise ImportError(
            "cryptography package required for ECDSA signing. "
            "Install with: pip install cryptography"
        ) from e

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )

    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Private key must be an ECDSA P-256 key")

    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))
    import base64

    signature_b64 = base64.b64encode(signature).decode("ascii")

    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    return signature_b64, public_key_pem


def _ecdsa_p256_verify(data: bytes, signature_b64: str, public_key_pem: str) -> bool:
    """Verify ECDSA-P256 signature."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
    except ImportError as e:
        raise ImportError("cryptography package required for ECDSA verification") from e

    import base64

    signature = base64.b64decode(signature_b64.encode("ascii"))

    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend(),
    )

    try:
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def sign_card(
    card: CapabilityCard,
    *,
    signer_id: str = "arc-runtime",
    secret_key: Optional[str] = None,
    private_key_pem: Optional[str] = None,
) -> SignedCapabilityCard:
    """Sign a Capability Card.

    Args:
        card: The CapabilityCard to sign.
        signer_id: Identity of the signer (e.g., "arc-runtime", "user@example.com").
        secret_key: HMAC secret key (required if not using private_key_pem).
        private_key_pem: ECDSA private key in PEM format (required if not using secret_key).

    Returns:
        SignedCapabilityCard with the signature attached.

    Raises:
        ValueError: If neither or both of secret_key and private_key_pem are provided,
            or if the private key is invalid.
    """
    if (secret_key is None) == (private_key_pem is None):
        raise ValueError("Provide exactly one of secret_key (HMAC) or private_key_pem (ECDSA)")

    canonical_data = _canonicalize_for_signing(card)

    if secret_key is not None:
        algorithm = SignatureAlgorithm.HMAC_SHA256
        signature_b64 = _hmac_sha256_sign(canonical_data, secret_key)
        # Store a hash of the secret for verification (not the secret itself)
        secret_hash = hashlib.sha256(secret_key.encode()).hexdigest()
        signature = CardSignature(
            algorithm=algorithm,
            signature=signature_b64,
            signer_id=signer_id,
            secret_hash=secret_hash,
        )
    else:
        algorithm = SignatureAlgorithm.ECDSA_P256
        signature_b64, public_key_pem = _ecdsa_p256_sign(canonical_data, private_key_pem)
        signature = CardSignature(
            algorithm=algorithm,
            signature=signature_b64,
            signer_id=signer_id,
            public_key_pem=public_key_pem,
        )

    return SignedCapabilityCard(card=card, signature=signature)


def verify_card(
    signed_card: SignedCapabilityCard,
    *,
    secret_key: Optional[str] = None,
    public_key_pem: Optional[str] = None,
) -> bool:
    """Verify a signed Capability Card.

    Args:
        signed_card: The SignedCapabilityCard to verify.
        secret_key: HMAC secret key (required if card was signed with HMAC).
        public_key_pem: ECDSA public key in PEM format (required if card was signed with ECDSA).

    Returns:
        True if the signature is valid, False otherwise.
    """
    algorithm = signed_card.signature.algorithm

    if algorithm == SignatureAlgorithm.HMAC_SHA256:
        if secret_key is None:
            raise ValueError("secret_key required for HMAC-SHA256 verification")
        canonical_data = _canonicalize_for_signing(signed_card.card)
        return _hmac_sha256_verify(canonical_data, signed_card.signature.signature, secret_key)
    elif algorithm == SignatureAlgorithm.ECDSA_P256:
        if public_key_pem is None:
            # Use the embedded public key if available
            if signed_card.signature.public_key_pem is None:
                raise ValueError("public_key_pem required for ECDSA-P256 verification")
            public_key_pem = signed_card.signature.public_key_pem
        canonical_data = _canonicalize_for_signing(signed_card.card)
        return _ecdsa_p256_verify(canonical_data, signed_card.signature.signature, public_key_pem)

    return False


def sign_card_file(
    card_path: Path,
    signed_path: Optional[Path] = None,
    *,
    signer_id: str = "arc-runtime",
    secret_key: Optional[str] = None,
    private_key_pem: Optional[str] = None,
) -> Path:
    """Sign a Capability Card file and write the signed version.

    Args:
        card_path: Path to the card JSON file.
        signed_path: Optional output path for the signed card. Defaults to <card_path>.signed.json.
        signer_id: Identity of the signer.
        secret_key: HMAC secret key.
        private_key_pem: ECDSA private key.

    Returns:
        Path to the signed card file.
    """
    import json as _json

    with open(card_path) as f:
        card_data = _json.load(f)

    card = CapabilityCard.model_validate(card_data)
    signed = sign_card(
        card,
        signer_id=signer_id,
        secret_key=secret_key,
        private_key_pem=private_key_pem,
    )

    output_path = signed_path or card_path.with_suffix(".signed.json")
    with open(output_path, "w") as f:
        _json.dump(
            {
                "card": card.model_dump(mode="json"),
                "signature": signed.signature.model_dump(mode="json"),
            },
            f,
            indent=2,
        )

    return output_path


def verify_card_file(
    signed_path: Path,
    *,
    secret_key: Optional[str] = None,
    public_key_pem: Optional[str] = None,
) -> bool:
    """Verify a signed Capability Card file.

    Args:
        signed_path: Path to the signed card JSON file.
        secret_key: HMAC secret key.
        public_key_pem: ECDSA public key.

    Returns:
        True if the signature is valid.
    """
    import json as _json

    with open(signed_path) as f:
        data = _json.load(f)

    card = CapabilityCard.model_validate(data["card"])
    signature = CardSignature.model_validate(data["signature"])

    signed_card = SignedCapabilityCard(card=card, signature=signature)
    return verify_card(signed_card, secret_key=secret_key, public_key_pem=public_key_pem)


def generate_secret_key() -> str:
    """Generate a random HMAC secret key.

    Returns:
        A 32-byte hex string suitable for HMAC-SHA256 signing.
    """
    import secrets

    return secrets.token_hex(32)


def generate_ecdsa_keypair() -> tuple[str, str]:
    """Generate an ECDSA-P256 keypair.

    Returns:
        Tuple of (private_key_pem, public_key_pem).
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
    except ImportError as e:
        raise ImportError(
            "cryptography package required for ECDSA key generation. "
            "Install with: pip install cryptography"
        ) from e

    private_key = ec.generate_private_key(ec.SECP256R1(), backend=default_backend())

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")

    return private_pem, public_pem


# ─── Exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "SignatureAlgorithm",
    "CardSignature",
    "SignedCapabilityCard",
    "sign_card",
    "verify_card",
    "sign_card_file",
    "verify_card_file",
    "generate_secret_key",
    "generate_ecdsa_keypair",
]
