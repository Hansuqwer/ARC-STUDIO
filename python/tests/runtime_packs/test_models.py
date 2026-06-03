"""Tests for runtime pack model declarations and convenience accessors."""

from __future__ import annotations

from agent_runtime_cockpit.runtime_packs import (
    DANGEROUS_PERMISSION_KINDS,
    KNOWN_PERMISSION_KINDS,
    MANIFEST_FILENAME,
    RUNTIME_PACK_SCHEMA_VERSION,
    RuntimeCapability,
    RuntimeEntrypoints,
    RuntimeIdentity,
    RuntimeIrDeclaration,
    RuntimeModelsDeclaration,
    RuntimePackManifest,
    RuntimePermission,
    RuntimeSearchDeclaration,
)


class TestConstants:
    def test_schema_version_is_int(self):
        assert isinstance(RUNTIME_PACK_SCHEMA_VERSION, int)
        assert RUNTIME_PACK_SCHEMA_VERSION == 1

    def test_manifest_filename(self):
        assert MANIFEST_FILENAME == "arc-runtime-pack.json"

    def test_known_permission_kinds_is_frozenset(self):
        assert isinstance(KNOWN_PERMISSION_KINDS, frozenset)
        assert "network" in KNOWN_PERMISSION_KINDS
        assert "paid_models" in KNOWN_PERMISSION_KINDS

    def test_dangerous_permission_kinds_subset(self):
        assert DANGEROUS_PERMISSION_KINDS <= KNOWN_PERMISSION_KINDS
        for dangerous in ("network", "paid_models", "secrets", "shell", "outside_workspace"):
            assert dangerous in DANGEROUS_PERMISSION_KINDS

    def test_background_not_dangerous(self):
        # background is a soft flag, not in the hard dangerous set
        assert "background" not in DANGEROUS_PERMISSION_KINDS


class TestRiskFlagsDefaultFalse:
    """All risk-bearing flags must default to False (fail-closed)."""

    def test_capability_defaults_false(self):
        cap = RuntimeCapability(name="test")
        for flag in (
            "network",
            "paid",
            "secrets",
            "shell",
            "mcp",
            "outside_workspace",
            "background",
            "replayable",
            "auditable",
        ):
            assert getattr(cap, flag) is False, f"{flag} should default to False"

    def test_models_declaration_default(self):
        m = RuntimeModelsDeclaration()
        assert m.requires_paid_models is False
        assert m.default_mode == "fake"

    def test_ir_declaration_defaults(self):
        ir = RuntimeIrDeclaration()
        assert ir.can_export_ir is False
        assert ir.supported_ir_version is None
        assert ir.opaque_node_policy is None

    def test_search_declaration_default(self):
        s = RuntimeSearchDeclaration()
        assert s.enabled is False
        assert s.network is False


class TestRuntimePackManifestCreation:
    def test_minimal_manifest_valid(self, minimal_manifest):
        m = minimal_manifest
        assert m.id == "acme.minimal-runtime"
        assert m.schema_version == RUNTIME_PACK_SCHEMA_VERSION
        assert m.manifest_hash is not None
        assert len(m.manifest_hash) == 64

    def test_extra_fields_ignored(self):
        """extra='ignore' must not crash on unknown keys."""
        data = {
            "schema_version": 1,
            "id": "test.runtime",
            "name": "Test",
            "runtime": {"runtime_name": "TestRuntime", "_future_field": "ignored"},
            "_unknown_root_key": "ignored",
        }
        m = RuntimePackManifest.model_validate(data)
        assert m.id == "test.runtime"

    def test_entrypoints_as_mapping_excludes_none(self):
        ep = RuntimeEntrypoints(inspect="my_pack.adapter:inspect", run=None)
        mapping = ep.as_mapping()
        assert "inspect" in mapping
        assert "run" not in mapping


class TestConvenienceAccessors:
    def test_permission_kinds_empty(self, minimal_manifest):
        assert minimal_manifest.permission_kinds() == set()

    def test_permission_kinds_collected(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            permissions=[
                RuntimePermission(kind="network", reason="tests"),
                RuntimePermission(kind="filesystem"),
            ],
        )
        kinds = m.permission_kinds()
        assert "network" in kinds
        assert "filesystem" in kinds

    def test_declares_paid_via_models(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            models=RuntimeModelsDeclaration(requires_paid_models=True),
        )
        assert m.declares_paid() is True

    def test_declares_paid_false_by_default(self, minimal_manifest):
        assert minimal_manifest.declares_paid() is False

    def test_declares_network_via_capability(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            capabilities=[RuntimeCapability(name="net_cap", network=True)],
        )
        assert m.declares_network() is True

    def test_declares_network_false_by_default(self, minimal_manifest):
        assert minimal_manifest.declares_network() is False

    def test_declares_network_via_search(self):
        m = RuntimePackManifest(
            id="x.y",
            name="X",
            runtime=RuntimeIdentity(runtime_name="X"),
            search=RuntimeSearchDeclaration(enabled=True, network=True),
        )
        assert m.declares_network() is True
