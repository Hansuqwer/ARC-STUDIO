"""Tests for PR14: privacy budget ledger."""

from __future__ import annotations


class TestPrivacyBudget:
    def test_full_catalog_budget(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.privacy_budget import compute_privacy_budget

        m = build_default_manifest("test.budget", "Budget Test")
        budget = compute_privacy_budget(m)
        assert budget.total_capabilities == 13
        assert budget.read_capabilities > 0
        assert budget.write_capabilities > 0
        assert budget.advisory is True
        assert "critical" in budget.sensitive_classes or "high" in budget.sensitive_classes

    def test_empty_manifest_zeros(self):
        from agent_runtime_cockpit.mobile.models import MobileRuntimeManifest
        from agent_runtime_cockpit.mobile.privacy_budget import compute_privacy_budget

        m = MobileRuntimeManifest(id="empty", name="Empty")
        budget = compute_privacy_budget(m)
        assert budget.total_capabilities == 0
        assert budget.read_capabilities == 0
        assert budget.sensitive_classes == []

    def test_critical_capabilities_listed(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.privacy_budget import compute_privacy_budget

        m = build_default_manifest("test.crit", "Critical Test")
        budget = compute_privacy_budget(m)
        # microphone and contacts are critical in the built-in catalog
        assert "device.microphone.transcribe.mock" in budget.critical_capabilities
        assert "device.contacts.search.mock" in budget.critical_capabilities

    def test_budget_as_dict_has_advisory(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.privacy_budget import compute_privacy_budget

        m = build_default_manifest("test.dict", "Dict Test")
        d = compute_privacy_budget(m).as_dict()
        assert d["advisory"] is True
        assert "total_capabilities" in d
        assert "sensitive_classes" in d

    def test_network_and_background_zero_for_mock_catalog(self):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.privacy_budget import compute_privacy_budget

        m = build_default_manifest("test.net", "Net Test")
        budget = compute_privacy_budget(m)
        # All built-in capabilities have network=False and background=False
        assert budget.network_capabilities == 0
        assert budget.background_capabilities == 0
