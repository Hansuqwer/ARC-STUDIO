from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import SlashCommandHandler
from agent_runtime_cockpit.runtime.tool_runtime import run_registered_tool


def _payload(result):
    return json.loads(result.output)


def test_edit_plan_previews_diff_without_writing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"],
    )

    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["allowed"] is True
    assert data["classification"] == "writes_workspace"
    assert data["original_exists"] is True
    assert data["original_hash"]
    assert data["replacement_hash"]
    assert "-old" in data["diff"]
    assert "+new" in data["diff"]
    assert (tmp_path / ".arc" / "audit" / "plan.events.jsonl").exists()
    assert target.read_text(encoding="utf-8") == "old\n"


def test_edit_apply_requires_explicit_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["edit", "apply", "--json", "--path", "note.txt", "--content", "new\n"],
    )

    assert result.exit_code == 3
    assert _payload(result)["data"]["applied"] is False
    assert target.read_text(encoding="utf-8") == "old\n"


def test_edit_apply_writes_after_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--path",
            "note.txt",
            "--content",
            "new\n",
            "--approve",
        ],
    )

    assert result.exit_code == 0, result.output
    assert _payload(result)["data"]["applied"] is True
    assert _payload(result)["data"]["audit_events"][0]["type"] == "edit_apply_applied"
    assert target.read_text(encoding="utf-8") == "new\n"


def test_edit_apply_denies_stale_preview_hash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"],
    )
    expected_hash = _payload(plan)["data"]["original_hash"]
    target.write_text("changed\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--path",
            "note.txt",
            "--content",
            "new\n",
            "--approve",
            "--expected-original-hash",
            expected_hash,
        ],
    )

    data = _payload(result)["data"]
    assert result.exit_code == 3
    assert data["applied"] is False
    assert data["reason"] == "file changed since preview"
    assert target.read_text(encoding="utf-8") == "changed\n"


def test_edit_denies_path_escape(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    result = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "../outside.txt", "--content", "x"],
    )

    assert result.exit_code == 2
    assert _payload(result)["ok"] is False


def test_repl_edit_plan_and_apply(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session = ChatSession()
    handler = SlashCommandHandler()

    plan = handler.handle("/edit plan --path note.txt --content hello", session)
    assert plan.state == "present"
    assert "Edit plan" in plan.output
    assert not (tmp_path / "note.txt").exists()

    apply = handler.handle("/edit apply --path note.txt --content hello --approve", session)
    assert apply.state == "present"
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "hello"


def test_help_lists_edit_command():
    result = SlashCommandHandler().handle("/help", ChatSession())
    assert "/edit" in str(result)


def test_tool_runtime_wraps_registered_tool(tmp_path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    wrapped = run_registered_tool("read_file", {"path": str(file_path)})

    assert 'tool="read_file"' in wrapped
    assert 'trust="untrusted"' in wrapped
    assert "hello" in wrapped


def test_tool_runtime_rejects_unknown_tool():
    try:
        run_registered_tool("missing-tool")
    except ValueError as exc:
        assert "unknown tool" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unknown tool was not rejected")
