"""CLI tests for LM Arena commands."""

from __future__ import annotations

import json


def _json(stdout: str) -> dict:
    return json.loads(stdout)


def test_arena_list_command(run_cli):
    result = run_cli(["arena", "list", "--json"])
    assert result.exit_code == 0
    body = _json(result.stdout)
    assert body["ok"] is True
    assert body["data"]
    assert body["data"][0]["id"]


def test_arena_chat_stores_run(run_cli, workspace):
    result = run_cli(
        [
            "arena",
            "chat",
            "hello",
            "--workspace",
            str(workspace),
            "--json",
        ]
    )
    assert result.exit_code == 0
    body = _json(result.stdout)
    assert body["ok"] is True
    run_id = body["data"]["run_id"]
    assert (workspace / ".arc" / "traces" / f"{run_id}.jsonl").exists()


def test_arena_vote_and_rankings(run_cli, workspace):
    chat = run_cli(
        [
            "arena",
            "chat",
            "compare",
            "--mode",
            "battle",
            "--workspace",
            str(workspace),
            "--json",
        ]
    )
    assert chat.exit_code == 0
    chat_body = _json(chat.stdout)
    run_id = chat_body["data"]["run_id"]
    candidates = chat_body["data"]["candidates"]
    assert len(candidates) >= 2

    vote = run_cli(
        [
            "arena",
            "vote",
            run_id,
            candidates[0]["id"],
            candidates[1]["id"],
            "--workspace",
            str(workspace),
            "--json",
        ]
    )
    assert vote.exit_code == 0
    assert _json(vote.stdout)["data"]["recorded"] is True

    rankings = run_cli(["arena", "rankings", "--workspace", str(workspace), "--json"])
    assert rankings.exit_code == 0
    rankings_body = _json(rankings.stdout)
    assert rankings_body["data"]["total_votes"] == 1
    assert rankings_body["data"]["rankings"][0]["wins"] == 1
