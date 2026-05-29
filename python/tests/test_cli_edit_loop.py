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
    assert data["plan_path"].endswith(f"{data['plan_id']}.json")
    assert (tmp_path / ".arc" / "edit-plans" / f"{data['plan_id']}.json").exists()
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


def test_edit_apply_by_plan_id_uses_saved_hashes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"],
    )
    plan_id = _payload(plan)["data"]["plan_id"]

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--plan-id",
            plan_id,
            "--content",
            "new\n",
            "--approve",
        ],
    )

    assert result.exit_code == 0, result.output
    assert _payload(result)["data"]["applied"] is True
    assert target.read_text(encoding="utf-8") == "new\n"


def test_edit_apply_by_plan_id_denies_content_drift(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"],
    )
    plan_id = _payload(plan)["data"]["plan_id"]

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--plan-id",
            plan_id,
            "--content",
            "other\n",
            "--approve",
        ],
    )

    data = _payload(result)["data"]
    assert result.exit_code == 3
    assert data["reason"] == "replacement content does not match edit plan"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_multi_file_edit_plan_and_apply(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("a0\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b0\n", encoding="utf-8")

    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--edit", "a.txt=a1\n", "--edit", "b.txt=b1\n"],
    )

    assert plan.exit_code == 0, plan.output
    data = _payload(plan)["data"]
    assert len(data["files"]) == 2
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a0\n"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "b0\n"

    apply = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--edit",
            "a.txt=a1\n",
            "--edit",
            "b.txt=b1\n",
            "--approve",
        ],
    )

    assert apply.exit_code == 0, apply.output
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a1\n"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "b1\n"


def test_multi_file_apply_writes_none_when_one_stale(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("a0\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b0\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--edit", "a.txt=a1\n", "--edit", "b.txt=b1\n"],
    )
    plan_id = _payload(plan)["data"]["plan_id"]
    (tmp_path / "b.txt").write_text("b-stale\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--plan-id",
            plan_id,
            "--edit",
            "a.txt=a1\n",
            "--edit",
            "b.txt=b1\n",
            "--approve",
        ],
    )

    assert result.exit_code == 3
    assert _payload(result)["data"]["reason"] == "file changed since preview"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "a0\n"
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "b-stale\n"


def test_edit_list_show_and_approve_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app,
        ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"],
    )
    plan_id = _payload(plan)["data"]["plan_id"]

    listed = CliRunner().invoke(app, ["edit", "list", "--json"])
    shown = CliRunner().invoke(app, ["edit", "show", "--json", "--plan-id", plan_id])
    approved = CliRunner().invoke(
        app, ["edit", "approve", "--json", "--plan-id", plan_id, "--token", "tok"]
    )

    assert listed.exit_code == 0, listed.output
    assert _payload(listed)["data"]["plans"][0]["plan_id"] == plan_id
    assert shown.exit_code == 0, shown.output
    assert _payload(shown)["data"]["status"] == "present"
    show_text = json.dumps(_payload(shown)["data"])
    assert "new\n" not in show_text
    assert approved.exit_code == 0, approved.output

    applied = CliRunner().invoke(
        app,
        [
            "edit",
            "apply",
            "--json",
            "--plan-id",
            plan_id,
            "--content",
            "new\n",
            "--approval-token",
            "tok",
        ],
    )
    assert applied.exit_code == 0, applied.output


def test_patch_mode_valid_and_malformed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "--- a/note.txt\n+++ b/note.txt\n@@ -1 +1 @@\n-old\n+new"

    plan = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--patch", patch]
    )
    assert plan.exit_code == 0, plan.output
    assert _payload(plan)["data"]["files"][0]["patch_hash"]

    apply = CliRunner().invoke(
        app,
        ["edit", "apply", "--json", "--path", "note.txt", "--patch", patch, "--approve"],
    )
    assert apply.exit_code == 0, apply.output
    assert target.read_text(encoding="utf-8") == "new\n"

    bad = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--patch", "bad"]
    )
    assert bad.exit_code == 2


def test_patch_mode_multi_hunk_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("one\ntwo\nthree\nfour\nfive\n", encoding="utf-8")
    patch = (
        "--- a/note.txt\n"
        "+++ b/note.txt\n"
        "@@ -1,2 +1,2 @@\n"
        "-one\n"
        "+ONE\n"
        " two\n"
        "@@ -4,2 +4,2 @@\n"
        " four\n"
        "-five\n"
        "+FIVE"
    )

    result = CliRunner().invoke(
        app, ["edit", "apply", "--json", "--path", "note.txt", "--patch", patch, "--approve"]
    )

    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == "ONE\ntwo\nthree\nfour\nFIVE\n"


def test_patch_mode_line_count_mismatch_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("one\ntwo\n", encoding="utf-8")
    patch = "--- a/note.txt\n+++ b/note.txt\n@@ -1,2 +1,3 @@\n-one\n+ONE\n two"

    result = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--patch", patch]
    )

    assert result.exit_code == 2


def test_patch_mode_binary_content_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("one\n", encoding="utf-8")
    patch = "--- a/note.txt\n+++ b/note.txt\n@@ -1 +1 @@\n-one\n+two\x00"

    result = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--patch", patch]
    )

    assert result.exit_code == 2


def test_patch_mode_path_escape_denied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    patch = "--- a/../x.txt\n+++ b/../x.txt\n@@ -1 +1 @@\n-old\n+new"
    result = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "../x.txt", "--patch", patch]
    )
    assert result.exit_code == 2


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


def test_repl_edit_approve(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"]
    )
    plan_id = _payload(plan)["data"]["plan_id"]
    result = SlashCommandHandler().handle(f"/edit approve {plan_id} tok", ChatSession())
    assert result.state == "present"


def test_repl_diff_apply_and_test_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"]
    )
    plan_id = _payload(plan)["data"]["plan_id"]
    handler = SlashCommandHandler()
    session = ChatSession()

    diff = handler.handle(f"/diff --plan-id {plan_id}", session)
    assert diff.state == "present"
    assert "Saved metadata omits replacement content" in diff.output

    apply = handler.handle("/apply --path note.txt --content new --approve", session)
    assert apply.state == "present"
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "new"

    test = handler.handle("/test -- python -c 'print(123)'", session)
    assert test.state == "present"
    assert "123" in test.output


def test_repl_test_denies_network_by_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = SlashCommandHandler().handle("/test -- curl https://example.com", ChatSession())
    assert result.state == "denied"


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
