"""Tests for optional exporters (capability card, policy findings, IR compat, MCP verify).

All exporters are guarded with try/except.  In the isolated test environment
(minimal venv) the ``..capabilities``, ``..security.policy_linter``,
``..swarmgraph_ir``, and ``..mcp`` modules may or may not be importable.  These
tests verify the *contract*: the function always returns *something* (never
raises), and the shape is correct whether the real types or fallback dicts are
used.
"""

from __future__ import annotations

from agent_runtime_cockpit.runtime_packs import (
    OpaqueNodePolicy,
    RuntimeIdentity,
    RuntimeIrDeclaration,
    RuntimePackManifest,
    ir_compatibility,
    manifest_hash,
    to_capability_card,
    to_policy_findings,
    validate_manifest,
    verify_mcp_against_registry,
)


def _make(id_: str = "x.y", **kwargs) -> RuntimePackManifest:
    m = RuntimePackManifest(
        id=id_,
        name="X",
        runtime=RuntimeIdentity(runtime_name="X"),
        **kwargs,
    )
    m.manifest_hash = manifest_hash(m)
    return m


class TestToCapabilityCard:
    def test_returns_without_raising(self, minimal_manifest):
        result = to_capability_card(minimal_manifest)
        assert result is not None

    def test_result_has_prefixed_id(self, minimal_manifest):
        result = to_capability_card(minimal_manifest)
        # The card id is prefixed with "runtime-pack:" (whether real card or dict fallback)
        card_id = getattr(result, "id", None) or (
            result.get("id") if isinstance(result, dict) else None
        )
        assert card_id == f"runtime-pack:{minimal_manifest.id}"

    def test_result_has_name(self, minimal_manifest):
        result = to_capability_card(minimal_manifest)
        name = getattr(result, "name", None) or (
            result.get("name") if isinstance(result, dict) else None
        )
        assert name == minimal_manifest.name


class TestToPolicyFindings:
    def test_clean_manifest_no_findings(self, minimal_manifest):
        report = validate_manifest(minimal_manifest)
        result = to_policy_findings(report)
        assert isinstance(result, list)
        assert result == []

    def test_invalid_manifest_returns_findings(self):
        m = _make()
        m.manifest_hash = "d" * 64  # drift the hash
        report = validate_manifest(m)
        result = to_policy_findings(report)
        assert isinstance(result, list)
        # Drifted hash → at least one finding
        assert len(result) >= 1

    def test_findings_have_rule_key(self):
        m = _make()
        m.manifest_hash = "d" * 64
        report = validate_manifest(m)
        result = to_policy_findings(report)
        for finding in result:
            rule_val = getattr(finding, "rule", None) or (
                finding.get("rule") if isinstance(finding, dict) else None
            )
            assert rule_val is not None


class TestIrCompatibility:
    def test_returns_dict_always(self, minimal_manifest):
        result = ir_compatibility(minimal_manifest)
        assert isinstance(result, dict)

    def test_no_ir_claim(self, minimal_manifest):
        result = ir_compatibility(minimal_manifest)
        assert result.get("can_export_ir") is False

    def test_ir_claim_compatible(self):
        m = _make(
            ir=RuntimeIrDeclaration(
                can_export_ir=True,
                supported_ir_version=1,
                opaque_node_policy=OpaqueNodePolicy.REJECT,
            )
        )
        result = ir_compatibility(m)
        assert result.get("can_export_ir") is True
        assert "compatible" in result or "local_ir_version" in result


class TestVerifyMcpAgainstRegistry:
    def test_no_mcp_returns_empty_list(self, minimal_manifest):
        result = verify_mcp_against_registry(minimal_manifest)
        assert isinstance(result, list)
        assert result == []

    def test_unknown_mcp_returns_status_unknown(self):
        from agent_runtime_cockpit.runtime_packs import RuntimeMcpDeclaration

        m = _make(mcp=[RuntimeMcpDeclaration(server_id="ghost-mcp", required=True)])
        result = verify_mcp_against_registry(m)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["server_id"] == "ghost-mcp"
        assert result[0]["status"] == "unknown"
