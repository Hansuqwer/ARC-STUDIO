from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def _payload(result):
    return json.loads(result.output)


def test_repair_loop_fail_repair_pass_with_audit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / ".arc" / "audit"))
    code = "import sys; data=open('target.txt').read(); print(data); sys.exit(0 if 'fixed' in data else 1)"

    result = CliRunner().invoke(
        app,
        [
            "edit",
            "repair-loop",
            "--json",
            "--path",
            "target.txt",
            "--initial-content",
            "broken\n",
            "--repair-content",
            "fixed\n",
            "--test-cmd",
            sys.executable,
            "--test-cmd=-c",
            "--test-cmd",
            code,
        ],
    )

    assert result.exit_code == 0, result.output
    data = _payload(result)["data"]
    assert data["ok"] is True
    assert data["stopped_reason"] == "passed"
    assert [item["step"] for item in data["attempts"]] == ["edit", "test", "repair", "test"]
    assert data["transaction_id"].startswith("txn-")
    assert len(data["audit_events"]) == 2
    assert (tmp_path / "target.txt").read_text(encoding="utf-8") == "fixed\n"


def test_repair_loop_denied_sandbox_command_stops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / ".arc" / "audit"))
    result = CliRunner().invoke(
        app,
        [
            "edit",
            "repair-loop",
            "--json",
            "--path",
            "target.txt",
            "--initial-content",
            "broken\n",
            "--repair-content",
            "fixed\n",
            "--test-cmd",
            "curl",
            "--test-cmd",
            "https://example.com",
        ],
    )

    assert result.exit_code == 3
    data = _payload(result)["data"]
    assert data["stopped_reason"] == "sandbox_denied"
    assert data["audit_events"][0]["allowed"] is False


def test_edit_transaction_undo_redo_and_conflict_protection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    apply = CliRunner().invoke(
        app,
        ["edit", "apply", "--json", "--path", "note.txt", "--content", "new\n", "--approve"],
    )
    assert apply.exit_code == 0, apply.output
    txn = _payload(apply)["data"]["transaction_id"]

    undo = CliRunner().invoke(app, ["edit", "undo", "--json", "--transaction-id", txn])
    assert undo.exit_code == 0, undo.output
    assert target.read_text(encoding="utf-8") == "old\n"

    redo = CliRunner().invoke(app, ["edit", "redo", "--json", "--transaction-id", txn])
    assert redo.exit_code == 0, redo.output
    assert target.read_text(encoding="utf-8") == "new\n"

    target.write_text("user-change\n", encoding="utf-8")
    blocked = CliRunner().invoke(app, ["edit", "undo", "--json", "--transaction-id", txn])
    assert blocked.exit_code == 3
    assert (
        _payload(blocked)["data"]["reason"] == "current file differs from transaction after-state"
    )
    assert target.read_text(encoding="utf-8") == "user-change\n"


def test_edit_diff_returns_real_capped_diff(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("old\n", encoding="utf-8")
    plan = CliRunner().invoke(
        app, ["edit", "plan", "--json", "--path", "note.txt", "--content", "new\n"]
    )
    plan_id = _payload(plan)["data"]["plan_id"]

    diff = CliRunner().invoke(app, ["edit", "diff", "--json", "--plan-id", plan_id])

    assert diff.exit_code == 0, diff.output
    data = _payload(diff)["data"]
    assert data["status"] == "present"
    assert "-old" in data["diff"]
    assert "+new" in data["diff"]
    assert data["binary"] is False


def test_provider_shell_dry_run_routes_tool_policy_and_live_gates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / ".arc" / "audit"))

    dry = CliRunner().invoke(
        app,
        ["providers", "shell", "--json", "--prompt", "hi", "--tool-cmd", "ls", "--tool-cmd", "."],
    )
    assert dry.exit_code == 0, dry.output
    data = _payload(dry)["data"]
    assert data["dry_run"] is True
    assert data["real_provider_call"] is False
    assert data["tool_decision"]["allowed"] is True

    live = CliRunner().invoke(app, ["providers", "shell", "--json", "--live"])
    assert live.exit_code == 1
    assert _payload(live)["ok"] is False
