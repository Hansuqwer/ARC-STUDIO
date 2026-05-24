"""Tests for mapper divergence and consistency."""

import time

import agent_runtime_cockpit.adapters.ag2.mapping  # noqa: F401
import agent_runtime_cockpit.adapters.crewai.mapping  # noqa: F401
import agent_runtime_cockpit.adapters.langgraph.mapping  # noqa: F401

# Import mappers to register them
import agent_runtime_cockpit.adapters.swarmgraph.mapping  # noqa: F401
from agent_runtime_cockpit.ag_ui import MappingContext, map_event


class TestMapperConsistency:
    """Test that all mappers follow consistent patterns."""

    def test_all_mappers_preserve_native_timestamp(self):
        """Test that mappers preserve native timestamp if provided."""
        native_ts = 1234567890.123

        test_cases = [
            ("swarmgraph", {"ts": native_ts, "kind": "run.start"}),
            ("langgraph", {"timestamp": native_ts, "event": "on_chain_start", "name": "test"}),
            ("crewai", {"timestamp": native_ts, "kind": "crew.start"}),
            ("ag2", {"timestamp": native_ts, "event": "run.start"}),
        ]

        for runtime, native in test_cases:
            ctx = MappingContext(thread_id="test-thread", run_id="test-run", runtime=runtime)

            events = map_event(runtime, native, ctx)

            # All events should have the native timestamp (or close to it)
            for event in events:
                assert "timestamp" in event, f"{runtime}: Missing timestamp"
                # Allow small delta for time.time() calls
                assert abs(event["timestamp"] - native_ts) < 1.0, (
                    f"{runtime}: Timestamp divergence too large: {abs(event['timestamp'] - native_ts)}"
                )

    def test_all_mappers_include_required_fields(self):
        """Test that all mappers include required fields."""
        runtimes = ["swarmgraph", "langgraph", "crewai", "ag2"]

        for runtime in runtimes:
            ctx = MappingContext(thread_id="test-thread", run_id="test-run", runtime=runtime)

            native = {"kind": "test.event", "event": "test.event"}
            events = map_event(runtime, native, ctx)

            for event in events:
                assert "type" in event, f"{runtime}: Missing type"
                assert "timestamp" in event, f"{runtime}: Missing timestamp"
                assert "threadId" in event, f"{runtime}: Missing threadId"
                assert "runId" in event, f"{runtime}: Missing runId"

    def test_message_id_consistency(self):
        """Test that messageId generation is consistent."""
        runtimes = ["swarmgraph", "crewai", "ag2"]

        for runtime in runtimes:
            ctx = MappingContext(thread_id="test-thread", run_id="test-run", runtime=runtime)

            # Create text message event
            native = {
                "kind": "agent.text" if runtime in ["swarmgraph", "crewai"] else "message",
                "event": "message" if runtime == "ag2" else "agent.text",
                "text": "test message",
                "content": "test message",
                "timestamp": time.time(),
            }

            events = map_event(runtime, native, ctx)

            # Find TEXT_MESSAGE_START event
            start_events = [e for e in events if "TEXT_MESSAGE_START" in e.get("type", "")]
            if start_events:
                event = start_events[0]
                assert "messageId" in event, f"{runtime}: Missing messageId"
                # messageId should contain run_id
                assert ctx.run_id in event["messageId"], (
                    f"{runtime}: messageId doesn't contain run_id"
                )

    def test_raw_event_fallback_consistency(self):
        """Test that RAW event fallback is consistent."""
        runtimes = ["swarmgraph", "langgraph", "crewai", "ag2"]

        for runtime in runtimes:
            ctx = MappingContext(thread_id="test-thread", run_id="test-run", runtime=runtime)

            # Unknown event type
            native = {"kind": "unknown.event", "event": "unknown.event"}
            events = map_event(runtime, native, ctx)

            assert len(events) == 1, f"{runtime}: Should return 1 RAW event"
            event = events[0]

            assert event["type"] == "RAW", f"{runtime}: Should be RAW event"
            assert "timestamp" in event, f"{runtime}: RAW missing timestamp"
            assert "source" in event, f"{runtime}: RAW missing source"
            assert event["source"] == runtime, f"{runtime}: Wrong source"


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
