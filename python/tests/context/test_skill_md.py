"""Tests for SKILL.md catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.context.skill_md import discovery


@pytest.fixture
def skill_workspace(tmp_path: Path) -> Path:
    """Create a workspace with SKILL.md files."""
    skill1 = tmp_path / "tools" / "SKILL.md"
    skill1.parent.mkdir(parents=True)
    skill1.write_text(
        "---\nname: code-review\ndescription: Reviews code for quality\ntags:\n  - review\n---\n\n"
        "# Code Review Skill\n\nThis skill reviews code.\n"
    )

    skill2 = tmp_path / "agents" / "SKILL.md"
    skill2.parent.mkdir(parents=True)
    skill2.write_text(
        "---\nname: search\ndescription: Searches the codebase\n---\n\n# Search Skill\n"
    )

    # Excluded directory
    excluded = tmp_path / "node_modules" / "pkg" / "SKILL.md"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("---\nname: excluded\n---\n\nShould not appear.\n")

    return tmp_path


class TestSkillDiscovery:
    """Test SKILL.md discovery and parsing."""

    def test_discovers_skill_files(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        assert len(entries) == 2

    def test_excludes_node_modules(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        paths = [str(e.path.relative_to(skill_workspace)) for e in entries]
        assert not any("node_modules" in p for p in paths)

    def test_parses_frontmatter_name(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        names = {e.name for e in entries}
        assert "code-review" in names
        assert "search" in names

    def test_parses_frontmatter_description(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        desc_map = {e.name: e.description for e in entries}
        assert desc_map["code-review"] == "Reviews code for quality"

    def test_parses_frontmatter_tags(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        review_entry = next(e for e in entries if e.name == "code-review")
        assert review_entry.frontmatter.get("tags") == ["review"]

    def test_sha256_computed(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        for e in entries:
            assert len(e.sha256) == 64

    def test_body_excludes_frontmatter(self, skill_workspace: Path) -> None:
        entries = discovery(skill_workspace)
        review_entry = next(e for e in entries if e.name == "code-review")
        assert "---" not in review_entry.body
        assert "Code Review Skill" in review_entry.body

    def test_no_frontmatter_uses_dirname(self, tmp_path: Path) -> None:
        skill = tmp_path / "my-skill" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# No Frontmatter\n\nJust a body.\n")
        entries = discovery(tmp_path)
        assert len(entries) == 1
        assert entries[0].name == "my-skill"
        assert entries[0].frontmatter == {}

    def test_empty_workspace(self, tmp_path: Path) -> None:
        entries = discovery(tmp_path)
        assert entries == []
