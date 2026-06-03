"""Tests for the Runtime Pack registry: install, list, get, drift, uninstall."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.runtime_packs import (
    MANIFEST_FILENAME,
    RuntimeIdentity,
    RuntimePackInstallError,
    RuntimePackManifest,
    create_registry,
    manifest_hash,
)


class TestRegistryInstall:
    def test_install_minimal_pack(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        entry = reg.install(manifest_file)
        assert entry.id == "acme.minimal-runtime"
        assert len(entry.manifest_hash) == 64

    def test_installed_pack_appears_in_list(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        ids = [e.id for e in reg.list_packs()]
        assert "acme.minimal-runtime" in ids

    def test_install_persists_to_disk(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        # Re-create registry from disk and check entry is still there
        reg2 = create_registry(workspace=workspace_dir)
        assert reg2.get_pack("acme.minimal-runtime") is not None

    def test_install_copies_manifest_metadata_only(self, manifest_file: Path, workspace_dir: Path):
        """Install must copy manifest JSON only, never execute or import pack code."""
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        # The registry dir contains only JSON metadata
        registry_root = workspace_dir / ".arc" / "runtime-packs"
        for f in registry_root.rglob("*"):
            if f.is_file():
                assert f.suffix in (".json",), f"Unexpected file type in registry: {f}"

    def test_install_refuses_invalid_manifest(self, tmp_path: Path, workspace_dir: Path):
        """Validation failure must raise RuntimePackInstallError."""
        # A manifest with a wrong schema_version
        bad_manifest = {
            "schema_version": 999,
            "id": "bad.runtime",
            "name": "Bad",
            "runtime": {"runtime_name": "Bad"},
        }
        p = tmp_path / MANIFEST_FILENAME
        p.write_text(json.dumps(bad_manifest), encoding="utf-8")
        reg = create_registry(workspace=workspace_dir)
        with pytest.raises(RuntimePackInstallError):
            reg.install(p)

    def test_install_duplicate_raises_without_force(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        with pytest.raises(RuntimePackInstallError):
            reg.install(manifest_file)

    def test_install_duplicate_ok_with_force(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        entry = reg.install(manifest_file, force=True)
        assert entry.id == "acme.minimal-runtime"


class TestRegistryGet:
    def test_get_returns_entry(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        entry = reg.get_pack("acme.minimal-runtime")
        assert entry is not None
        assert entry.id == "acme.minimal-runtime"

    def test_get_unknown_returns_none(self, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        assert reg.get_pack("does.not.exist") is None


class TestRegistryDrift:
    def test_no_drift_fresh_install(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        drift = reg.check_drift("acme.minimal-runtime")
        assert drift["installed"] is True
        assert drift["drifted"] is False

    def test_drift_detected_after_installed_file_change(self, tmp_path: Path, workspace_dir: Path):
        m = RuntimePackManifest(
            id="acme.drift-test",
            name="Drift Test",
            runtime=RuntimeIdentity(runtime_name="Drifter"),
        )
        m.manifest_hash = manifest_hash(m)
        mp = tmp_path / MANIFEST_FILENAME
        mp.write_text(json.dumps(m.model_dump(mode="json"), indent=2), encoding="utf-8")

        reg = create_registry(workspace=workspace_dir)
        reg.install(mp)

        # Mutate the INSTALLED manifest (simulates tampering with the registry copy).
        installed_path = (
            workspace_dir
            / ".arc"
            / "runtime-packs"
            / "packs"
            / "acme.drift-test"
            / MANIFEST_FILENAME
        )
        data = json.loads(installed_path.read_text())
        data["name"] = "TAMPERED"
        # Hash in stored file differs from name change → drift
        data["manifest_hash"] = "c" * 64
        installed_path.write_text(json.dumps(data), encoding="utf-8")

        drift = reg.check_drift("acme.drift-test")
        assert drift["installed"] is True
        assert drift["drifted"] is True

    def test_drift_unknown_pack(self, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        drift = reg.check_drift("not.installed")
        assert drift["installed"] is False


class TestRegistryUninstall:
    def test_uninstall_removes_pack(self, manifest_file: Path, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        reg.install(manifest_file)
        reg.uninstall("acme.minimal-runtime")
        assert reg.get_pack("acme.minimal-runtime") is None
        assert "acme.minimal-runtime" not in [e.id for e in reg.list_packs()]

    def test_uninstall_unknown_pack_raises(self, workspace_dir: Path):
        reg = create_registry(workspace=workspace_dir)
        with pytest.raises(RuntimePackInstallError, match="not installed"):
            reg.uninstall("does.not.exist")
