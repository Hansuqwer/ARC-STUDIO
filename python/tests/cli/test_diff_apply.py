"""Tests: R89a — arc diff apply (Phase 291)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app

runner = CliRunner()


@pytest.fixture
def git_repo_with_file(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    f = tmp_path / "hello.txt"
    f.write_text("line1\nline2\nline3\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    return tmp_path


def make_patch(repo: Path) -> Path:
    """Create a valid patch file."""
    patch = repo / "test.patch"
    patch.write_text(
        "diff --git a/hello.txt b/hello.txt\n"
        "index abc..def 100644\n"
        "--- a/hello.txt\n"
        "+++ b/hello.txt\n"
        "@@ -1,3 +1,3 @@\n"
        " line1\n"
        "-line2\n"
        "+LINE2\n"
        " line3\n"
    )
    return patch


def test_diff_apply_noninteractive(git_repo_with_file):
    patch = make_patch(git_repo_with_file)
    result = runner.invoke(
        app, ["diff", "apply", str(patch), "--workspace", str(git_repo_with_file)]
    )
    assert result.exit_code == 0
    content = (git_repo_with_file / "hello.txt").read_text()
    assert "LINE2" in content


def test_diff_apply_json_output(git_repo_with_file):
    patch = make_patch(git_repo_with_file)
    result = runner.invoke(
        app, ["diff", "apply", str(patch), "--json", "--workspace", str(git_repo_with_file)]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True


def test_diff_apply_missing_patch(tmp_path):
    result = runner.invoke(
        app, ["diff", "apply", str(tmp_path / "no.patch"), "--workspace", str(tmp_path)]
    )
    assert result.exit_code == 1
