"""Tests for Smolagents gated runner."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.adapters.smolagents.runner import (
    SMOLAGENTS_RUNNER_GATE_ENV,
    SmolagentsEventHandler,
    is_runner_enabled,
    run_smolagents_agent,
)


def test_runner_disabled_by_default(monkeypatch):
    monkeypatch.delenv(SMOLAGENTS_RUNNER_GATE_ENV, raising=False)
    assert is_runner_enabled() is False


def test_runner_enabled(monkeypatch):
    monkeypatch.setenv(SMOLAGENTS_RUNNER_GATE_ENV, "1")
    assert is_runner_enabled() is True


def test_event_handler_emits_agent_events():
    events = []
    handler = SmolagentsEventHandler("run-1", lambda rid, et, data: events.append((rid, et, data)))
    handler.on_agent_start("CodeAgent", "task")
    handler.on_code_execution("docker")
    handler.on_agent_end("CodeAgent", "ok")
    assert [event[1] for event in events] == [
        "SMOLAGENTS_AGENT_START",
        "SMOLAGENTS_CODE_EXECUTION",
        "SMOLAGENTS_AGENT_END",
    ]
    assert events[0][2]["sequence"] == 0
    assert events[2][2]["sequence"] == 2


def test_run_agent_raises_when_gated(monkeypatch):
    monkeypatch.delenv(SMOLAGENTS_RUNNER_GATE_ENV, raising=False)
    agent = Mock()
    with pytest.raises(RuntimeError, match="gated"):
        run_smolagents_agent(agent, "task", "run-1", lambda *_: None)
    agent.run.assert_not_called()


def test_run_agent_when_enabled(monkeypatch):
    monkeypatch.setenv(SMOLAGENTS_RUNNER_GATE_ENV, "1")
    agent = Mock()
    agent.run.return_value = "done"
    events = []
    result = run_smolagents_agent(agent, "task", "run-1", lambda *event: events.append(event))
    assert result == "done"
    agent.run.assert_called_once_with("task")
    assert events[0][1] == "SMOLAGENTS_AGENT_START"
    assert events[-1][1] == "SMOLAGENTS_AGENT_END"


def test_run_agent_emits_error(monkeypatch):
    monkeypatch.setenv(SMOLAGENTS_RUNNER_GATE_ENV, "1")
    agent = Mock()
    agent.run.side_effect = ValueError("bad")
    events = []
    with pytest.raises(ValueError, match="bad"):
        run_smolagents_agent(agent, "task", "run-1", lambda *event: events.append(event))
    assert events[-1][1] == "SMOLAGENTS_AGENT_ERROR"
