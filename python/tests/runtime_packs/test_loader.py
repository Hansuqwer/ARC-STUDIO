"""Tests for manifest loading and inspection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.runtime_packs import (
    MANIFEST_FILENAME,
    ManifestLoadError,
    RuntimeIdentity,
    RuntimeMcpDeclaration,
    RuntimeModelsDeclaration,
    RuntimePackManifest,
    RuntimePermission,
    find_manifest,
    inspect_manifest,
    load_manifest,
    load_manifest_dict,
    manifest_hash,
)


class TestFindManifest:
    def test_finds_manifest_in_dir(self, manifest_file: Path):
        found = find_manifest(manifest_file.parent)
        assert found == manifest_file

    def test_finds_manifest_at_file_path(self, manifest_file: Path):
        found = find_manifest(manifest_file)
        assert found == manifest_file

    def test_raises_for_missing_manifest(self, tmp_path: Path):
        with pytest.raises(ManifestLoadError, match="No arc-runtime-pack.json"):
            find_manifest(tmp_path)


class TestLoadManifestDict:
    def test_load_dict_from_file(self, manifest_file: Path):
        data = load_manifest_dict(manifest_file)
        assert isinstance(data, dict)
        assert data["id"] == "acme.minimal-runtime"

    def test_load_dict_from_dir(self, manifest_file: Path):
        data = load_manifest_dict(manifest_file.parent)
        assert data["id"] == "acme.minimal-runtime"

    def test_raises_for_invalid_json(self, tmp_path: Path):
        bad = tmp_path / MANIFEST_FILENAME
        bad.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ManifestLoadError):
            load_manifest_dict(bad)


class TestLoadManifest:
    def test_load_returns_manifest_model(self, manifest_file: Path):
        m = load_manifest(manifest_file)
        assert isinstance(m, RuntimePackManifest)
        assert m.id == "acme.minimal-runtime"

    def test_load_from_directory(self, manifest_file: Path):
        m = load_manifest(manifest_file.parent)
        assert m.id == "acme.minimal-runtime"

    def test_load_unknown_schema_version_raises(self, tmp_path: Path):
        data = {
            "schema_version": 9999,
            "id": "future.runtime",
            "name": "Future",
            "runtime": {"runtime_name": "Future"},
        }
        p = tmp_path / MANIFEST_FILENAME
        p.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ManifestLoadError, match="Unsupported schema_version"):
            load_manifest(p)


class TestInspectManifest:
    def test_inspect_minimal_manifest(self, manifest_file: Path):
        m = load_manifest(manifest_file)
        surface = inspect_manifest(m)
        assert surface["security_surface"]["can_call_paid_models"] is False
        assert surface["security_surface"]["can_access_network"] is False
        assert surface["security_surface"]["can_run_shell"] is False
        assert surface["security_surface"]["can_call_mcp"] is False
        assert "permissions" in surface
        assert "capabilities" in surface

    def test_inspect_ir_manifest(self, ir_manifest: RuntimePackManifest, tmp_path: Path):
        surface = inspect_manifest(ir_manifest)
        assert surface["ir"]["can_export_ir"] is True
        assert surface["ir"]["supported_ir_version"] == 1

    def test_inspect_paid_manifest(self, tmp_path: Path):
        m = RuntimePackManifest(
            id="x.paid",
            name="Paid",
            runtime=RuntimeIdentity(runtime_name="Paid"),
            models=RuntimeModelsDeclaration(requires_paid_models=True),
            permissions=[RuntimePermission(kind="paid_models", reason="LLM inference")],
        )
        m.manifest_hash = manifest_hash(m)
        surface = inspect_manifest(m)
        assert surface["security_surface"]["can_call_paid_models"] is True

    def test_inspect_mcp_manifest(self, tmp_path: Path):
        m = RuntimePackManifest(
            id="x.mcp",
            name="MCP",
            runtime=RuntimeIdentity(runtime_name="MCP"),
            mcp=[RuntimeMcpDeclaration(server_id="my-server", required=False)],
        )
        m.manifest_hash = manifest_hash(m)
        surface = inspect_manifest(m)
        assert surface["security_surface"]["can_call_mcp"] is True
        assert "mcp" in surface
