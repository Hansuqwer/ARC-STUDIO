from __future__ import annotations

import os
import sys

from agent_runtime_cockpit.cli_repl.cancellation import never_cancelled
from agent_runtime_cockpit.security.sandbox import SandboxPolicy
from agent_runtime_cockpit.tools.shell import BashArgs, BashTool
from agent_runtime_cockpit.tools.write import (
    CreateFileArgs,
    CreateFileTool,
    EditFileArgs,
    EditFileTool,
    WriteFileArgs,
    WriteFileTool,
)


def test_write_file_tool_writes_inside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = WriteFileTool(tmp_path, tmp_path / "trust.json").execute(
        WriteFileArgs(path="a.txt", content="hello"), never_cancelled()
    )
    assert (tmp_path / "a.txt").read_text() == "hello"
    assert result.content["bytes_written"] == 5


def test_write_file_tool_denies_outside_and_symlink_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "outside.txt"
    result = WriteFileTool(tmp_path, tmp_path / "trust.json").execute(
        WriteFileArgs(path=str(outside), content="bad"), never_cancelled()
    )
    assert "error" in result.content
    link = tmp_path / "link"
    link.symlink_to(tmp_path.parent)
    result = WriteFileTool(tmp_path, tmp_path / "trust.json").execute(
        WriteFileArgs(path="link/escape.txt", content="bad"), never_cancelled()
    )
    assert "error" in result.content


def test_edit_file_tool_applies_replacement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "a.txt"
    path.write_text("hello old", encoding="utf-8")
    result = EditFileTool(tmp_path, tmp_path / "trust.json").execute(
        EditFileArgs(path="a.txt", old_string="old", new_string="new"), never_cancelled()
    )
    assert result.content["applied"] is True
    assert path.read_text(encoding="utf-8") == "hello new"


def test_edit_file_tool_errors_on_missing_old_string(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    result = EditFileTool(tmp_path, tmp_path / "trust.json").execute(
        EditFileArgs(path="a.txt", old_string="missing", new_string="new"), never_cancelled()
    )
    assert result.content["applied"] is False
    assert "exactly once" in result.content["error"]


def test_create_file_tool_creates_new_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CreateFileTool(tmp_path, tmp_path / "trust.json").execute(
        CreateFileArgs(path="new.txt", content="x"), never_cancelled()
    )
    assert result.content["created"] is True
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "x"


def test_create_file_tool_errors_if_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "new.txt").write_text("x", encoding="utf-8")
    result = CreateFileTool(tmp_path, tmp_path / "trust.json").execute(
        CreateFileArgs(path="new.txt", content="y"), never_cancelled()
    )
    assert result.content["created"] is False
    assert "already exists" in result.content["error"]


def test_bash_tool_runs_read_only_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = BashTool(tmp_path, trust_db=tmp_path / "trust.json").execute(
        BashArgs(command="ls"), never_cancelled()
    )
    assert result.content["exit_code"] == 0


def test_bash_tool_denies_destructive_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = BashTool(tmp_path, trust_db=tmp_path / "trust.json").execute(
        BashArgs(command="rm -rf ."), never_cancelled()
    )
    assert result.content["allowed"] is False
    assert result.content["classification"] == "destructive"


def test_bash_tool_respects_timeout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy = SandboxPolicy(workspace_root=tmp_path, allow_unknown=True, timeout_seconds=1)
    result = BashTool(tmp_path, policy, tmp_path / "trust.json").execute(
        BashArgs(command=f"{sys.executable} -c 'import time; time.sleep(3)'"), never_cancelled()
    )
    assert result.content["timed_out"] is True


def test_bash_tool_output_capped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy = SandboxPolicy(workspace_root=tmp_path, max_output_bytes=10, allow_unknown=True)
    result = BashTool(tmp_path, policy, tmp_path / "trust.json").execute(
        BashArgs(command=f"{sys.executable} -c 'print(\"x\"*100)'"), never_cancelled()
    )
    assert len(result.content["stdout"].encode()) <= 10


def test_bash_tool_env_secret_stripped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secretsecretsecretsecret")
    policy = SandboxPolicy(workspace_root=tmp_path, allow_unknown=True)
    result = BashTool(tmp_path, policy, tmp_path / "trust.json").execute(
        BashArgs(command=f"{sys.executable} -c 'import os; print(os.getenv(\"OPENAI_API_KEY\"))'"),
        never_cancelled(),
    )
    assert "None" in result.content["stdout"]
    assert os.environ["OPENAI_API_KEY"]
