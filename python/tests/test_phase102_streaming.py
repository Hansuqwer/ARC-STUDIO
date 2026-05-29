from __future__ import annotations

import json
import sys

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.runtime.streaming import (
    StreamEventType,
    disconnected_replay_event,
    stream_subprocess_events,
)


def _jsonl(output: str) -> list[dict]:
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def test_sandbox_run_stream_json_stdout_stderr(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "run",
            "--json",
            "--stream-json",
            "--",
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
    )

    assert result.exit_code == 0, result.output
    events = [item["data"] for item in _jsonl(result.output)]
    assert [event["event"] for event in events][0] == "started"
    assert any(event["event"] == "stdout" and "out" in event["data"] for event in events)
    assert any(event["event"] == "stderr" and "err" in event["data"] for event in events)
    assert events[-1]["event"] == "completed"
    assert {event["mode"] for event in events} == {"live"}


def test_testbench_run_stream_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "testbench",
            "run",
            "--json",
            "--stream-json",
            "--",
            sys.executable,
            "-c",
            "print('testbench')",
        ],
    )

    assert result.exit_code == 0, result.output
    events = [item["data"] for item in _jsonl(result.output)]
    assert any(event["source"] == "testbench" for event in events)
    assert any("testbench" in event["data"] for event in events)


def test_provider_shell_stream_json_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        ["providers", "shell", "--json", "--stream-json", "--prompt", "hi", "--tool-cmd", "ls"],
    )

    assert result.exit_code == 0, result.output
    events = [item["data"] for item in _jsonl(result.output)]
    assert [event["event"] for event in events] == ["started", "completed"]
    assert {event["source"] for event in events} == {"provider_shell"}


def test_stream_cancel_timeout_truncation_and_replay_disconnect(tmp_path):
    cancel_events, cancel_result = stream_subprocess_events(
        [sys.executable, "-c", "import time; print('first', flush=True); time.sleep(5)"],
        cwd=tmp_path,
        source="sandbox",
        timeout_seconds=10,
        cancel_after_events=1,
    )
    assert cancel_result.terminal_event == StreamEventType.CANCELLED
    assert cancel_events[-1].event == StreamEventType.CANCELLED

    timeout_events, timeout_result = stream_subprocess_events(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        source="sandbox",
        timeout_seconds=0,
    )
    assert timeout_result.terminal_event == StreamEventType.TIMEOUT
    assert timeout_events[-1].reason == "timeout"

    trunc_events, trunc_result = stream_subprocess_events(
        [sys.executable, "-c", "print('x' * 100)"],
        cwd=tmp_path,
        source="sandbox",
        max_output_bytes=8,
    )
    assert trunc_result.stdout_truncated is True
    assert any(event.event == StreamEventType.TRUNCATED for event in trunc_events)

    disconnected = disconnected_replay_event("stream-old", source="sandbox")
    assert disconnected.event == StreamEventType.DISCONNECTED
    assert disconnected.mode == "replay"
