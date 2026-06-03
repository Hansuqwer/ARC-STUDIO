"""Tests for runtime pack scaffolding (init_pack / build_scaffold_manifest)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.runtime_packs import (
    MANIFEST_FILENAME,
    ScaffoldError,
    build_scaffold_manifest,
    init_pack,
    validate_manifest,
    verify_manifest_hash,
)


class TestBuildScaffoldManifest:
    def test_manifest_is_valid(self):
        m = build_scaffold_manifest("org.my-runtime", "My Runtime")
        rep = validate_manifest(m)
        assert rep.ok is True

    def test_manifest_is_hash_pinned(self):
        m = build_scaffold_manifest("org.my-runtime", "My Runtime")
        assert m.manifest_hash is not None
        assert verify_manifest_hash(m, m.manifest_hash) is True

    def test_manifest_id_and_name_set(self):
        m = build_scaffold_manifest("org.my-runtime", "My Runtime")
        assert m.id == "org.my-runtime"
        assert m.name == "My Runtime"

    def test_scaffold_is_fail_closed(self):
        m = build_scaffold_manifest("org.safe", "Safe")
        # All risk flags must be false (fail-closed defaults)
        for cap in m.capabilities:
            for flag in ("network", "paid", "secrets", "shell", "mcp", "outside_workspace"):
                assert getattr(cap, flag) is False

    def test_no_secrets_in_scaffold(self):
        from agent_runtime_cockpit.runtime_packs import is_safe_manifest

        m = build_scaffold_manifest("org.clean", "Clean")
        assert is_safe_manifest(m) is True


class TestInitPack:
    def test_creates_expected_files(self, tmp_pack_dir: Path):
        created = init_pack(tmp_pack_dir, pack_id="org.test", name="Test Runtime")
        names = {p.name for p in created}
        assert MANIFEST_FILENAME in names
        assert "README.md" in names
        assert "minimal.workflow.json" in names

    def test_manifest_file_is_valid_json(self, tmp_pack_dir: Path):
        init_pack(tmp_pack_dir, pack_id="org.test", name="Test")
        manifest_path = tmp_pack_dir / MANIFEST_FILENAME
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["id"] == "org.test"
        assert data["schema_version"] == 1

    def test_manifest_file_passes_validation(self, tmp_pack_dir: Path):
        init_pack(tmp_pack_dir, pack_id="org.test", name="Test")
        from agent_runtime_cockpit.runtime_packs import load_manifest

        m = load_manifest(tmp_pack_dir)
        rep = validate_manifest(m)
        assert rep.ok is True

    def test_example_workflow_created(self, tmp_pack_dir: Path):
        init_pack(tmp_pack_dir, pack_id="org.test", name="Test")
        example = tmp_pack_dir / "examples" / "minimal.workflow.json"
        assert example.exists()
        data = json.loads(example.read_text())
        assert "nodes" in data

    def test_raises_if_manifest_exists_without_force(self, tmp_pack_dir: Path):
        init_pack(tmp_pack_dir, pack_id="org.test", name="First")
        with pytest.raises(ScaffoldError):
            init_pack(tmp_pack_dir, pack_id="org.test", name="Second")

    def test_force_overwrites_existing(self, tmp_pack_dir: Path):
        init_pack(tmp_pack_dir, pack_id="org.first", name="First")
        init_pack(tmp_pack_dir, pack_id="org.second", name="Second", force=True)
        data = json.loads((tmp_pack_dir / MANIFEST_FILENAME).read_text())
        assert data["id"] == "org.second"

    def test_target_dir_created_if_missing(self, tmp_path: Path):
        new_dir = tmp_path / "brand" / "new" / "dir"
        assert not new_dir.exists()
        init_pack(new_dir, pack_id="org.new", name="New")
        assert (new_dir / MANIFEST_FILENAME).exists()
