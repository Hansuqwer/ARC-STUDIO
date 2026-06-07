"""Org/tenant policy context for ARC Mobile Runtime (Phase 12).

A deterministic RBAC/ABAC overlay delivered as a SIGNED org policy bundle. Implements
``EnterprisePolicyHook`` so it composes with the existing capability/plan policy. Fails
closed: an unsigned/forged bundle, a tenant mismatch, a bundle-denied capability, or a role
not permitted for a capability all yield a denial. HMAC-SHA256 signing (reuses the project's
symmetric-key approach). No LLM, no network.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .policy import MOBILE_POLICY_VERSION, MobilePolicyDecision

BUNDLE_SIGN_ALGORITHM = "hmac-sha256"


class OrgPolicyBundle(BaseModel):
    """A signed, tenant-scoped RBAC/ABAC policy bundle."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    version: str = "1"
    # capability_id -> roles permitted to use it. Absent/empty list = no RBAC restriction.
    allowed_roles: dict[str, list[str]] = Field(default_factory=dict)
    # capabilities denied outright for this tenant.
    denied_capabilities: list[str] = Field(default_factory=list)
    # ABAC: attribute key -> set of values that are denied (e.g. {"region": ["us"]}).
    denied_attributes: dict[str, list[str]] = Field(default_factory=dict)
    algorithm: str = BUNDLE_SIGN_ALGORITHM
    signature: str = ""


def _bundle_message(bundle: OrgPolicyBundle) -> bytes:
    payload = bundle.model_dump(mode="json")
    payload.pop("signature", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_org_bundle(bundle: OrgPolicyBundle, key: bytes) -> OrgPolicyBundle:
    """Return a copy of the bundle with a valid HMAC signature."""
    sig = hmac.new(key, _bundle_message(bundle), hashlib.sha256).hexdigest()
    return bundle.model_copy(update={"signature": sig})


def verify_org_bundle(bundle: OrgPolicyBundle, key: bytes) -> bool:
    """Constant-time verify the bundle signature."""
    if not bundle.signature:
        return False
    expected = hmac.new(key, _bundle_message(bundle), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, bundle.signature)


@dataclass
class OrgPolicyContext:
    """The caller's RBAC/ABAC context (tenant, role, attributes)."""

    tenant_id: str
    role: str
    attributes: dict[str, Any] = field(default_factory=dict)


def _deny(decision: MobilePolicyDecision, rule: str, reason: str) -> MobilePolicyDecision:
    return decision.model_copy(
        update={
            "allowed": False,
            "reason": reason,
            "denied_rules": [*decision.denied_rules, rule],
            "policy_version": MOBILE_POLICY_VERSION,
        }
    )


class TenantPolicyHook:
    """EnterprisePolicyHook applying a signed tenant bundle deterministically (fail-closed)."""

    def __init__(self, bundle: OrgPolicyBundle, key: bytes, context: OrgPolicyContext) -> None:
        self.bundle = bundle
        self.context = context
        self._bundle_valid = verify_org_bundle(bundle, key)

    def evaluate(
        self, decision: MobilePolicyDecision, context: dict[str, Any]
    ) -> MobilePolicyDecision | None:
        cap_id = decision.capability_id or context.get("capability_id")

        # 1. Fail closed on an unsigned/forged bundle.
        if not self._bundle_valid:
            return _deny(
                decision, "org_bundle_signature_invalid", "org policy bundle signature invalid"
            )
        # 2. Tenant scoping.
        if self.context.tenant_id != self.bundle.tenant_id:
            return _deny(
                decision, "tenant_mismatch", "context tenant does not match policy bundle tenant"
            )
        # 3. ABAC attribute denials.
        for attr, denied_values in self.bundle.denied_attributes.items():
            if str(self.context.attributes.get(attr)) in {str(v) for v in denied_values}:
                return _deny(
                    decision, f"abac_denied:{attr}", f"attribute '{attr}' denied by org policy"
                )
        # 4. Tenant capability denial.
        if cap_id and cap_id in self.bundle.denied_capabilities:
            return _deny(
                decision, "tenant_capability_denied", f"capability '{cap_id}' denied for tenant"
            )
        # 5. RBAC: role must be permitted when the capability lists allowed roles.
        if cap_id:
            roles = self.bundle.allowed_roles.get(cap_id)
            if roles and self.context.role not in roles:
                return _deny(
                    decision,
                    "rbac_role_denied",
                    f"role '{self.context.role}' not permitted for '{cap_id}'",
                )
        # Defer to the base decision otherwise.
        return None
