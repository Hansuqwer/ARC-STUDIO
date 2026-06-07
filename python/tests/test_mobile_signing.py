"""Tests for PR18: plan signing envelope (HMAC-SHA256)."""

from __future__ import annotations

import os


def _plan():
    from agent_runtime_cockpit.mobile import MobileActionPlan, MobileActionStep

    return MobileActionPlan(
        plan_id="sign-test",
        steps=[MobileActionStep(step_id="s1", capability_id="app.memory.write.mock", mock=True)],
    )


class TestPlanSigning:
    def test_sign_and_verify(self):
        from agent_runtime_cockpit.mobile import sign_plan, verify_plan

        key = os.urandom(32)
        env = sign_plan(_plan(), key)
        assert verify_plan(env, key) is True

    def test_wrong_key_fails(self):
        from agent_runtime_cockpit.mobile import sign_plan, verify_plan

        key = os.urandom(32)
        env = sign_plan(_plan(), key)
        assert verify_plan(env, os.urandom(32)) is False

    def test_tampered_plan_fails(self):
        from agent_runtime_cockpit.mobile import sign_plan, verify_plan

        key = os.urandom(32)
        env = sign_plan(_plan(), key)
        env.plan["plan_id"] = "tampered"
        assert verify_plan(env, key) is False

    def test_tampered_signature_fails(self):
        from agent_runtime_cockpit.mobile import sign_plan, verify_plan

        key = os.urandom(32)
        env = sign_plan(_plan(), key)
        env.signature = "0" * 64
        assert verify_plan(env, key) is False

    def test_envelope_has_nonce(self):
        from agent_runtime_cockpit.mobile import sign_plan

        key = os.urandom(32)
        e1 = sign_plan(_plan(), key)
        e2 = sign_plan(_plan(), key)
        assert e1.nonce != e2.nonce  # replay prevention

    def test_envelope_fields_present(self):
        from agent_runtime_cockpit.mobile import sign_plan

        key = os.urandom(32)
        env = sign_plan(_plan(), key)
        assert env.algorithm == "hmac-sha256"
        assert env.version == "1"
        assert len(env.plan_hash) == 64
        assert len(env.signature) == 64
        assert env.plan_id == "sign-test"
