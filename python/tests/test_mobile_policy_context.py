"""Tests for T10 (Phase 12): org/tenant policy context + RBAC/ABAC + signed bundle."""

from __future__ import annotations


from agent_runtime_cockpit.mobile import (
    MobilePolicyDecision,
    OrgPolicyBundle,
    OrgPolicyContext,
    TenantPolicyHook,
    explain_capability_policy,
    sign_org_bundle,
    verify_org_bundle,
)
from agent_runtime_cockpit.mobile.capabilities import get_capability, list_capabilities

KEY = b"0" * 32


def _decision(cap_id: str = "device.camera.capture.mock") -> MobilePolicyDecision:
    return MobilePolicyDecision(allowed=True, capability_id=cap_id, reason="base allow")


def test_sign_and_verify_round_trip() -> None:
    bundle = OrgPolicyBundle(tenant_id="acme")
    signed = sign_org_bundle(bundle, KEY)
    assert signed.signature
    assert verify_org_bundle(signed, KEY) is True


def test_tampered_or_wrong_key_fails_verify() -> None:
    signed = sign_org_bundle(OrgPolicyBundle(tenant_id="acme", denied_capabilities=["x"]), KEY)
    tampered = signed.model_copy(update={"denied_capabilities": []})
    assert verify_org_bundle(tampered, KEY) is False
    assert verify_org_bundle(signed, b"1" * 32) is False


def test_unsigned_bundle_fails_closed() -> None:
    bundle = OrgPolicyBundle(tenant_id="acme")  # no signature
    hook = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "user"))
    out = hook.evaluate(_decision(), {})
    assert out is not None and out.allowed is False
    assert "org_bundle_signature_invalid" in out.denied_rules


def test_tenant_mismatch_denied() -> None:
    bundle = sign_org_bundle(OrgPolicyBundle(tenant_id="acme"), KEY)
    hook = TenantPolicyHook(bundle, KEY, OrgPolicyContext("other-tenant", "user"))
    out = hook.evaluate(_decision(), {})
    assert out is not None and out.allowed is False and "tenant_mismatch" in out.denied_rules


def test_rbac_role_denied() -> None:
    bundle = sign_org_bundle(
        OrgPolicyBundle(tenant_id="acme", allowed_roles={"device.camera.capture.mock": ["admin"]}),
        KEY,
    )
    hook = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "user"))
    out = hook.evaluate(_decision(), {})
    assert out is not None and out.allowed is False and "rbac_role_denied" in out.denied_rules
    # admin is permitted -> defer (None)
    hook_admin = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "admin"))
    assert hook_admin.evaluate(_decision(), {}) is None


def test_capability_and_abac_denials() -> None:
    bundle = sign_org_bundle(
        OrgPolicyBundle(
            tenant_id="acme",
            denied_capabilities=["device.camera.capture.mock"],
            denied_attributes={"region": ["us"]},
        ),
        KEY,
    )
    hook = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "admin", {"region": "eu"}))
    out = hook.evaluate(_decision(), {})
    assert out is not None and "tenant_capability_denied" in out.denied_rules
    # ABAC: a us-region context is denied even for an otherwise-allowed capability
    hook_us = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "admin", {"region": "us"}))
    out_us = hook_us.evaluate(_decision("app.memory.write.mock"), {})
    assert out_us is not None and any(r.startswith("abac_denied") for r in out_us.denied_rules)


def test_integration_with_explain_capability_policy() -> None:
    cap = get_capability("app.memory.write.mock") or list_capabilities()[0]
    bundle = sign_org_bundle(
        OrgPolicyBundle(tenant_id="acme", allowed_roles={cap.id: ["admin"]}), KEY
    )
    hook = TenantPolicyHook(bundle, KEY, OrgPolicyContext("acme", "intern"))
    decision = explain_capability_policy(cap, enterprise_hook=hook, log_decision=False)
    assert decision.allowed is False and "rbac_role_denied" in decision.denied_rules
