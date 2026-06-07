"""Tests for PR19: ApprovalGrant model + issue/revoke engine."""

from __future__ import annotations

import time


class TestApprovalGrant:
    def setup_method(self):
        from agent_runtime_cockpit.mobile.approval import clear_grants

        clear_grants()

    def test_issue_grant_is_valid(self):
        from agent_runtime_cockpit.mobile.approval import issue_grant

        grant = issue_grant("app.memory.write.mock", "write:once", ttl_seconds=300)
        assert grant.is_valid()
        assert grant.capability_id == "app.memory.write.mock"
        assert grant.scope == "write:once"
        assert not grant.revoked

    def test_expired_grant_is_invalid(self):
        from agent_runtime_cockpit.mobile.approval import issue_grant

        grant = issue_grant("app.memory.write.mock", "write:once", ttl_seconds=0)
        # ttl=0: should expire immediately (or in < 1s)
        time.sleep(0.01)
        assert not grant.is_valid()

    def test_revoke_grant(self):
        from agent_runtime_cockpit.mobile.approval import issue_grant, revoke_grant, get_grant

        grant = issue_grant("app.memory.write.mock", "write:once", ttl_seconds=300)
        assert revoke_grant(grant.grant_id) is True
        stored = get_grant(grant.grant_id)
        assert stored is not None
        assert stored.revoked is True
        assert not stored.is_valid()

    def test_revoke_nonexistent_returns_false(self):
        from agent_runtime_cockpit.mobile.approval import revoke_grant

        assert revoke_grant("nonexistent-id") is False

    def test_list_active_grants(self):
        from agent_runtime_cockpit.mobile.approval import (
            issue_grant,
            revoke_grant,
            list_active_grants,
        )

        g1 = issue_grant("app.memory.write.mock", "s1", ttl_seconds=300)
        g2 = issue_grant("app.memory.retrieve.mock", "s2", ttl_seconds=300)
        revoke_grant(g1.grant_id)
        active = list_active_grants()
        ids = [g.grant_id for g in active]
        assert g1.grant_id not in ids
        assert g2.grant_id in ids

    def test_grant_ids_unique(self):
        from agent_runtime_cockpit.mobile.approval import issue_grant

        g1 = issue_grant("app.memory.write.mock", "s", ttl_seconds=300)
        g2 = issue_grant("app.memory.write.mock", "s", ttl_seconds=300)
        assert g1.grant_id != g2.grant_id

    def test_grant_with_plan_hash(self):
        from agent_runtime_cockpit.mobile.approval import issue_grant

        grant = issue_grant(
            "device.camera.capture.mock", "read:once", ttl_seconds=60, plan_hash="abc" * 21 + "d"
        )
        assert grant.plan_hash is not None
