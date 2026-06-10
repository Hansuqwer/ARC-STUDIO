"""Tests for ARC Hub — local-first config sharing (R91, Phase 316)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agent_runtime_cockpit.hub import (
    VALID_ITEM_TYPES,
    HubCatalog,
    HubError,
    HubInvalidType,
    compute_dir_sha256,
    compute_file_sha256,
    load_hub_item,
)


@pytest.fixture
def hub_dir(tmp_path: Path) -> Path:
    return tmp_path / ".arc_hub"


@pytest.fixture
def catalog(hub_dir: Path) -> HubCatalog:
    return HubCatalog(hub_dir)


@pytest.fixture
def sample_preset(tmp_path: Path) -> Path:
    p = tmp_path / "openai_preset.yaml"
    p.write_text(
        yaml.dump(
            {
                "id": "openai-gpt4",
                "name": "OpenAI GPT-4 Preset",
                "item_type": "provider-preset",
                "version": "1.0.0",
                "description": "GPT-4 provider configuration",
                "tags": ["openai", "gpt4"],
                "provider": "openai",
                "model": "gpt-4",
            }
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def sample_policy_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data_science_policy"
    d.mkdir()
    manifest = {
        "id": "ds-policy",
        "name": "Data Science Policy Template",
        "item_type": "policy-template",
        "version": "0.2.0",
        "description": "Policy for data science workflows",
        "tags": ["data-science", "policy"],
    }
    (d / "hub_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (d / "policy.yaml").write_text(
        yaml.dump({"allow_network": False, "allow_shell": True}), encoding="utf-8"
    )
    return d


class TestComputeSha256:
    def test_file_sha256_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world", encoding="utf-8")
        h1 = compute_file_sha256(f)
        h2 = compute_file_sha256(f)
        assert h1 == h2
        assert len(h1) == 64

    def test_file_sha256_changes_with_content(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        h1 = compute_file_sha256(f)
        f.write_text("world", encoding="utf-8")
        h2 = compute_file_sha256(f)
        assert h1 != h2

    def test_dir_sha256_deterministic(self, tmp_path: Path) -> None:
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a.txt").write_text("a", encoding="utf-8")
        (d / "b.txt").write_text("b", encoding="utf-8")
        h1 = compute_dir_sha256(d)
        h2 = compute_dir_sha256(d)
        assert h1 == h2


class TestLoadHubItem:
    def test_load_yaml_file(self, sample_preset: Path) -> None:
        item = load_hub_item(sample_preset)
        assert item.id == "openai-gpt4"
        assert item.item_type == "provider-preset"
        assert item.version == "1.0.0"
        assert len(item.sha256) == 64

    def test_load_directory_with_manifest(self, sample_policy_dir: Path) -> None:
        item = load_hub_item(sample_policy_dir)
        assert item.id == "ds-policy"
        assert item.item_type == "policy-template"
        assert item.version == "0.2.0"

    def test_invalid_type_rejected(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text(yaml.dump({"item_type": "invalid-type"}), encoding="utf-8")
        with pytest.raises(HubInvalidType):
            load_hub_item(p)

    def test_nonexistent_source_raises(self, tmp_path: Path) -> None:
        with pytest.raises(HubError):
            load_hub_item(tmp_path / "nonexistent.yaml")

    def test_valid_types(self) -> None:
        assert "provider-preset" in VALID_ITEM_TYPES
        assert "policy-template" in VALID_ITEM_TYPES
        assert "swarm-def" in VALID_ITEM_TYPES
        assert "eval-suite" in VALID_ITEM_TYPES
        assert "theme" in VALID_ITEM_TYPES


class TestHubCatalog:
    def test_list_empty(self, catalog: HubCatalog) -> None:
        items = catalog.list_items()
        assert items == []

    def test_add_and_list(self, catalog: HubCatalog, sample_preset: Path) -> None:
        item = catalog.add(sample_preset)
        assert item.id == "openai-gpt4"
        assert item.installed_at is not None
        items = catalog.list_items()
        assert len(items) == 1
        assert items[0].id == "openai-gpt4"

    def test_add_duplicate_without_force_raises(
        self, catalog: HubCatalog, sample_preset: Path
    ) -> None:
        catalog.add(sample_preset)
        with pytest.raises(HubError, match="already installed"):
            catalog.add(sample_preset)

    def test_add_duplicate_with_force(self, catalog: HubCatalog, sample_preset: Path) -> None:
        catalog.add(sample_preset)
        item = catalog.add(sample_preset, force=True)
        assert item.id == "openai-gpt4"

    def test_add_directory(self, catalog: HubCatalog, sample_policy_dir: Path) -> None:
        item = catalog.add(sample_policy_dir)
        assert item.id == "ds-policy"
        assert item.item_type == "policy-template"

    def test_remove(self, catalog: HubCatalog, sample_preset: Path) -> None:
        catalog.add(sample_preset)
        catalog.remove("openai-gpt4")
        assert catalog.list_items() == []

    def test_remove_nonexistent_raises(self, catalog: HubCatalog) -> None:
        with pytest.raises(HubError, match="not found"):
            catalog.remove("nonexistent")

    def test_verify_ok(self, catalog: HubCatalog, sample_preset: Path) -> None:
        catalog.add(sample_preset)
        result = catalog.verify("openai-gpt4")
        assert result["ok"] is True
        assert result["reason"] is None

    def test_verify_missing_files(self, catalog: HubCatalog, sample_preset: Path) -> None:
        catalog.add(sample_preset)
        import shutil

        shutil.rmtree(catalog._hub_dir / "openai-gpt4")
        result = catalog.verify("openai-gpt4")
        assert result["ok"] is False
        assert result["reason"] == "installed_files_missing"

    def test_verify_nonexistent_raises(self, catalog: HubCatalog) -> None:
        with pytest.raises(HubError, match="not found"):
            catalog.verify("nonexistent")

    def test_get(self, catalog: HubCatalog, sample_preset: Path) -> None:
        catalog.add(sample_preset)
        item = catalog.get("openai-gpt4")
        assert item.id == "openai-gpt4"
        assert item.name == "OpenAI GPT-4 Preset"

    def test_get_nonexistent_raises(self, catalog: HubCatalog) -> None:
        with pytest.raises(HubError, match="not found"):
            catalog.get("nonexistent")

    def test_list_filter_by_type(
        self, catalog: HubCatalog, sample_preset: Path, sample_policy_dir: Path
    ) -> None:
        catalog.add(sample_preset)
        catalog.add(sample_policy_dir)
        presets = catalog.list_items(item_type="provider-preset")
        assert len(presets) == 1
        assert presets[0].item_type == "provider-preset"
        policies = catalog.list_items(item_type="policy-template")
        assert len(policies) == 1
        assert policies[0].item_type == "policy-template"


class TestHubCLI:
    def test_hub_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["hub", "--help"])
        assert result.exit_code == 0
        assert "hub" in result.output.lower()

    def test_hub_list_empty(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["hub", "list", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] == 0

    def test_hub_add_and_list(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        preset = tmp_path / "preset.yaml"
        preset.write_text(
            yaml.dump(
                {
                    "id": "test-preset",
                    "name": "Test Preset",
                    "item_type": "provider-preset",
                    "version": "1.0.0",
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(app, ["hub", "add", str(preset), "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["id"] == "test-preset"

        result = runner.invoke(app, ["hub", "list", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["count"] == 1

    def test_hub_verify(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        preset = tmp_path / "preset.yaml"
        preset.write_text(
            yaml.dump(
                {
                    "id": "verify-test",
                    "name": "Verify Test",
                    "item_type": "provider-preset",
                    "version": "1.0.0",
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        runner.invoke(app, ["hub", "add", str(preset), "--json", "-w", str(tmp_path)])
        result = runner.invoke(app, ["hub", "verify", "verify-test", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_hub_remove(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        preset = tmp_path / "preset.yaml"
        preset.write_text(
            yaml.dump(
                {
                    "id": "remove-test",
                    "name": "Remove Test",
                    "item_type": "provider-preset",
                    "version": "1.0.0",
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        runner.invoke(app, ["hub", "add", str(preset), "--json", "-w", str(tmp_path)])
        result = runner.invoke(app, ["hub", "remove", "remove-test", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_hub_inspect(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        preset = tmp_path / "preset.yaml"
        preset.write_text(
            yaml.dump(
                {
                    "id": "inspect-test",
                    "name": "Inspect Test",
                    "item_type": "provider-preset",
                    "version": "1.0.0",
                    "description": "A test preset",
                }
            ),
            encoding="utf-8",
        )

        runner = CliRunner()
        runner.invoke(app, ["hub", "add", str(preset), "--json", "-w", str(tmp_path)])
        result = runner.invoke(
            app, ["hub", "inspect", "inspect-test", "--json", "-w", str(tmp_path)]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["id"] == "inspect-test"
        assert data["data"]["description"] == "A test preset"
