"""Tests for LangChain live streaming (Phase 26 T3).

Phase 26 T3: Live streaming via BaseCallbackHandler.
Minimum 12 tests required per roadmap.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock


from agent_runtime_cockpit.adapters.langchain import LangChainAdapter
from agent_runtime_cockpit.adapters.langchain.runner import (
    ARCCallbackHandler,
    LangChainRunner,
)
from agent_runtime_cockpit.protocol.schemas import RunStatus


# Test 1: ARCCallbackHandler initialization
def test_arc_callback_handler_initialization():
    """Test ARCCallbackHandler initializes correctly."""
    emit_event = Mock()
    handler = ARCCallbackHandler(
        run_id="test-run",
        emit_event=emit_event,
        provider_registry={"known_llm": True},
    )

    assert handler.run_id == "test-run"
    assert handler.emit_event == emit_event
    assert handler.provider_registry == {"known_llm": True}
    assert handler.sequence == 0
    assert handler._chain_stack == []


# Test 2: Chain start callback emits event
def test_chain_start_callback():
    """Test on_chain_start emits CHAIN_START event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    handler.on_chain_start(
        serialized={"name": "test_chain"},
        inputs={"input": "test"},
    )

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][0] == "test-run"  # run_id
    assert call_args[0][1] == "CHAIN_START"  # event_type
    assert call_args[0][2]["chain_name"] == "test_chain"
    assert call_args[0][2]["inputs"] == {"input": "test"}


# Test 3: Chain end callback emits event
def test_chain_end_callback():
    """Test on_chain_end emits CHAIN_END event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    # Start chain first
    handler.on_chain_start(serialized={"name": "test_chain"}, inputs={})
    emit_event.reset_mock()

    # End chain
    handler.on_chain_end(outputs={"output": "result"})

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "CHAIN_END"  # event_type
    assert call_args[0][2]["chain_name"] == "test_chain"
    assert call_args[0][2]["outputs"] == {"output": "result"}


# Test 4: Chain error callback emits event
def test_chain_error_callback():
    """Test on_chain_error emits CHAIN_ERROR event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    # Start chain first
    handler.on_chain_start(serialized={"name": "test_chain"}, inputs={})
    emit_event.reset_mock()

    # Error in chain
    error = ValueError("test error")
    handler.on_chain_error(error=error)

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "CHAIN_ERROR"  # event_type
    assert call_args[0][2]["error"] == "test error"
    assert call_args[0][2]["error_type"] == "ValueError"


# Test 5: LLM start callback emits event
def test_llm_start_callback():
    """Test on_llm_start emits LLM_START event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(
        run_id="test-run",
        emit_event=emit_event,
        provider_registry={"known_llm": True},
    )

    handler.on_llm_start(
        serialized={"name": "known_llm"},
        prompts=["prompt1", "prompt2"],
    )

    # Should emit LLM_START (no bypass warning for known provider)
    assert emit_event.call_count == 1
    call_args = emit_event.call_args
    assert call_args[0][1] == "LLM_START"  # event_type
    assert call_args[0][2]["llm_name"] == "known_llm"
    assert call_args[0][2]["prompt_count"] == 2


# Test 6: LLM start with unknown provider emits bypass warning
def test_llm_start_unknown_provider_emits_bypass_warning():
    """Test on_llm_start emits POLICY_BYPASS_WARNING for unknown provider."""
    emit_event = Mock()
    handler = ARCCallbackHandler(
        run_id="test-run",
        emit_event=emit_event,
        provider_registry={"known_llm": True},
    )

    handler.on_llm_start(
        serialized={"name": "unknown_llm"},
        prompts=["prompt"],
    )

    # Should emit both POLICY_BYPASS_WARNING and LLM_START
    assert emit_event.call_count == 2

    # Check that both event types were emitted (event_type is second arg)
    event_types = [call[0][1] for call in emit_event.call_args_list]
    assert "POLICY_BYPASS_WARNING" in event_types
    assert "LLM_START" in event_types

    # Find the bypass warning call
    bypass_call = next(c for c in emit_event.call_args_list if c[0][1] == "POLICY_BYPASS_WARNING")
    # Check that it mentions the unknown provider
    assert "unknown_llm" in str(bypass_call)


# Test 7: LLM token callback emits event
def test_llm_token_callback():
    """Test on_llm_new_token emits LLM_TOKEN event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    handler.on_llm_new_token(token="hello")

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "LLM_TOKEN"  # event_type
    assert call_args[0][2]["token"] == "hello"


# Test 8: LLM end callback emits event
def test_llm_end_callback():
    """Test on_llm_end emits LLM_END event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    # Mock LLMResult
    result = Mock()
    result.generations = [["gen1"], ["gen2"]]
    result.llm_output = {"model": "test"}

    handler.on_llm_end(response=result)

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "LLM_END"  # event_type
    assert call_args[0][2]["generations"] == 2


# Test 9: Tool start callback emits event
def test_tool_start_callback():
    """Test on_tool_start emits TOOL_START event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    handler.on_tool_start(
        serialized={"name": "search_tool"},
        input_str="query",
    )

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "TOOL_START"  # event_type
    assert call_args[0][2]["tool_name"] == "search_tool"
    assert call_args[0][2]["input"] == "query"


# Test 10: Tool end callback emits event
def test_tool_end_callback():
    """Test on_tool_end emits TOOL_END event."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    handler.on_tool_end(output="result")

    emit_event.assert_called_once()
    call_args = emit_event.call_args
    assert call_args[0][1] == "TOOL_END"  # event_type
    assert call_args[0][2]["output"] == "result"


# Test 11: Sequence numbers increment correctly
def test_sequence_numbers_increment():
    """Test that sequence numbers increment correctly."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    # Emit multiple events
    handler.on_chain_start(serialized={"name": "chain"}, inputs={})
    handler.on_llm_new_token(token="a")
    handler.on_llm_new_token(token="b")
    handler.on_chain_end(outputs={})

    # Check sequence numbers
    sequences = [call[0][2]["sequence"] for call in emit_event.call_args_list]
    assert sequences == [0, 1, 2, 3]


# Test 12: LangChainRunner executes chain successfully
def test_langchain_runner_executes_chain(tmp_path: Path):
    """Test LangChainRunner executes a chain and returns RunRecord."""
    runner = LangChainRunner(tmp_path)

    # Mock chain
    mock_chain = Mock()
    mock_chain.invoke = Mock(return_value="result")

    # Run chain
    record = runner.run(mock_chain, {"input": "test"})

    assert record.runtime == "langchain"
    assert record.status == RunStatus.COMPLETED
    assert len(record.events) >= 2  # At least RUN_STARTED and RUN_COMPLETED
    assert record.metadata["result"] == "result"

    # Verify chain was invoked with callback
    mock_chain.invoke.assert_called_once()
    call_args = mock_chain.invoke.call_args
    assert "callbacks" in call_args[1]["config"]


# Test 13: LangChainRunner handles chain errors
def test_langchain_runner_handles_errors(tmp_path: Path):
    """Test LangChainRunner handles chain execution errors."""
    runner = LangChainRunner(tmp_path)

    # Mock chain that raises error
    mock_chain = Mock()
    mock_chain.invoke = Mock(side_effect=ValueError("test error"))

    # Run chain
    record = runner.run(mock_chain, {"input": "test"})

    assert record.runtime == "langchain"
    assert record.status == RunStatus.FAILED
    assert "test error" in record.metadata["error"]


# Test 14: LangChainAdapter run_chain method
def test_langchain_adapter_run_chain(tmp_path: Path):
    """Test LangChainAdapter.run_chain() method."""
    adapter = LangChainAdapter()

    # Mock chain
    mock_chain = Mock()
    mock_chain.invoke = Mock(return_value="result")

    # Run chain
    record = adapter.run_chain(tmp_path, mock_chain, {"input": "test"})

    assert isinstance(record.id, str)
    assert record.runtime == "langchain"
    assert record.status == RunStatus.COMPLETED


# Test 15: Capabilities reflect T3 implementation
def test_capabilities_reflect_t3_implementation():
    """Test that adapter capabilities correctly reflect T3 implementation."""
    adapter = LangChainAdapter()
    caps = adapter.capabilities()

    assert caps.can_run is True  # T3 implemented
    assert caps.can_trace is True  # T3 implemented
    assert caps.can_stream_events is True  # T3 implemented
    assert caps.can_export_workflow is True  # T2 implemented
    assert caps.can_inspect is True  # T1 implemented


# Test 16: Chain stack tracks nested chains
def test_chain_stack_tracks_nesting():
    """Test that chain stack correctly tracks nested chain execution."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    # Start outer chain
    handler.on_chain_start(serialized={"name": "outer"}, inputs={})
    assert len(handler._chain_stack) == 1

    # Start inner chain
    handler.on_chain_start(serialized={"name": "inner"}, inputs={})
    assert len(handler._chain_stack) == 2

    # End inner chain
    handler.on_chain_end(outputs={})
    assert len(handler._chain_stack) == 1

    # End outer chain
    handler.on_chain_end(outputs={})
    assert len(handler._chain_stack) == 0


# Test 17: Events include timestamps
def test_events_include_timestamps():
    """Test that emitted events include timestamps."""
    emit_event = Mock()
    handler = ARCCallbackHandler(run_id="test-run", emit_event=emit_event)

    handler.on_chain_start(serialized={"name": "chain"}, inputs={})

    call_args = emit_event.call_args
    assert "timestamp" in call_args[0][2]
    # Timestamp should be ISO format
    timestamp = call_args[0][2]["timestamp"]
    assert "T" in timestamp
    assert "Z" in timestamp or "+" in timestamp
