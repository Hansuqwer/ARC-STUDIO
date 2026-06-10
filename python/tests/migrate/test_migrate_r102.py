"""Tests for ARC Migrate — cross-adapter migration assistant (R102, Phase 327)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.migrate import (
    FrameworkType,
    MigrationAnalysis,
    MigrationIssue,
    MigrationStatus,
    analyze_migration,
    detect_framework,
    generate_migration,
    migrate_workspace,
    validate_migration,
)


class TestFrameworkType:
    def test_framework_values(self) -> None:
        assert FrameworkType.LANGGRAPH.value == "langgraph"
        assert FrameworkType.CREWAI.value == "crewai"
        assert FrameworkType.SWARMGRAPH.value == "swarmgraph"
        assert FrameworkType.OPENAI_AGENTS.value == "openai_agents"
        assert FrameworkType.UNKNOWN.value == "unknown"


class TestMigrationIssue:
    def test_create_issue(self) -> None:
        issue = MigrationIssue(
            issue_type="incompatible_feature",
            severity="warning",
            message="Feature X not supported in target",
        )
        assert issue.issue_type == "incompatible_feature"
        assert issue.severity == "warning"

    def test_issue_to_dict(self) -> None:
        issue = MigrationIssue(
            issue_type="missing_mapping",
            severity="error",
            message="No mapping for class Y",
            source_location="file.py:10",
            suggestion="Use class Z instead",
        )
        d = issue.to_dict()
        assert d["issue_type"] == "missing_mapping"
        assert d["severity"] == "error"
        assert d["suggestion"] == "Use class Z instead"


class TestMigrationAnalysis:
    def test_create_analysis(self) -> None:
        analysis = MigrationAnalysis(
            source_framework=FrameworkType.LANGGRAPH,
            target_framework=FrameworkType.CREWAI,
        )
        assert analysis.source_framework == FrameworkType.LANGGRAPH
        assert analysis.target_framework == FrameworkType.CREWAI
        assert analysis.compatibility_score == 0.0

    def test_analysis_to_dict(self) -> None:
        analysis = MigrationAnalysis(
            source_framework=FrameworkType.LANGGRAPH,
            target_framework=FrameworkType.CREWAI,
            source_files=["main.py"],
            detected_patterns=["import:langgraph"],
            compatibility_score=0.8,
            estimated_effort="low",
        )
        d = analysis.to_dict()
        assert d["source_framework"] == "langgraph"
        assert d["target_framework"] == "crewai"
        assert d["compatibility_score"] == 0.8
        assert len(d["source_files"]) == 1


class TestDetectFramework:
    def test_detect_langgraph(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text(
            "from langgraph.graph import StateGraph", encoding="utf-8"
        )
        framework = detect_framework(tmp_path)
        assert framework == FrameworkType.LANGGRAPH

    def test_detect_crewai(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("from crewai import Crew", encoding="utf-8")
        framework = detect_framework(tmp_path)
        assert framework == FrameworkType.CREWAI

    def test_detect_swarmgraph(self, tmp_path: Path) -> None:
        (tmp_path / "swarmgraph.yaml").write_text("name: test", encoding="utf-8")
        framework = detect_framework(tmp_path)
        assert framework == FrameworkType.SWARMGRAPH

    def test_detect_unknown(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        framework = detect_framework(tmp_path)
        assert framework == FrameworkType.UNKNOWN


class TestAnalyzeMigration:
    def test_analyze_same_framework(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text(
            "from langgraph.graph import StateGraph", encoding="utf-8"
        )
        analysis = analyze_migration(tmp_path, FrameworkType.LANGGRAPH, FrameworkType.LANGGRAPH)
        assert analysis.compatibility_score == 1.0
        assert analysis.estimated_effort == "low"

    def test_analyze_different_frameworks(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text(
            "from langgraph.graph import StateGraph", encoding="utf-8"
        )
        analysis = analyze_migration(tmp_path, FrameworkType.LANGGRAPH, FrameworkType.CREWAI)
        assert analysis.compatibility_score > 0.0
        assert len(analysis.source_files) > 0

    def test_analyze_unknown_framework(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        analysis = analyze_migration(tmp_path, FrameworkType.UNKNOWN, FrameworkType.LANGGRAPH)
        assert analysis.compatibility_score < 0.5
        assert any(i.issue_type == "unknown_framework" for i in analysis.issues)


class TestGenerateMigration:
    def test_generate_langgraph_to_crewai(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("from langgraph.graph import StateGraph", encoding="utf-8")

        output = tmp_path / "output"
        analysis = MigrationAnalysis(
            source_framework=FrameworkType.LANGGRAPH,
            target_framework=FrameworkType.CREWAI,
            source_files=["main.py"],
        )

        generated = generate_migration(source, output, analysis)
        assert len(generated) == 1
        content = (output / "main.py").read_text(encoding="utf-8")
        assert "from crewai" in content
        assert "from langgraph" not in content

    def test_generate_crewai_to_langgraph(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("from crewai import Crew", encoding="utf-8")

        output = tmp_path / "output"
        analysis = MigrationAnalysis(
            source_framework=FrameworkType.CREWAI,
            target_framework=FrameworkType.LANGGRAPH,
            source_files=["main.py"],
        )

        generated = generate_migration(source, output, analysis)
        assert len(generated) == 1
        content = (output / "main.py").read_text(encoding="utf-8")
        assert "from langgraph" in content


class TestValidateMigration:
    def test_validate_success(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("x = 1", encoding="utf-8")

        output = tmp_path / "output"
        output.mkdir()
        (output / "main.py").write_text("x = 1", encoding="utf-8")

        analysis = MigrationAnalysis(
            source_framework=FrameworkType.LANGGRAPH,
            target_framework=FrameworkType.CREWAI,
            source_files=["main.py"],
        )

        report = validate_migration(source, output, analysis)
        assert report["validation_passed"] is True
        assert report["parse_errors"] == 0

    def test_validate_syntax_error(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("x = 1", encoding="utf-8")

        output = tmp_path / "output"
        output.mkdir()
        (output / "main.py").write_text("x = ", encoding="utf-8")

        analysis = MigrationAnalysis(
            source_framework=FrameworkType.LANGGRAPH,
            target_framework=FrameworkType.CREWAI,
            source_files=["main.py"],
        )

        report = validate_migration(source, output, analysis)
        assert report["validation_passed"] is False
        assert report["parse_errors"] > 0


class TestMigrateWorkspace:
    def test_migrate_full_workflow(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("from langgraph.graph import StateGraph", encoding="utf-8")

        output = tmp_path / "output"
        result = migrate_workspace(source, output, FrameworkType.CREWAI, "test-session")

        assert result.session_id == "test-session"
        assert result.status == MigrationStatus.COMPLETED
        assert result.source_framework == FrameworkType.LANGGRAPH
        assert result.target_framework == FrameworkType.CREWAI
        assert len(result.generated_files) > 0
        assert result.completed_at is not None

    def test_migrate_to_dict(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("from langgraph.graph import StateGraph", encoding="utf-8")

        output = tmp_path / "output"
        result = migrate_workspace(source, output, FrameworkType.CREWAI)

        d = result.to_dict()
        assert d["session_id"] == result.session_id
        assert d["status"] == "completed"
        assert d["source_framework"] == "langgraph"
        assert d["target_framework"] == "crewai"


class TestMigrateCLI:
    def test_migrate_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "migrate" in result.output.lower()

    def test_migrate_detect(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        (tmp_path / "main.py").write_text(
            "from langgraph.graph import StateGraph", encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["migrate", "detect", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["framework"] == "langgraph"

    def test_migrate_analyze(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        (tmp_path / "main.py").write_text(
            "from langgraph.graph import StateGraph", encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["migrate", "analyze", "crewai", "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["source_framework"] == "langgraph"
        assert data["data"]["target_framework"] == "crewai"

    def test_migrate_run(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("from langgraph.graph import StateGraph", encoding="utf-8")

        output = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "migrate",
                "run",
                "crewai",
                "--output",
                str(output),
                "--source",
                str(source),
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["status"] == "completed"

    def test_migrate_validate(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("x = 1", encoding="utf-8")

        output = tmp_path / "output"
        output.mkdir()
        (output / "main.py").write_text("x = 1", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "migrate",
                "validate",
                str(output),
                "--source",
                str(source),
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["validation_passed"] is True
