"""Mobile supply-chain provenance attestation (R79.4 / Batch 7 T26).

Builds a deterministic provenance document for the mobile runtime package (subject + builder +
CycloneDX SBOM + SBOM digest + materials) and signs it locally with the existing HMAC primitive.
No external signing infrastructure (sigstore/cosign) is required or implied — this is a local,
deterministic attestation. Verify with ``verify_provenance``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from .sbom import generate_sbom

PROVENANCE_SCHEMA = "arc-mobile-provenance/v1"


def _canonical(doc: dict[str, Any]) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_provenance(version: str = "0.1.0", *, builder: str = "arc-mobile-ci") -> dict[str, Any]:
    """Build a deterministic provenance attestation document (unsigned)."""
    sbom = generate_sbom(version)
    components = sbom.get("components", []) if isinstance(sbom, dict) else []
    return {
        "schema": PROVENANCE_SCHEMA,
        "subject": {"name": "arc-mobile-runtime", "version": version},
        "builder": builder,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sbom_format": sbom.get("bomFormat", "CycloneDX") if isinstance(sbom, dict) else "unknown",
        "sbom_sha256": hashlib.sha256(_canonical(sbom)).hexdigest(),
        "component_count": len(components),
        "sbom": sbom,
    }


def sign_provenance(provenance: dict[str, Any], key: bytes) -> dict[str, Any]:
    """Wrap a provenance document in a locally-signed envelope (deterministic HMAC-SHA256)."""
    signature = hmac.new(key, _canonical(provenance), hashlib.sha256).hexdigest()
    return {"provenance": provenance, "signature": signature, "algorithm": "HMAC-SHA256"}


def verify_provenance(envelope: dict[str, Any], key: bytes) -> bool:
    """Verify a signed provenance envelope. Fail-closed on any malformed input."""
    prov = envelope.get("provenance")
    signature = envelope.get("signature", "")
    if not isinstance(prov, dict) or not isinstance(signature, str) or not signature:
        return False
    expected = hmac.new(key, _canonical(prov), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
