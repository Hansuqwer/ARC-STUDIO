"""Tests for AGENTS.md workspace ingestion."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.context.agents_md import (
    SIZE_CAP_BYTES,
    check_drift,
    discovery,
    is_likely_llm_generated,
    nearest_for,
    pin,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "agents_md" / "root"


class TestDiscovery:
    """Test AGENTS.md discovery."""

    def test_discovers_root_agents_md(self) -> None:
        entries = discovery(FIXTURES)
        paths = [str(e.path.relative_to(FIXTURES)) for e in entries if not e.is_override]
        assert "AGENTS.md" in paths

    def test_discovers_nested(self) -> None:
        entries = discovery(FIXTURES)
        paths = [str(e.path.relative_to(FIXTURES)) for e in entries]
        assert any("sub_a/AGENTS.md" in p for p in paths)
        assert any("sub_a/deep/AGENTS.md" in p for p in paths)

    def test_excludes_node_modules(self) -> None:
        entries = discovery(FIXTURES)
        paths = [str(e.path.relative_to(FIXTURES)) for e in entries]
        assert not any("node_modules" in p for p in paths)

    def test_discovers_override(self) -> None:
        entries = discovery(FIXTURES)
        overrides = [e for e in entries if e.is_override]
        assert len(overrides) >= 1
        assert overrides[0].is_override is True

    def test_over_cap_flagged(self) -> None:
        entries = discovery(FIXTURES)
        over_cap = [e for e in entries if e.over_cap]
        assert len(over_cap) >= 1
        assert over_cap[0].size_bytes > SIZE_CAP_BYTES

    def test_sorted_by_depth(self) -> None:
        entries = discovery(FIXTURES)
        depths = [len(e.path.relative_to(FIXTURES).parts) for e in entries]
        assert depths == sorted(depths)

    def test_sha256_is_hex(self) -> None:
        entries = discovery(FIXTURES)
        for e in entries:
            assert len(e.sha256) == 64
            int(e.sha256, 16)  # raises if not hex


class TestLLMHeuristic:
    """Test LLM-generated detection heuristic."""

    def test_llm_generated_detected(self) -> None:
        entries = discovery(FIXTURES)
        llm_entries = [e for e in entries if "llm_generated" in str(e.path) and not e.is_override]
        assert len(llm_entries) == 1
        assert llm_entries[0].likely_llm_generated is True

    def test_hand_written_not_flagged(self) -> None:
        entries = discovery(FIXTURES)
        hand = [e for e in entries if "hand_written" in str(e.path) and not e.is_override]
        assert len(hand) == 1
        assert hand[0].likely_llm_generated is False

    def test_heuristic_deterministic(self) -> None:
        text = "Ensure you do this. Make sure to do that. Always follow rules."
        r1 = is_likely_llm_generated(text, "myproject")
        r2 = is_likely_llm_generated(text, "myproject")
        assert r1 == r2

    def test_empty_text_not_llm(self) -> None:
        assert is_likely_llm_generated("", "project") is False

    def test_project_name_present_reduces_signal(self) -> None:
        # Text with project name has one less signal
        text = "myproject uses this pattern. Short text."
        assert is_likely_llm_generated(text, "myproject") is False


class TestNearestFor:
    """Test nearest-wins resolution."""

    def test_deep_file_finds_deep_agents(self) -> None:
        target = FIXTURES / "sub_a" / "deep" / "somefile.py"
        entry = nearest_for(target, FIXTURES)
        assert entry is not None
        assert "deep" in str(entry.path)

    def test_sub_a_file_finds_sub_a_agents(self) -> None:
        target = FIXTURES / "sub_a" / "module.py"
        entry = nearest_for(target, FIXTURES)
        assert entry is not None
        assert "sub_a" in str(entry.path)
        assert "deep" not in str(entry.path)

    def test_root_file_finds_override(self) -> None:
        """Override takes priority at same level."""
        target = FIXTURES / "somefile.py"
        entry = nearest_for(target, FIXTURES)
        assert entry is not None
        assert entry.is_override is True

    def test_nonexistent_path_outside_workspace(self) -> None:
        target = Path("/tmp/completely/elsewhere/file.py")
        entry = nearest_for(target, FIXTURES)
        assert entry is None


class TestPin:
    """Test pinning to .arc/agents-md/index.json."""

    def test_pin_creates_index(self, tmp_path: Path) -> None:
        # Copy a simple agents.md to tmp
        agents_file = tmp_path / "AGENTS.md"
        agents_file.write_text("# Test\narc-theia-studio rules.\n")

        index_path = pin(tmp_path)
        assert index_path.exists()
        data = json.loads(index_path.read_text())
        assert data["version"] == 1
        assert len(data["entries"]) == 1
        assert data["entries"][0]["path"] == "AGENTS.md"
        assert len(data["entries"][0]["sha256"]) == 64


class TestCheckDrift:
    """Test drift detection."""

    def test_no_pin_with_files_is_drift(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Hello\n")
        report = check_drift(tmp_path)
        assert report.drifted is True
        assert "AGENTS.md" in report.added

    def test_no_pin_no_files_no_drift(self, tmp_path: Path) -> None:
        report = check_drift(tmp_path)
        assert report.drifted is False

    def test_pinned_unchanged_no_drift(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Hello\n")
        pin(tmp_path)
        report = check_drift(tmp_path)
        assert report.drifted is False

    def test_file_changed_detected(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Hello\n")
        pin(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Changed\n")
        report = check_drift(tmp_path)
        assert report.drifted is True
        assert "AGENTS.md" in report.changed

    def test_file_added_detected(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# Hello\n")
        pin(tmp_path)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "AGENTS.md").write_text("# Sub\n")
        report = check_drift(tmp_path)
        assert report.drifted is True
        assert any("sub" in p for p in report.added)

    def test_file_removed_detected(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "AGENTS.md").write_text("# Sub\n")
        (tmp_path / "AGENTS.md").write_text("# Root\n")
        pin(tmp_path)
        (sub / "AGENTS.md").unlink()
        report = check_drift(tmp_path)
        assert report.drifted is True
        assert any("sub" in p for p in report.removed)
