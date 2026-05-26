from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.cli_repl.aliases import set_alias
from agent_runtime_cockpit.cli_repl.batch import (
    BatchErrorMode,
    build_batch_plan,
    execute_batch_plan,
)
from agent_runtime_cockpit.cli_repl.session import ChatSession
from agent_runtime_cockpit.cli_repl.slash_commands import CommandResult, SlashCommandHandler


class FakeHandler(SlashCommandHandler):
    def __init__(self) -> None:
        super().__init__()
        self.commands: list[str] = []

    def handle(self, command: str, session: ChatSession):  # type: ignore[override]
        self.commands.append(command)
        if "fail" in command:
            return CommandResult(state="error", output="failed", reason="test")
        return CommandResult(state="present", output=command)


def test_batch_parsing_and_alias_expansion(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_STUDIO_ALIASES_FILE", str(tmp_path / "user-aliases.json"))
    set_alias("hello", "/status", scope="workspace", workspace=tmp_path)

    plan = build_batch_plan("# c\n/alias run hello\n/status | /search foo\n", workspace=tmp_path)

    assert len(plan.segments) == 3
    assert plan.segments[0].expanded == "/status"
    assert plan.segments[0].alias_chain == ["hello (workspace) -> /status"]
    assert plan.segments[2].operator_before == "|"


def test_batch_denies_raw_no_shell_command(tmp_path):
    plan = build_batch_plan("echo hello; touch nope", workspace=tmp_path)

    assert plan.segments[0].allowed is False
    assert plan.segments[0].command_type == "denied"


def test_batch_denies_network_by_default(tmp_path):
    plan = build_batch_plan("/sandbox run -- curl https://example.com", workspace=tmp_path)

    assert plan.segments[0].allowed is False
    assert plan.segments[0].sandbox_decision["classification"] == "network"


def test_batch_run_fail_fast_stops(tmp_path):
    plan = build_batch_plan("/status\n/fail\n/status", workspace=tmp_path)
    handler = FakeHandler()

    result = execute_batch_plan(plan, handler=handler, error_mode=BatchErrorMode.FAIL_FAST)

    assert [r.command for r in result.results] == ["/status", "/fail"]
    assert result.ok is False


def test_batch_run_continue_on_error(tmp_path):
    plan = build_batch_plan("/status\n/fail\n/status", workspace=tmp_path)
    handler = FakeHandler()

    result = execute_batch_plan(plan, handler=handler, error_mode=BatchErrorMode.CONTINUE_ON_ERROR)

    assert [r.command for r in result.results] == ["/status", "/fail", "/status"]


def test_batch_cli_json_stable(tmp_path):
    batch = tmp_path / "batch.arc"
    batch.write_text("/status\n", encoding="utf-8")

    result = CliRunner().invoke(
        app, ["batch", "plan", str(batch), "--workspace", str(tmp_path), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["segments"][0]["expanded"] == "/status"
