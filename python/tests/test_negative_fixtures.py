"""Tests for PR13: extras sensitivity guard and negative fixtures."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "mobile" / "fixtures"


class TestExtrasSensitivityGuard:
    def test_high_sensitivity_non_mock_extra_is_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            simulate_action_plan,
        )

        sensitive_extra = MobileCapability(
            id="device.camera.capture.real",  # NOT .mock but HIGH sensitivity
            name="Real Camera",
            category=MobileCapabilityCategory.MEDIA,
            data_sensitivity=MobileDataSensitivity.HIGH,
            approval_mode=MobileApprovalMode.REQUIRED,
        )
        plan = MobileActionPlan(
            plan_id="extras-guard",
            steps=[
                MobileActionStep(
                    step_id="s1", capability_id="device.camera.capture.real", mock=False
                )
            ],
        )
        report = simulate_action_plan(plan, extra_capabilities=[sensitive_extra])
        assert not report.overall_allowed
        assert "s1" in report.blocked_steps
        assert any("EXTRAS_SENSITIVITY_GUARD" in w for w in report.warnings)

    def test_mock_extra_allowed(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            simulate_action_plan,
        )

        mock_extra = MobileCapability(
            id="app.custom.action.mock",
            name="Custom Mock",
            category=MobileCapabilityCategory.APP,
            data_sensitivity=MobileDataSensitivity.LOW,
            approval_mode=MobileApprovalMode.NONE,
        )
        plan = MobileActionPlan(
            plan_id="mock-extra-ok",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.custom.action.mock", mock=True)
            ],
        )
        report = simulate_action_plan(plan, extra_capabilities=[mock_extra])
        assert report.overall_allowed
        assert not any("EXTRAS_SENSITIVITY_GUARD" in w for w in report.warnings)

    def test_critical_sensitivity_non_mock_extra_blocked(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            MobileCapability,
            MobileCapabilityCategory,
            MobileDataSensitivity,
            MobileApprovalMode,
            simulate_action_plan,
        )

        critical_extra = MobileCapability(
            id="device.contacts.search.real",
            name="Real Contacts",
            category=MobileCapabilityCategory.COMMUNICATION,
            data_sensitivity=MobileDataSensitivity.CRITICAL,
            approval_mode=MobileApprovalMode.BLOCKING,
        )
        plan = MobileActionPlan(
            plan_id="critical-guard",
            steps=[
                MobileActionStep(
                    step_id="s1", capability_id="device.contacts.search.real", mock=False
                )
            ],
        )
        report = simulate_action_plan(plan, extra_capabilities=[critical_extra])
        assert not report.overall_allowed


class TestNegativeFixtures:
    def test_duplicate_ids_manifest_rejected(self):
        from agent_runtime_cockpit.mobile.manifest import load_manifest, MobileManifestLoadError

        with pytest.raises(MobileManifestLoadError, match="duplicate"):
            load_manifest(FIXTURES / "duplicate_ids_manifest.json")

    def test_wrong_hash_manifest_fails_validation(self):
        from agent_runtime_cockpit.mobile.manifest import load_manifest
        from agent_runtime_cockpit.mobile import validate_manifest

        m = load_manifest(FIXTURES / "wrong_hash_manifest.json")
        report = validate_manifest(m)
        assert not report.ok
        assert any("hash_mismatch" in f.rule for f in report.errors)

    def test_malicious_metadata_secret_redacted(self):
        from agent_runtime_cockpit.mobile.manifest import load_manifest
        from agent_runtime_cockpit.mobile.redaction import redact_dict

        m = load_manifest(FIXTURES / "malicious_metadata_manifest.json")
        # The api_key in metadata should be redacted
        cap = m.capabilities[0]
        redacted, count = redact_dict(dict(cap.metadata))
        assert count > 0, "Expected at least 1 redacted secret in metadata"
        assert redacted.get("api_key") == "[REDACTED]"


import pytest  # noqa: E402 — placed after test classes for readability
