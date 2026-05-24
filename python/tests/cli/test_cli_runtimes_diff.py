"""Tests for `arc runtimes --diff-from X --diff-to Y`."""

from __future__ import annotations

import json
import re

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    return ANSI_RE.sub("", text)


class TestRuntimesDiffCLI:
    """Capability diff CLI tests."""

    def test_diff_help_available(self, run_cli):
        r = run_cli(["runtimes", "--help"])
        assert r.exit_code == 0
        help_text = plain(r.stdout)
        assert "--diff-from" in help_text
        assert "--diff-to" in help_text

    def test_diff_unknown_from_runtime(self, run_cli):
        r = run_cli(
            ["runtimes", "--diff-from", "nonexistent_xyz", "--diff-to", "langgraph", "--json"]
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert not data.get("ok", True) or data.get("error") is not None

    def test_diff_unknown_to_runtime(self, run_cli):
        r = run_cli(
            ["runtimes", "--diff-from", "langgraph", "--diff-to", "nonexistent_xyz", "--json"]
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert not data.get("ok", True) or data.get("error") is not None

    def test_diff_known_runtimes_returns_json(self, run_cli):
        r = run_cli(["runtimes", "--diff-from", "langgraph", "--diff-to", "swarmgraph", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data.get("ok") is True
        assert "data" in data
        diff = data["data"]
        assert "diff_id" in diff
        assert "added_capabilities" in diff
        assert "removed_capabilities" in diff
        assert "changed_flags" in diff
        assert "requires_confirmation" in diff
        assert "timestamp" in diff

    def test_diff_requires_confirmation_field_is_bool(self, run_cli):
        r = run_cli(["runtimes", "--diff-from", "langgraph", "--diff-to", "swarmgraph", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        diff = data["data"]
        assert isinstance(diff["requires_confirmation"], bool)

    def test_diff_same_runtime_no_changes(self, run_cli):
        r = run_cli(["runtimes", "--diff-from", "langgraph", "--diff-to", "langgraph", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        diff = data["data"]
        assert len(diff["added_capabilities"]) == 0
        assert len(diff["removed_capabilities"]) == 0
        assert diff["requires_confirmation"] is False

    def test_diff_schema_version(self, run_cli):
        r = run_cli(["runtimes", "--diff-from", "langgraph", "--diff-to", "swarmgraph", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        diff = data["data"]
        assert diff.get("schema_version") == 1
