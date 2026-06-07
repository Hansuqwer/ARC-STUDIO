"""Tests for PR16: runtime_pack bridge capabilities_detail and platform_support."""

from __future__ import annotations


class TestRuntimePackDetail:
    def test_pack_contains_capabilities_detail(self, tmp_path):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.runtime_pack import build_runtime_pack_manifest

        m = build_default_manifest("test.detail", "Detail Test")
        pack = build_runtime_pack_manifest(m, tmp_path)
        detail = pack["metadata"]["capabilities_detail"]
        assert len(detail) == 13
        first = detail[0]
        for key in (
            "data_sensitivity",
            "approval_mode",
            "reads",
            "writes",
            "requires_trust",
            "mcp_exposable",
            "capability_hash",
        ):
            assert key in first, f"Missing key {key!r} in capabilities_detail entry"

    def test_pack_contains_platform_support(self, tmp_path):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.runtime_pack import build_runtime_pack_manifest

        m = build_default_manifest("test.platforms", "Platform Test")
        pack = build_runtime_pack_manifest(m, tmp_path)
        plat = pack["metadata"]["platform_support"]
        assert len(plat) > 0
        assert "stub_only" in plat[0]
        assert "framework" in plat[0]

    def test_pack_still_has_capability_ids_list(self, tmp_path):
        from agent_runtime_cockpit.mobile import build_default_manifest
        from agent_runtime_cockpit.mobile.runtime_pack import build_runtime_pack_manifest

        m = build_default_manifest("test.ids", "IDs Test")
        pack = build_runtime_pack_manifest(m, tmp_path)
        cap_ids = pack["metadata"]["mobile_capabilities"]
        assert len(cap_ids) == 13
        assert all(isinstance(cid, str) for cid in cap_ids)
