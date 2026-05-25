"""Tests for DSPy runner (Phase 30 T3 — gated scaffold)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.adapters.dspy.runner import (
    DSPY_RUNNER_GATE_ENV,
    DSPyEventHandler,
    is_runner_enabled,
    run_dspy_program,
)


class TestRunnerGate:
    """Test runner environment gate."""

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(DSPY_RUNNER_GATE_ENV, raising=False)
        assert is_runner_enabled() is False

    def test_enabled_with_env_var(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "1")
        assert is_runner_enabled() is True

    def test_disabled_with_wrong_value(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "true")
        assert is_runner_enabled() is False

    def test_disabled_with_empty_value(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "")
        assert is_runner_enabled() is False


class TestEventHandler:
    """Test DSPyEventHandler event emission."""

    def test_module_start_event(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_module_start("ChainOfThought", "question -> answer")

        assert len(events) == 1
        assert events[0][0] == "run-001"
        assert events[0][1] == "DSPY_MODULE_START"
        assert events[0][2]["module_type"] == "ChainOfThought"
        assert events[0][2]["signature"] == "question -> answer"

    def test_module_end_event(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_module_end("Predict", result="answer text", duration_ms=150)

        assert len(events) == 1
        assert events[0][1] == "DSPY_MODULE_END"
        assert events[0][2]["status"] == "success"
        assert events[0][2]["duration_ms"] == 150

    def test_module_error_event(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_module_error("ReAct", RuntimeError("test error"))

        assert len(events) == 1
        assert events[0][1] == "DSPY_MODULE_ERROR"
        assert events[0][2]["error"] == "test error"
        assert events[0][2]["error_type"] == "RuntimeError"

    def test_predict_events(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_predict_start("question -> answer", {"question": "what?"})
        handler.on_predict_end("question -> answer", "42")

        assert len(events) == 2
        assert events[0][1] == "DSPY_PREDICT_START"
        assert events[1][1] == "DSPY_PREDICT_END"

    def test_compile_events(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_compile_start("MIPROv2", trainset_size=100)
        handler.on_compile_end("MIPROv2", duration_ms=5000)

        assert len(events) == 2
        assert events[0][1] == "DSPY_COMPILE_START"
        assert events[0][2]["optimizer"] == "MIPROv2"
        assert events[1][1] == "DSPY_COMPILE_END"

    def test_tool_events(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_tool_call("search", {"query": "test"})
        handler.on_tool_result("search", "results found")

        assert len(events) == 2
        assert events[0][1] == "DSPY_TOOL_CALL"
        assert events[1][1] == "DSPY_TOOL_RESULT"

    def test_sequence_numbers_increment(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_module_start("Predict")
        handler.on_module_end("Predict")
        handler.on_module_start("ChainOfThought")

        assert events[0][2]["sequence"] == 0
        assert events[1][2]["sequence"] == 1
        assert events[2][2]["sequence"] == 2

    def test_events_have_timestamps(self):
        events = []
        handler = DSPyEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_module_start("Predict")

        assert "timestamp" in events[0][2]


class TestRunDSPyProgram:
    """Test run_dspy_program gated execution."""

    def test_raises_when_gate_not_set(self, monkeypatch):
        monkeypatch.delenv(DSPY_RUNNER_GATE_ENV, raising=False)

        mock_program = Mock()
        events = []

        with pytest.raises(RuntimeError, match="gated"):
            run_dspy_program(
                mock_program,
                {"question": "test"},
                "run-001",
                lambda rid, et, d: events.append((rid, et, d)),
            )

        mock_program.assert_not_called()

    def test_executes_when_gate_set(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "1")

        mock_program = Mock()
        mock_program.forward.return_value = "answer"
        events = []

        result = run_dspy_program(
            mock_program,
            {"question": "test"},
            "run-001",
            lambda rid, et, d: events.append((rid, et, d)),
        )

        assert result == "answer"
        mock_program.forward.assert_called_once_with(question="test")
        assert any(e[1] == "DSPY_MODULE_START" for e in events)
        assert any(e[1] == "DSPY_MODULE_END" for e in events)

    def test_emits_error_on_failure(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "1")

        mock_program = Mock()
        mock_program.forward.side_effect = ValueError("bad input")
        events = []

        with pytest.raises(ValueError, match="bad input"):
            run_dspy_program(
                mock_program,
                {"question": "test"},
                "run-001",
                lambda rid, et, d: events.append((rid, et, d)),
            )

        assert any(e[1] == "DSPY_MODULE_ERROR" for e in events)

    def test_callable_program(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "1")

        mock_program = Mock()
        del mock_program.forward
        mock_program.return_value = "callable result"
        events = []

        result = run_dspy_program(
            mock_program,
            {"input": "data"},
            "run-001",
            lambda rid, et, d: events.append((rid, et, d)),
        )

        assert result == "callable result"

    def test_non_callable_raises(self, monkeypatch):
        monkeypatch.setenv(DSPY_RUNNER_GATE_ENV, "1")

        class NotCallable:
            pass

        events = []

        with pytest.raises(TypeError, match="not callable"):
            run_dspy_program(
                NotCallable(),
                {"input": "data"},
                "run-001",
                lambda rid, et, d: events.append((rid, et, d)),
            )
