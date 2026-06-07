"""Strict validation tests for ARC Mobile Runtime Simulator Preview."""

from __future__ import annotations


def test_strict_manifest_rejects_duplicate_capability_ids():
    from agent_runtime_cockpit.mobile import (
        MobileCapability,
        MobileRuntimeManifest,
        validate_manifest,
    )
    from agent_runtime_cockpit.mobile.hashing import capability_hash, manifest_hash

    cap = MobileCapability(id="app.duplicate.mock", name="Duplicate", requires_trust=True)
    cap.capability_hash = capability_hash(cap)
    duplicate = cap.model_copy(deep=True)
    manifest = MobileRuntimeManifest(
        id="test.duplicate",
        name="Duplicate Test",
        capabilities=[cap, duplicate],
    )
    manifest.manifest_hash = manifest_hash(manifest)

    report = validate_manifest(manifest, strict=True)

    assert not report.ok
    assert any(f.rule == "duplicate_capability_id" for f in report.errors)


def test_strict_manifest_rejects_invalid_capability_id():
    from agent_runtime_cockpit.mobile import (
        MobileCapability,
        MobileRuntimeManifest,
        validate_manifest,
    )
    from agent_runtime_cockpit.mobile.hashing import capability_hash, manifest_hash

    cap = MobileCapability(id="Bad Capability ID", name="Bad", requires_trust=True)
    cap.capability_hash = capability_hash(cap)
    manifest = MobileRuntimeManifest(id="test.bad-id", name="Bad ID", capabilities=[cap])
    manifest.manifest_hash = manifest_hash(manifest)

    report = validate_manifest(manifest, strict=True)

    assert not report.ok
    assert any(f.rule == "capability_id_invalid" for f in report.errors)


def test_strict_manifest_requires_hash_pinning():
    from agent_runtime_cockpit.mobile import MobileCapability, MobileRuntimeManifest, validate_manifest

    cap = MobileCapability(id="app.unpinned.mock", name="Unpinned", requires_trust=True)
    manifest = MobileRuntimeManifest(id="test.unpinned", name="Unpinned", capabilities=[cap])

    report = validate_manifest(manifest, strict=True)

    assert not report.ok
    assert any(f.rule == "manifest_not_pinned" for f in report.errors)
    assert any(f.rule == "capability_not_pinned" for f in report.errors)


def test_strict_write_without_hitl_or_trust_is_error():
    from agent_runtime_cockpit.mobile import MobileCapability, validate_capability
    from agent_runtime_cockpit.mobile.hashing import capability_hash

    cap = MobileCapability(
        id="app.write_without_gate.mock",
        name="Write Without Gate",
        writes=True,
        auditable=True,
        requires_hitl=False,
        requires_trust=False,
    )
    cap.capability_hash = capability_hash(cap)

    loose = validate_capability(cap)
    strict = validate_capability(cap, strict=True)

    assert loose.ok
    assert any(f.rule == "write_requires_hitl_or_trust" for f in loose.warnings)
    assert not strict.ok
    assert any(f.rule == "write_requires_hitl_or_trust" for f in strict.errors)


def test_strict_action_plan_rejects_duplicate_step_ids():
    from agent_runtime_cockpit.mobile import (
        MobileActionPlan,
        MobileActionStep,
        MobileCapability,
        validate_action_plan,
    )

    cap = MobileCapability(id="app.memory.write.mock", name="Memory", requires_trust=True)
    plan = MobileActionPlan(
        plan_id="plan.duplicate-steps",
        steps=[
            MobileActionStep(step_id="same", capability_id="app.memory.write.mock"),
            MobileActionStep(step_id="same", capability_id="app.memory.write.mock"),
        ],
    )

    report = validate_action_plan(plan, [cap], strict=True)

    assert not report.ok
    assert any(f.rule == "duplicate_step_id" for f in report.errors)
