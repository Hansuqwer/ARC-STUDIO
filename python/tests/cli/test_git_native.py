"""Tests: R88a — arc git-native init + auto-branch (Phase 289)."""

from __future__ import annotations

import json
import subprocess

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"], cwd=str(tmp_path), capture_output=True
    )
    return tmp_path


def test_git_init_creates_repo(tmp_path):
    result = runner.invoke(app, ["git-native", "init", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".git").exists()


def test_git_init_json_output(tmp_path):
    result = runner.invoke(app, ["git-native", "init", "--json", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True


def test_git_init_idempotent(git_repo):
    result = runner.invoke(app, ["git-native", "init", "--workspace", str(git_repo)])
    assert result.exit_code == 0
    assert "already initialized" in result.output


def test_git_branch_creates_branch(git_repo):
    result = runner.invoke(
        app, ["git-native", "branch", "sess-abc123", "--workspace", str(git_repo)]
    )
    assert result.exit_code == 0
    branches = subprocess.run(
        ["git", "branch"], cwd=str(git_repo), capture_output=True, text=True
    ).stdout
    assert "arc/session-sess-abc123" in branches


def test_git_branch_json_output(git_repo):
    result = runner.invoke(
        app, ["git-native", "branch", "my-session", "--json", "--workspace", str(git_repo)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["branch"] == "arc/session-my-session"
    assert data["ok"] is True


def test_git_branch_fails_without_repo(tmp_path):
    result = runner.invoke(app, ["git-native", "branch", "sess-1", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
