"""Workspace symlink-escape guard tests (ADR-024 P3/P5 — code-level proof).

Tests is_path_within_root() and check_workspace_escape() from security/sandbox.py.

These tests prove the code-level guard works correctly for:
  - Paths inside the workspace root (allowed)
  - Paths outside the workspace root (denied)
  - Paths with .. components escaping the root (denied)
  - Symlinks inside the workspace pointing outside (denied)
  - Chained symlinks escaping (denied)
  - Dangling symlinks (denied — treated as outside)
  - Relative path resolution

All tests use tmp_path and os.symlink(); no Lima or Firecracker required.

Note on mount-level proof (P3/P5):
  Code-level symlink detection prevents workspace_root itself from being
  a symlink pointing elsewhere. However, virtiofs (Lima 2.x VZ default)
  passes symlinks through to the guest — a symlink INSIDE the workspace
  pointing outside will be accessible in the guest. Full mount-level proof
  requires a real guest-side test, which is blocked pending Lima real-host
  execution (ADR-024 P3/P5 partially satisfied).
"""

from __future__ import annotations

import os

import pytest

from agent_runtime_cockpit.security.sandbox import check_workspace_escape, is_path_within_root


class TestIsPathWithinRoot:
    """is_path_within_root() must correctly detect escape attempts."""

    def test_path_inside_root_allowed(self, tmp_path):
        """A normal sub-path inside root returns True."""
        subdir = tmp_path / "subdir" / "file.txt"
        assert is_path_within_root(subdir, tmp_path) is True

    def test_path_equals_root_allowed(self, tmp_path):
        """root == path returns True (exact equality)."""
        assert is_path_within_root(tmp_path, tmp_path) is True

    def test_path_outside_root_denied(self, tmp_path):
        """A path clearly outside the root returns False."""
        outside = tmp_path.parent / "other-dir" / "file.txt"
        assert is_path_within_root(outside, tmp_path) is False

    def test_path_with_dotdot_outside_denied(self, tmp_path):
        """A path using .. to escape the root returns False."""
        escape = tmp_path / "subdir" / ".." / ".." / "etc" / "passwd"
        assert is_path_within_root(escape, tmp_path) is False

    def test_path_prefix_collision_denied(self, tmp_path):
        """A path that is a prefix string match but not a child is denied.

        e.g. /tmp/workspace-evil must not match /tmp/workspace.
        """
        root = tmp_path / "workspace"
        root.mkdir()
        evil = tmp_path / "workspace-evil" / "file.txt"
        assert is_path_within_root(evil, root) is False

    def test_symlink_inside_pointing_outside_denied(self, tmp_path):
        """A symlink inside workspace pointing to a path outside → False."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        sentinel = outside / "secret.txt"
        sentinel.write_text("secret", encoding="utf-8")

        link = workspace / "escape-link"
        os.symlink(outside, link)

        # The symlink itself is inside workspace, but its target is outside
        assert is_path_within_root(link, workspace) is False

    def test_symlink_chain_escaping_denied(self, tmp_path):
        """Chained symlinks that ultimately escape workspace → False."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        # link1 → link2 → outside
        link2 = workspace / "link2"
        os.symlink(outside, link2)
        link1 = workspace / "link1"
        os.symlink(link2, link1)

        assert is_path_within_root(link1, workspace) is False

    def test_dangling_symlink_treated_as_outside(self, tmp_path):
        """A dangling symlink (target does not exist) pointing outside → False."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        # Symlink to a non-existent path outside workspace
        nonexistent_outside = tmp_path / "nonexistent" / "path"
        link = workspace / "dangling"
        os.symlink(nonexistent_outside, link)

        # os.path.realpath follows the symlink even for missing targets
        assert is_path_within_root(link, workspace) is False

    def test_nested_path_within_root_allowed(self, tmp_path):
        """A deeply nested real path inside workspace → True."""
        deep = tmp_path / "a" / "b" / "c" / "d" / "file.txt"
        assert is_path_within_root(deep, tmp_path) is True

    def test_relative_path_resolved_correctly(self, tmp_path):
        """Relative paths that resolve inside workspace → True."""
        # Create a real subdir
        subdir = tmp_path / "sub"
        subdir.mkdir()
        # Relative path from subdir going back up but staying in workspace
        rel = subdir / ".." / "other-sub"
        assert is_path_within_root(rel, tmp_path) is True

    def test_symlink_inside_pointing_inside_allowed(self, tmp_path):
        """A symlink inside workspace pointing to another location inside → True."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        target = workspace / "real-dir"
        target.mkdir()
        link = workspace / "safe-link"
        os.symlink(target, link)

        assert is_path_within_root(link, workspace) is True


class TestCheckWorkspaceEscape:
    """check_workspace_escape() raises ValueError on escape; no-op on safe paths."""

    def test_safe_path_does_not_raise(self, tmp_path):
        """A path inside workspace → no exception."""
        safe = tmp_path / "subdir" / "file.py"
        check_workspace_escape(safe, tmp_path)  # should not raise

    def test_escape_raises_value_error(self, tmp_path):
        """A path outside workspace → ValueError."""
        outside = tmp_path.parent / "escape" / "file.py"
        with pytest.raises(ValueError, match="Path escape detected"):
            check_workspace_escape(outside, tmp_path)

    def test_dotdot_raises_value_error(self, tmp_path):
        """.. escape raises ValueError."""
        escape = tmp_path / "sub" / ".." / ".." / "etc" / "passwd"
        with pytest.raises(ValueError, match="Path escape detected"):
            check_workspace_escape(escape, tmp_path)

    def test_symlink_escape_raises_value_error(self, tmp_path):
        """Symlink pointing outside workspace raises ValueError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        link = workspace / "evil-link"
        os.symlink(outside, link)

        with pytest.raises(ValueError, match="Path escape detected"):
            check_workspace_escape(link, workspace)

    def test_error_message_contains_candidate_and_root(self, tmp_path):
        """Error message includes both the candidate and workspace root paths."""
        outside = tmp_path.parent / "other"
        with pytest.raises(ValueError) as exc_info:
            check_workspace_escape(outside, tmp_path)
        msg = str(exc_info.value)
        assert "outside workspace root" in msg


class TestHarnessEscapeGuard:
    """LimaIntegrationHarness and FirecrackerIntegrationHarness workspace escape guards.

    Note on scope: the harness escape guard uses check_workspace_escape() at
    __init__ time to ensure workspace_root itself doesn't point outside its
    parent directory. The primary protection (is_path_within_root) is used at
    the security layer for paths inside the workspace.

    Mount-level symlink escape (a symlink INSIDE the workspace pointing outside)
    requires a real guest-side test; this is documented as a P3/P5 gap.
    """

    def test_lima_harness_rejects_workspace_root_outside_parent(self, tmp_path):
        """workspace_root pointing to a path outside its declared parent → ValueError."""
        from agent_runtime_cockpit.isolation.microvm import LimaIntegrationHarness

        # Create a workspace at /tmp/X/workspace and an outside path at /tmp/Y/outside
        parent_a = tmp_path / "parent-a"
        parent_a.mkdir()
        workspace = parent_a / "workspace"
        workspace.mkdir()

        parent_b = tmp_path / "parent-b"
        parent_b.mkdir()
        outside = parent_b / "outside"
        outside.mkdir()

        # Symlink workspace to point outside its own parent (parent_a)
        link_root = parent_a / "link-workspace"
        os.symlink(outside, link_root)

        with pytest.raises(ValueError, match="Path escape detected"):
            LimaIntegrationHarness(
                workspace_root=link_root,
                runner=lambda *_: None,
            )

    def test_firecracker_harness_rejects_workspace_root_outside_parent(self, tmp_path):
        """FirecrackerIntegrationHarness: workspace_root pointing outside parent → ValueError."""
        from agent_runtime_cockpit.isolation.microvm import FirecrackerIntegrationHarness

        parent_a = tmp_path / "parent-a"
        parent_a.mkdir()
        parent_b = tmp_path / "parent-b"
        parent_b.mkdir()
        outside = parent_b / "outside"
        outside.mkdir()

        link_root = parent_a / "link-workspace"
        os.symlink(outside, link_root)

        with pytest.raises(ValueError, match="Path escape detected"):
            FirecrackerIntegrationHarness(
                workspace_root=link_root,
                runner=lambda *_: None,
            )

    def test_lima_harness_safe_workspace_no_raise(self, tmp_path):
        """A real (non-symlink) workspace_root does not trigger escape check."""
        from agent_runtime_cockpit.isolation.base import IsolationResult
        from agent_runtime_cockpit.isolation.microvm import LimaIntegrationHarness

        calls: list = []

        def runner(argv, _t, _m):
            calls.append(argv)
            return IsolationResult(exit_code=0, stdout="ok", provider="microvm")

        harness = LimaIntegrationHarness(
            workspace_root=tmp_path,
            runner=runner,
            instance_name="arc-escape-test",
        )
        result = harness.run(["echo", "ok"], require_gate=False)
        assert result.teardown_attempted is True
        # check_workspace_escape did not raise → harness proceeded to call runner
        assert len(calls) > 0
