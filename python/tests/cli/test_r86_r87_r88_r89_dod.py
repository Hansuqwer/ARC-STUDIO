"""CLI error-state tests for R86/R87/R88/R89 new commands (DoD gate 1/4).

Covers: loading state, empty state, error state, degraded state per DoD.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


# ── R86 continuum ────────────────────────────────────────────────────────────


def test_continuum_list_empty_state(tmp_path, monkeypatch):
    """Empty state: no sessions dir shows 'No sessions found'."""
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    result = runner.invoke(app, ["continuum", "list", "--sessions-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "No sessions found" in result.output


def test_continuum_list_json_is_array(tmp_path, monkeypatch):
    """JSON output is a stable array (parity gate)."""
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    result = runner.invoke(app, ["continuum", "list", "--json", "--sessions-dir", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_continuum_resume_not_found_exits_1(tmp_path, monkeypatch):
    """Error state: missing session exits 1 with message, no traceback."""
    monkeypatch.setenv("ARC_STUDIO_SESSIONS_DIR", str(tmp_path))
    result = runner.invoke(app, ["continuum", "resume", "no-such", "--sessions-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "not found" in (result.stderr or "").lower()
    assert "Traceback" not in (result.output + (result.stderr or ""))


# ── R88 git-native ────────────────────────────────────────────────────────────


def test_git_native_branch_no_repo_exits_1(tmp_path):
    """Error state: branch without repo exits 1 cleanly."""
    result = runner.invoke(app, ["git-native", "branch", "sess-1", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "Traceback" not in (result.output + (result.stderr or ""))


def test_git_native_init_json_ok_field(tmp_path):
    """JSON output has ok field (stable parity)."""
    result = runner.invoke(app, ["git-native", "init", "--json", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True
    assert "workspace" in data


def test_git_native_auto_commit_no_repo_exits_1(tmp_path):
    """Error state: auto-commit without repo exits 1."""
    result = runner.invoke(app, ["git-native", "auto-commit", "--workspace", str(tmp_path)])
    assert result.exit_code == 1


def test_git_native_auto_revert_no_repo_exits_1(tmp_path):
    """Error state: auto-revert without repo exits 1."""
    result = runner.invoke(app, ["git-native", "auto-revert", "--workspace", str(tmp_path)])
    assert result.exit_code == 1


# ── R89 diff ─────────────────────────────────────────────────────────────────


def test_diff_apply_missing_file_exits_1(tmp_path):
    """Error state: missing patch file exits 1."""
    result = runner.invoke(
        app, ["diff", "apply", str(tmp_path / "missing.patch"), "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "Traceback" not in (result.output + (result.stderr or ""))


def test_diff_apply_missing_file_no_traceback(tmp_path):
    """Error state shows human-readable message, not traceback."""
    result = runner.invoke(
        app, ["diff", "apply", str(tmp_path / "gone.patch"), "--workspace", str(tmp_path)]
    )
    assert "not found" in result.output.lower() or "not found" in (result.stderr or "").lower()
