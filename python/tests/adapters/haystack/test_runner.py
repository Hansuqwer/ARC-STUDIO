"""Tests for Haystack runner (Phase 31 T3 — gated scaffold)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.adapters.haystack.runner import (
    HAYSTACK_RUNNER_GATE_ENV,
    HaystackEventHandler,
    is_runner_enabled,
    run_haystack_pipeline,
)


class TestRunnerGate:
    """Test runner environment gate."""

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(HAYSTACK_RUNNER_GATE_ENV, raising=False)
        assert is_runner_enabled() is False

    def test_enabled_with_env_var(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "1")
        assert is_runner_enabled() is True

    def test_disabled_with_wrong_value(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "true")
        assert is_runner_enabled() is False

    def test_disabled_with_empty_value(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "")
        assert is_runner_enabled() is False


class TestEventHandler:
    """Test HaystackEventHandler event emission."""

    def test_pipeline_start_event(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_pipeline_start("rag_pipe", 3, {"query": "test"})

        assert len(events) == 1
        assert events[0][0] == "run-001"
        assert events[0][1] == "HAYSTACK_PIPELINE_START"
        assert events[0][2]["pipeline_name"] == "rag_pipe"
        assert events[0][2]["component_count"] == 3

    def test_pipeline_end_event(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_pipeline_end("rag_pipe", result={"answer": "42"}, duration_ms=250)

        assert len(events) == 1
        assert events[0][1] == "HAYSTACK_PIPELINE_END"
        assert events[0][2]["status"] == "success"
        assert events[0][2]["duration_ms"] == 250

    def test_pipeline_error_event(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_pipeline_error("rag_pipe", RuntimeError("connection failed"))

        assert len(events) == 1
        assert events[0][1] == "HAYSTACK_PIPELINE_ERROR"
        assert events[0][2]["error"] == "connection failed"
        assert events[0][2]["error_type"] == "RuntimeError"

    def test_component_events(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_component_start("retriever", "BM25Retriever")
        handler.on_component_end("retriever", "BM25Retriever", duration_ms=50)

        assert len(events) == 2
        assert events[0][1] == "HAYSTACK_COMPONENT_START"
        assert events[1][1] == "HAYSTACK_COMPONENT_END"

    def test_component_error_event(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_component_error("generator", "OpenAIGenerator", ValueError("bad input"))

        assert len(events) == 1
        assert events[0][1] == "HAYSTACK_COMPONENT_ERROR"
        assert events[0][2]["error"] == "bad input"

    def test_sequence_numbers_increment(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_pipeline_start("pipe", 2, {})
        handler.on_component_start("a", "CompA")
        handler.on_component_end("a", "CompA")

        assert events[0][2]["sequence"] == 0
        assert events[1][2]["sequence"] == 1
        assert events[2][2]["sequence"] == 2

    def test_events_have_timestamps(self):
        events = []
        handler = HaystackEventHandler("run-001", lambda rid, et, d: events.append((rid, et, d)))

        handler.on_pipeline_start("pipe", 1, {})

        assert "timestamp" in events[0][2]


class TestRunHaystackPipeline:
    """Test run_haystack_pipeline gated execution."""

    def test_raises_when_gate_not_set(self, monkeypatch):
        monkeypatch.delenv(HAYSTACK_RUNNER_GATE_ENV, raising=False)

        mock_pipeline = Mock()
        events = []

        with pytest.raises(RuntimeError, match="gated"):
            run_haystack_pipeline(
                mock_pipeline,
                {"query": "test"},
                "run-001",
                lambda rid, et, d: events.append((rid, et, d)),
            )

        mock_pipeline.run.assert_not_called()

    def test_executes_when_gate_set(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "1")

        mock_pipeline = Mock()
        mock_pipeline.run.return_value = {"answer": "42"}
        mock_pipeline._components = {"a": Mock(), "b": Mock()}
        events = []

        result = run_haystack_pipeline(
            mock_pipeline,
            {"query": "test"},
            "run-001",
            lambda rid, et, d: events.append((rid, et, d)),
        )

        assert result == {"answer": "42"}
        mock_pipeline.run.assert_called_once_with({"query": "test"})
        assert any(e[1] == "HAYSTACK_PIPELINE_START" for e in events)
        assert any(e[1] == "HAYSTACK_PIPELINE_END" for e in events)

    def test_emits_error_on_failure(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "1")

        mock_pipeline = Mock()
        mock_pipeline.run.side_effect = RuntimeError("pipeline failed")
        mock_pipeline._components = {}
        events = []

        with pytest.raises(RuntimeError, match="pipeline failed"):
            run_haystack_pipeline(
                mock_pipeline,
                {"query": "test"},
                "run-001",
                lambda rid, et, d: events.append((rid, et, d)),
            )

        assert any(e[1] == "HAYSTACK_PIPELINE_ERROR" for e in events)

    def test_custom_pipeline_name(self, monkeypatch):
        monkeypatch.setenv(HAYSTACK_RUNNER_GATE_ENV, "1")

        mock_pipeline = Mock()
        mock_pipeline.run.return_value = {}
        mock_pipeline._components = {}
        events = []

        run_haystack_pipeline(
            mock_pipeline,
            {},
            "run-001",
            lambda rid, et, d: events.append((rid, et, d)),
            pipeline_name="my_rag_pipeline",
        )

        start_event = [e for e in events if e[1] == "HAYSTACK_PIPELINE_START"][0]
        assert start_event[2]["pipeline_name"] == "my_rag_pipeline"
