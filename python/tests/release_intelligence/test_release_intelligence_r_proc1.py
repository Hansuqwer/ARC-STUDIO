"""Tests for ARC Release Intelligence — auto-generate release intelligence from CI (R-PROC1, Phase 330)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.release_intelligence import (
    RELEASE_INTELLIGENCE_SCHEMA_VERSION,
    CommitInfo,
    ReleaseIntelligence,
    generate_release_intelligence,
    load_release_intelligence,
    save_release_intelligence,
)


class TestCommitInfo:
    def test_create_commit_info(self) -> None:
        commit = CommitInfo(
            sha="abc123def456",
            short_sha="abc123de",
            author="Test Author",
            author_email="test@example.com",
            date="2026-01-01 12:00:00",
            message="Test commit",
        )
        assert commit.sha == "abc123def456"
        assert commit.short_sha == "abc123de"
        assert commit.author == "Test Author"

    def test_commit_info_to_dict(self) -> None:
        commit = CommitInfo(
            sha="abc123",
            short_sha="abc123",
            author="Author",
            author_email="author@test.com",
            date="2026-01-01",
            message="Message",
            files_changed=5,
            insertions=100,
            deletions=50,
        )
        d = commit.to_dict()
        assert d["sha"] == "abc123"
        assert d["files_changed"] == 5
        assert d["insertions"] == 100
        assert d["deletions"] == 50


class TestReleaseIntelligence:
    def test_create_release_intelligence(self) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        assert ri.version == "1.0.0"
        assert ri.schema_version == RELEASE_INTELLIGENCE_SCHEMA_VERSION
        assert ri.total_commits == 0

    def test_release_intelligence_to_dict(self) -> None:
        ri = ReleaseIntelligence(
            version="2.0.0",
            git_commit="abc123",
            git_short="abc123",
            git_branch="main",
            git_dirty=False,
            total_commits=10,
            total_files_changed=50,
            total_insertions=1000,
            total_deletions=500,
            python_tests=5000,
            ruff_clean=True,
            banned_clean=True,
        )
        d = ri.to_dict()
        assert d["version"] == "2.0.0"
        assert d["git_branch"] == "main"
        assert d["total_commits"] == 10
        assert d["python_tests"] == 5000
        assert d["ruff_clean"] is True

    def test_release_intelligence_to_json(self) -> None:
        ri = ReleaseIntelligence(version="1.0.0", git_branch="main")
        j = ri.to_json()
        data = json.loads(j)
        assert data["version"] == "1.0.0"
        assert data["git_branch"] == "main"


class TestGenerateReleaseIntelligence:
    def test_generate_from_current_repo(self) -> None:
        repo_path = Path.cwd()
        ri = generate_release_intelligence(repo_path, version="test-version", max_commits=10)

        assert ri.schema_version == RELEASE_INTELLIGENCE_SCHEMA_VERSION
        assert ri.version == "test-version"
        assert ri.git_commit != ""
        assert ri.git_branch != ""
        assert ri.total_commits <= 10

    def test_generate_with_since(self) -> None:
        repo_path = Path.cwd()
        ri = generate_release_intelligence(
            repo_path, version="test", since="2020-01-01", max_commits=5
        )
        assert ri.total_commits <= 5


class TestSaveLoadReleaseIntelligence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(
            version="1.0.0",
            git_commit="abc123",
            git_branch="main",
            total_commits=5,
            python_tests=1000,
        )
        ri.commits_since_last_release = [
            CommitInfo(
                sha="commit1",
                short_sha="commit1",
                author="Author",
                author_email="author@test.com",
                date="2026-01-01",
                message="Test commit",
            )
        ]

        output_path = tmp_path / "release.json"
        save_release_intelligence(ri, output_path)
        assert output_path.exists()

        loaded = load_release_intelligence(output_path)
        assert loaded.version == "1.0.0"
        assert loaded.git_commit == "abc123"
        assert loaded.total_commits == 5
        assert len(loaded.commits_since_last_release) == 1
        assert loaded.commits_since_last_release[0].sha == "commit1"

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        output_path = tmp_path / "subdir" / "nested" / "release.json"
        save_release_intelligence(ri, output_path)
        assert output_path.exists()


class TestReleaseIntelligenceCLI:
    def test_release_intelligence_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
