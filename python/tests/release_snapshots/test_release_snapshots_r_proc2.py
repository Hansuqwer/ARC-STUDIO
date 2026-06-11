"""Tests for ARC Release Snapshots — dated, locked, HEAD-derived markdown (R-PROC2, Phase 331)."""

from __future__ import annotations

from pathlib import Path
import json

from agent_runtime_cockpit.release_intelligence import CommitInfo, ReleaseIntelligence
from agent_runtime_cockpit.release_snapshots import (
    RELEASE_SNAPSHOTS_SCHEMA_VERSION,
    SnapshotError,
    generate_snapshot_filename,
    generate_snapshot_markdown,
    get_latest_snapshot,
    list_snapshots,
    save_snapshot,
)


class TestGenerateSnapshotFilename:
    def test_generate_filename(self) -> None:
        ri = ReleaseIntelligence(git_short="abc12345")
        filename = generate_snapshot_filename(ri)
        assert filename.endswith("-abc12345.md")
        assert len(filename) > 10

    def test_generate_filename_unknown_sha(self) -> None:
        ri = ReleaseIntelligence(git_short="")
        filename = generate_snapshot_filename(ri)
        assert filename.endswith("-unknown.md")


class TestGenerateSnapshotMarkdown:
    def test_generate_markdown_basic(self) -> None:
        ri = ReleaseIntelligence(
            version="1.0.0",
            git_commit="abc123def456",
            git_short="abc123de",
            git_branch="main",
            git_dirty=False,
            python_tests=5000,
            ruff_clean=True,
            banned_clean=True,
            total_commits=10,
            total_files_changed=50,
            total_insertions=1000,
            total_deletions=500,
        )
        md = generate_snapshot_markdown(ri)

        assert "# ARC Studio Release Snapshot" in md
        assert "**Version:** 1.0.0" in md
        assert "`abc123def456`" in md
        assert "**Git Branch:** main" in md
        assert "**Python Tests:** 5000" in md
        assert "**Ruff Clean:** True" in md
        assert "**Total Commits:** 10" in md

    def test_generate_markdown_with_commits(self) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        ri.commits_since_last_release = [
            CommitInfo(
                sha="commit1abc",
                short_sha="commit1a",
                author="Author 1",
                author_email="author1@test.com",
                date="2026-01-01 12:00:00",
                message="First commit",
            ),
            CommitInfo(
                sha="commit2def",
                short_sha="commit2d",
                author="Author 2",
                author_email="author2@test.com",
                date="2026-01-02 12:00:00",
                message="Second commit",
            ),
        ]
        md = generate_snapshot_markdown(ri)

        assert "| SHA | Author | Date | Message |" in md
        assert "commit1a" in md
        assert "Author 1" in md
        assert "First commit" in md
        assert "commit2d" in md
        assert "Author 2" in md

    def test_generate_markdown_no_commits(self) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        md = generate_snapshot_markdown(ri)
        assert "*No commits recorded.*" in md

    def test_generate_markdown_includes_schema_version(self) -> None:
        ri = ReleaseIntelligence()
        md = generate_snapshot_markdown(ri)
        assert f"**Schema Version:** {RELEASE_SNAPSHOTS_SCHEMA_VERSION}" in md

    def test_generate_markdown_includes_immutability_notice(self) -> None:
        ri = ReleaseIntelligence()
        md = generate_snapshot_markdown(ri)
        assert "This snapshot is immutable" in md


class TestSaveSnapshot:
    def test_save_snapshot(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(
            version="1.0.0",
            git_short="abc12345",
            git_branch="main",
        )
        output_dir = tmp_path / "snapshots"
        saved_path = save_snapshot(ri, output_dir)

        assert saved_path.exists()
        assert saved_path.name.endswith("-abc12345.md")
        assert output_dir.exists()

    def test_save_snapshot_custom_filename(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        output_dir = tmp_path / "snapshots"
        saved_path = save_snapshot(ri, output_dir, filename="custom-snapshot.md")

        assert saved_path.exists()
        assert saved_path.name == "custom-snapshot.md"

    def test_save_snapshot_immutability(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(version="1.0.0", git_short="abc12345")
        output_dir = tmp_path / "snapshots"

        # Save first snapshot
        path1 = save_snapshot(ri, output_dir)
        content1 = path1.read_text(encoding="utf-8")

        # Try to save again (should fail closed and not overwrite)
        ri.version = "2.0.0"
        try:
            save_snapshot(ri, output_dir)
        except SnapshotError:
            pass
        else:  # pragma: no cover - explicit failure path
            raise AssertionError("expected SnapshotError")
        content2 = path1.read_text(encoding="utf-8")

        assert content1 == content2
        assert "1.0.0" in content2
        assert "2.0.0" not in content2

    def test_save_snapshot_creates_parent_dirs(self, tmp_path: Path) -> None:
        ri = ReleaseIntelligence(version="1.0.0")
        output_dir = tmp_path / "subdir" / "nested" / "snapshots"
        saved_path = save_snapshot(ri, output_dir)
        assert saved_path.exists()
        assert output_dir.exists()


class TestListSnapshots:
    def test_list_snapshots_empty(self, tmp_path: Path) -> None:
        snapshot_dir = tmp_path / "snapshots"
        snapshots = list_snapshots(snapshot_dir)
        assert snapshots == []

    def test_list_snapshots_sorted(self, tmp_path: Path) -> None:
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        (snapshot_dir / "2026-01-01-abc123.md").write_text("old", encoding="utf-8")
        (snapshot_dir / "2026-01-02-def456.md").write_text("new", encoding="utf-8")
        (snapshot_dir / "2026-01-03-ghi789.md").write_text("newest", encoding="utf-8")

        snapshots = list_snapshots(snapshot_dir)
        assert len(snapshots) == 3
        assert snapshots[0].name == "2026-01-03-ghi789.md"
        assert snapshots[2].name == "2026-01-01-abc123.md"


class TestGetLatestSnapshot:
    def test_get_latest_snapshot(self, tmp_path: Path) -> None:
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()

        (snapshot_dir / "2026-01-01-abc123.md").write_text("old", encoding="utf-8")
        (snapshot_dir / "2026-01-02-def456.md").write_text("new", encoding="utf-8")

        latest = get_latest_snapshot(snapshot_dir)
        assert latest is not None
        assert latest.name == "2026-01-02-def456.md"

    def test_get_latest_snapshot_empty(self, tmp_path: Path) -> None:
        snapshot_dir = tmp_path / "snapshots"
        latest = get_latest_snapshot(snapshot_dir)
        assert latest is None


class TestReleaseSnapshotsCLI:
    def test_release_snapshots_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_release_snapshot_list_json(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        result = CliRunner().invoke(
            app, ["release", "snapshot", "list", "--json", "--snapshot-dir", str(tmp_path)]
        )
        data = json.loads(result.output)
        assert result.exit_code == 0
        assert data["ok"] is True
        assert data["data"]["state"] == "empty"

    def test_release_snapshot_create_json(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        out = tmp_path / "snapshots"
        result = CliRunner().invoke(
            app,
            [
                "release",
                "snapshot",
                "create",
                "--json",
                "--output-dir",
                str(out),
                "--filename",
                "test.md",
                "--workspace",
                str(tmp_path),
            ],
        )
        data = json.loads(result.output)
        assert result.exit_code == 0
        assert data["ok"] is True
        assert (out / "test.md").exists()
