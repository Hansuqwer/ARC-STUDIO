"""Mobile DoD gate 6 (security: signed plan + RBAC audit) tests.

Phase 220 — R-MOBILE-POLISH3
"""

from __future__ import annotations

import json


class TestMobileGate6Security:
    """DoD gate 6: security decisions deterministic, audit appended on execute."""

    def test_gate_always_denies_without_signed_plan(self):
        """CapabilityEntryGate must deny without a signed plan (deterministic)."""
        import secrets
        from agent_runtime_cockpit.mobile.capability_gate import CapabilityEntryGate
        from agent_runtime_cockpit.mobile.feature_flags import FeatureFlags

        gate = CapabilityEntryGate(FeatureFlags(), secrets.token_bytes(32))
        decision = gate.evaluate("device.camera.capture.mock")
        assert not decision.eligible
        assert "signed_plan_invalid" in decision.missing

    def test_gate_always_routes_to_fixtures(self):
        """Gate must always route to 'fixtures' regardless of eligibility (never real device)."""
        import secrets
        from agent_runtime_cockpit.mobile.capability_gate import CapabilityEntryGate, FIXTURES_ROUTE
        from agent_runtime_cockpit.mobile.feature_flags import FeatureFlags

        gate = CapabilityEntryGate(FeatureFlags(), secrets.token_bytes(32))
        result = gate.execute("app.memory.retrieve.mock")
        assert result["route"] == FIXTURES_ROUTE
        assert result["executed_real_device"] is False

    def test_gate_execute_appends_to_audit_log(self, tmp_path, monkeypatch):
        """gate.execute() must append an audit entry (gate 6: audit on allow/deny)."""
        import secrets
        from agent_runtime_cockpit.mobile import capability_gate as cg
        from agent_runtime_cockpit.mobile.capability_gate import CapabilityEntryGate
        from agent_runtime_cockpit.mobile.feature_flags import FeatureFlags

        audit_path = tmp_path / "gate_decisions.jsonl"
        monkeypatch.setattr(cg, "_GATE_AUDIT_LOG", audit_path)

        gate = CapabilityEntryGate(FeatureFlags(), secrets.token_bytes(32))
        gate.execute("app.memory.retrieve.mock")

        assert audit_path.exists(), "Gate must write to audit log on execute"
        lines = [l for l in audit_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["capability_id"] == "app.memory.retrieve.mock"
        assert "logged_at" in entry

    def test_gate_audit_appended_on_both_allow_and_deny(self, tmp_path, monkeypatch):
        """Audit log must be written regardless of eligible/denied outcome."""
        import secrets
        from agent_runtime_cockpit.mobile import capability_gate as cg
        from agent_runtime_cockpit.mobile.capability_gate import CapabilityEntryGate
        from agent_runtime_cockpit.mobile.feature_flags import FeatureFlags

        audit_path = tmp_path / "gate_audit.jsonl"
        monkeypatch.setattr(cg, "_GATE_AUDIT_LOG", audit_path)

        gate = CapabilityEntryGate(FeatureFlags(), secrets.token_bytes(32))
        gate.execute("cap.one.mock")
        gate.execute("cap.two.mock")

        lines = [l for l in audit_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2, "Both gate executes must produce audit entries"
