"""Tests for ARC Policies — sandbox policy template library (R97, Phase 322)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agent_runtime_cockpit.security.policy_templates import (
    TEMPLATES_DIR,
    apply_template,
    list_templates,
    load_template,
    validate_template,
)


class TestPolicyTemplate:
    def test_load_data_science_template(self) -> None:
        template = load_template("data-science")
        assert template.id == "data-science"
        assert template.name == "Data Science Profile"
        assert template.category == "data-science"
        assert template.profile.allow_paid_calls is True
        assert template.profile.allow_network is True
        assert template.profile.allow_shell is False

    def test_load_open_source_template(self) -> None:
        template = load_template("open-source")
        assert template.id == "open-source"
        assert template.profile.allow_paid_calls is False
        assert template.profile.allow_network is False
        assert template.profile.allow_shell is False

    def test_load_regulated_industry_template(self) -> None:
        template = load_template("regulated-industry")
        assert template.id == "regulated-industry"
        assert template.category == "regulated"
        assert template.profile.allow_paid_calls is False
        assert template.profile.allow_network is False

    def test_load_development_template(self) -> None:
        template = load_template("development")
        assert template.id == "development"
        assert template.profile.allow_shell is True
        assert template.profile.allow_network is True

    def test_load_ci_cd_template(self) -> None:
        template = load_template("ci-cd")
        assert template.id == "ci-cd"
        assert template.profile.allow_shell is True
        assert template.profile.allow_network is True
        assert template.profile.allow_paid_calls is False

    def test_load_nonexistent_template(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent-template")

    def test_to_dict(self) -> None:
        template = load_template("data-science")
        d = template.to_dict()
        assert d["id"] == "data-science"
        assert d["name"] == "Data Science Profile"
        assert "profile" in d
        assert d["profile"]["allow_paid_calls"] is True

    def test_compliance_note(self) -> None:
        template = load_template("data-science")
        assert "aspirational" in template.compliance_note.lower()
        assert "not a certification" in template.compliance_note.lower()


class TestListTemplates:
    def test_list_all_templates(self) -> None:
        templates = list_templates()
        assert len(templates) >= 5
        ids = [t.id for t in templates]
        assert "data-science" in ids
        assert "open-source" in ids
        assert "regulated-industry" in ids
        assert "development" in ids
        assert "ci-cd" in ids

    def test_list_by_category(self) -> None:
        templates = list_templates(category="data-science")
        assert len(templates) >= 1
        assert all(t.category == "data-science" for t in templates)

    def test_list_by_nonexistent_category(self) -> None:
        templates = list_templates(category="nonexistent")
        assert len(templates) == 0


class TestValidateTemplate:
    def test_validate_data_science(self) -> None:
        result = validate_template("data-science")
        assert result["ok"] is True
        assert result["template_id"] == "data-science"

    def test_validate_open_source(self) -> None:
        result = validate_template("open-source")
        assert result["ok"] is True

    def test_validate_nonexistent(self) -> None:
        result = validate_template("nonexistent")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_validate_development_has_shell_warning(self) -> None:
        result = validate_template("development")
        assert result["ok"] is True
        issues = result["issues"]
        shell_issues = [i for i in issues if i["rule"] == "shell_without_secrets"]
        assert len(shell_issues) > 0


class TestApplyTemplate:
    def test_apply_template(self, tmp_path: Path) -> None:
        result = apply_template("data-science", tmp_path)
        assert result["ok"] is True
        assert result["template_id"] == "data-science"
        assert result["profile_id"] == "data-science"

        profile_file = Path(result["profile_file"])
        assert profile_file.exists()

        with open(profile_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["profile_id"] == "data-science"
        assert data["allow_paid_calls"] is True
        assert data["allow_network"] is True

    def test_apply_nonexistent_template(self, tmp_path: Path) -> None:
        result = apply_template("nonexistent", tmp_path)
        assert result["ok"] is False

    def test_apply_creates_arc_dir(self, tmp_path: Path) -> None:
        arc_dir = tmp_path / ".arc"
        assert not arc_dir.exists()
        apply_template("open-source", tmp_path)
        assert arc_dir.exists()


class TestTemplatesDirectory:
    def test_templates_dir_exists(self) -> None:
        assert TEMPLATES_DIR.exists()
        assert TEMPLATES_DIR.is_dir()

    def test_templates_are_valid_yaml(self) -> None:
        for template_file in TEMPLATES_DIR.glob("*.yaml"):
            with open(template_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict)
            assert "id" in data
            assert "name" in data
            assert "profile" in data


class TestPolicyTemplatesCLI:
    def test_template_list(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["policy", "template-list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["count"] >= 5

    def test_template_show(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["policy", "template-show", "data-science", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["id"] == "data-science"

    def test_template_show_nonexistent(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["policy", "template-show", "nonexistent", "--json"])
        assert result.exit_code == 1

    def test_template_validate(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["policy", "template-validate", "data-science", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_template_apply(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["policy", "template-apply", "open-source", "--json", "-w", str(tmp_path)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["template_id"] == "open-source"
