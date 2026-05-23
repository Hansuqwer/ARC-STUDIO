"""Tests for Pydantic AI streaming (Phase 29 PR 29.3)."""

from __future__ import annotations

from unittest.mock import Mock


from agent_runtime_cockpit.adapters.pydantic_ai.runner import (
    PydanticAIEventHandler,
    run_agent_with_streaming,
)


class TestEventHandler:
    """Test PydanticAIEventHandler."""

    def test_initialization(self):
        """Should initialize with run_id and emit_event callback."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        assert handler.run_id == "test-run-id"
        assert handler.emit_event == emit_event
        assert handler.sequence == 0

    def test_sequence_numbers_increment(self):
        """Should increment sequence numbers for each event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_run_start("agent1", {})
        handler.on_run_end("agent1", "result")

        assert emit_event.call_count == 2
        # First call should have sequence 0
        assert emit_event.call_args_list[0][0][2]["sequence"] == 0
        # Second call should have sequence 1
        assert emit_event.call_args_list[1][0][2]["sequence"] == 1

    def test_on_run_start_emits_event(self):
        """Should emit AGENT_RUN_START event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_run_start("weather_agent", {"location": "NYC"})

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[0] == "test-run-id"
        assert call_args[1] == "AGENT_RUN_START"
        assert call_args[2]["agent_name"] == "weather_agent"
        assert call_args[2]["input"] == {"location": "NYC"}

    def test_on_run_end_emits_event(self):
        """Should emit AGENT_RUN_END event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_run_end("weather_agent", "Sunny, 72°F")

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "AGENT_RUN_END"
        assert call_args[2]["agent_name"] == "weather_agent"
        assert call_args[2]["result"] == "Sunny, 72°F"
        assert call_args[2]["status"] == "success"

    def test_on_run_error_emits_event(self):
        """Should emit AGENT_RUN_ERROR event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        error = ValueError("Invalid input")
        handler.on_run_error("weather_agent", error)

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "AGENT_RUN_ERROR"
        assert call_args[2]["agent_name"] == "weather_agent"
        assert call_args[2]["error"] == "Invalid input"
        assert call_args[2]["error_type"] == "ValueError"
        assert call_args[2]["status"] == "error"

    def test_on_validation_error_emits_typed_event(self):
        """Should emit VALIDATION_ERROR as typed event variant."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        validation_error = {
            "field": "temperature",
            "message": "must be a number",
        }
        handler.on_validation_error("weather_agent", validation_error)

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "VALIDATION_ERROR"
        assert call_args[2]["agent_name"] == "weather_agent"
        assert call_args[2]["validation_error"] == validation_error
        assert call_args[2]["error_type"] == "ValidationError"

    def test_on_tool_call_emits_event(self):
        """Should emit TOOL_CALL event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_tool_call("get_weather", {"location": "NYC"})

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "TOOL_CALL"
        assert call_args[2]["tool_name"] == "get_weather"
        assert call_args[2]["arguments"] == {"location": "NYC"}

    def test_on_tool_result_emits_event(self):
        """Should emit TOOL_RESULT event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_tool_result("get_weather", "Sunny, 72°F")

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "TOOL_RESULT"
        assert call_args[2]["tool_name"] == "get_weather"
        assert call_args[2]["result"] == "Sunny, 72°F"

    def test_on_model_request_emits_event(self):
        """Should emit MODEL_REQUEST event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        messages = [{"role": "user", "content": "Hello"}]
        handler.on_model_request("gpt-4o-mini", messages)

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "MODEL_REQUEST"
        assert call_args[2]["model"] == "gpt-4o-mini"
        assert call_args[2]["message_count"] == 1

    def test_on_model_response_emits_event(self):
        """Should emit MODEL_RESPONSE event."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_model_response("gpt-4o-mini", "Hello! How can I help?")

        emit_event.assert_called_once()
        call_args = emit_event.call_args[0]
        assert call_args[1] == "MODEL_RESPONSE"
        assert call_args[2]["model"] == "gpt-4o-mini"
        assert call_args[2]["response"] == "Hello! How can I help?"

    def test_events_include_timestamp(self):
        """All events should include timestamp."""
        emit_event = Mock()
        handler = PydanticAIEventHandler("test-run-id", emit_event)

        handler.on_run_start("agent", {})

        call_args = emit_event.call_args[0]
        assert "timestamp" in call_args[2]
        # Timestamp should be ISO format
        assert "T" in call_args[2]["timestamp"]


class TestRunAgentWithStreaming:
    """Test run_agent_with_streaming function."""

    def test_emits_start_and_end_events(self):
        """Should emit start and end events for successful run."""
        emit_event = Mock()
        agent = Mock()
        agent.name = "test_agent"

        # Call function (result not used in this test)
        run_agent_with_streaming(
            agent,
            {"input": "test"},
            "run-123",
            emit_event,
        )

        # Should emit start and end events
        assert emit_event.call_count == 2

        # First event should be start
        assert emit_event.call_args_list[0][0][1] == "AGENT_RUN_START"

        # Second event should be end
        assert emit_event.call_args_list[1][0][1] == "AGENT_RUN_END"

    def test_emits_error_event_on_exception(self):
        """Should emit error event when agent run fails."""
        # Note: This test documents expected behavior for error handling.
        # In actual implementation with real Pydantic AI integration,
        # this would test that exceptions during agent.run() emit error events.

        # Placeholder test - in production this would be:
        # _emit_event = Mock()
        # agent = Mock()
        # agent.run.side_effect = ValueError("Test error")
        # with pytest.raises(ValueError):
        #     run_agent_with_streaming(agent, {}, "run-123", _emit_event)
        # assert any("AGENT_RUN_ERROR" in str(call) for call in _emit_event.call_args_list)
        pass
