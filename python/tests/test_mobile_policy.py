"""Tests for PR12: policy versioning, decision logging, enterprise hook."""

from __future__ import annotations

import json


class TestPolicyVersion:
    def test_capability_decision_has_policy_version(self):
        from agent_runtime_cockpit.mobile import explain_capability_policy, get_capability

        cap = get_capability("app.memory.write.mock")
        decision = explain_capability_policy(cap, log_decision=False)
        assert decision.policy_version == "1.0.0"

    def test_plan_decision_has_policy_version(self):
        from agent_runtime_cockpit.mobile import (
            MobileActionPlan,
            MobileActionStep,
            explain_plan_policy,
            list_capabilities,
        )

        plan = MobileActionPlan(
            plan_id="pv-test",
            steps=[
                MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)
            ],
        )
        decision = explain_plan_policy(plan, list_capabilities(), log_decision=False)
        assert decision.policy_version == "1.0.0"

    def test_denied_capability_has_policy_version(self):
        from agent_runtime_cockpit.mobile import MobileCapability, explain_capability_policy

        cap = MobileCapability(id="device.camera.capture", name="Real Cam")  # invalid
        decision = explain_capability_policy(cap, log_decision=False)
        assert not decision.allowed
        assert decision.policy_version == "1.0.0"


class TestDecisionLogging:
    def test_decision_logged_to_file(self, tmp_path, monkeypatch):
        import agent_runtime_cockpit.mobile.policy as pol

        audit_file = tmp_path / "mobile_decisions.jsonl"
        monkeypatch.setattr(pol, "_AUDIT_FILE", audit_file)
        from agent_runtime_cockpit.mobile import get_capability

        cap = get_capability("app.memory.retrieve.mock")
        from agent_runtime_cockpit.mobile.policy import explain_capability_policy

        explain_capability_policy(cap, log_decision=True)
        assert audit_file.exists()
        lines = [json.loads(l) for l in audit_file.read_text().splitlines()]
        assert len(lines) == 1
        assert lines[0]["policy_version"] == "1.0.0"
        assert "logged_at" in lines[0]

    def test_log_decision_false_skips_file(self, tmp_path, monkeypatch):
        import agent_runtime_cockpit.mobile.policy as pol

        audit_file = tmp_path / "mobile_decisions.jsonl"
        monkeypatch.setattr(pol, "_AUDIT_FILE", audit_file)
        from agent_runtime_cockpit.mobile import get_capability
        from agent_runtime_cockpit.mobile.policy import explain_capability_policy

        explain_capability_policy(get_capability("app.memory.write.mock"), log_decision=False)
        assert not audit_file.exists()


class TestEnterprisePolicyHook:
    def test_hook_can_override_decision(self):
        from agent_runtime_cockpit.mobile.policy import (
            explain_capability_policy,
            MobilePolicyDecision,
        )
        from agent_runtime_cockpit.mobile import get_capability

        class AlwaysDenyHook:
            def evaluate(self, decision, context):
                return MobilePolicyDecision(
                    allowed=False,
                    reason="enterprise hook denied",
                    denied_rules=["enterprise_deny"],
                )

        cap = get_capability("app.memory.write.mock")
        decision = explain_capability_policy(
            cap, enterprise_hook=AlwaysDenyHook(), log_decision=False
        )
        assert not decision.allowed
        assert decision.reason == "enterprise hook denied"

    def test_hook_returning_none_preserves_default(self):
        from agent_runtime_cockpit.mobile.policy import explain_capability_policy
        from agent_runtime_cockpit.mobile import get_capability

        class PassthroughHook:
            def evaluate(self, decision, context):
                return None  # defer

        cap = get_capability("app.memory.write.mock")
        decision = explain_capability_policy(
            cap, enterprise_hook=PassthroughHook(), log_decision=False
        )
        assert decision.allowed  # default behavior preserved
