"""Tests for MCPContextPropagator — W3C traceparent round-trip through JSON-RPC _meta.

No live network. All synthetic JSON-RPC messages.
"""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.observability.openinference_mapping import MCPContextPropagator


@pytest.fixture
def propagator():
    return MCPContextPropagator()


TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN_ID = "00f067aa0ba902b7"


class TestInject:
    def test_inject_creates_traceparent_in_meta(self, propagator):
        msg = propagator.inject(TRACE_ID, SPAN_ID)
        tp = msg["params"]["_meta"]["traceparent"]
        assert tp == f"00-{TRACE_ID}-{SPAN_ID}-01"

    def test_inject_into_existing_message(self, propagator):
        msg = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "read_file"}}
        result = propagator.inject(TRACE_ID, SPAN_ID, message=msg)
        assert result["params"]["_meta"]["traceparent"] == f"00-{TRACE_ID}-{SPAN_ID}-01"
        assert result["params"]["name"] == "read_file"

    def test_inject_preserves_existing_meta(self, propagator):
        msg = {"params": {"_meta": {"progressToken": "abc"}}}
        result = propagator.inject(TRACE_ID, SPAN_ID, message=msg)
        assert result["params"]["_meta"]["progressToken"] == "abc"
        assert "traceparent" in result["params"]["_meta"]

    def test_inject_custom_flags(self, propagator):
        msg = propagator.inject(TRACE_ID, SPAN_ID, trace_flags="00")
        tp = msg["params"]["_meta"]["traceparent"]
        assert tp.endswith("-00")


class TestExtract:
    def test_extract_valid_traceparent(self, propagator):
        msg = {"params": {"_meta": {"traceparent": f"00-{TRACE_ID}-{SPAN_ID}-01"}}}
        result = propagator.extract(msg)
        assert result == ("00", TRACE_ID, SPAN_ID, "01")

    def test_extract_returns_none_when_no_params(self, propagator):
        assert propagator.extract({}) is None

    def test_extract_returns_none_when_no_meta(self, propagator):
        assert propagator.extract({"params": {"name": "foo"}}) is None

    def test_extract_returns_none_when_meta_not_dict(self, propagator):
        assert propagator.extract({"params": {"_meta": "invalid"}}) is None

    def test_extract_returns_none_for_invalid_format(self, propagator):
        msg = {"params": {"_meta": {"traceparent": "not-valid"}}}
        assert propagator.extract(msg) is None

    def test_extract_returns_none_for_missing_traceparent(self, propagator):
        msg = {"params": {"_meta": {"other": "value"}}}
        assert propagator.extract(msg) is None


class TestRoundTrip:
    def test_inject_then_extract(self, propagator):
        msg = propagator.inject(TRACE_ID, SPAN_ID)
        result = propagator.extract(msg)
        assert result is not None
        version, trace_id, span_id, flags = result
        assert trace_id == TRACE_ID
        assert span_id == SPAN_ID
        assert version == "00"
        assert flags == "01"

    def test_roundtrip_through_jsonrpc_request(self, propagator):
        """Simulate full JSON-RPC MCP tool call with traceparent."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"path": "/workspace/file.txt"},
            },
        }
        injected = propagator.inject(TRACE_ID, SPAN_ID, message=request)
        # Verify structure preserved
        assert injected["method"] == "tools/call"
        assert injected["params"]["name"] == "read_file"
        assert injected["params"]["arguments"]["path"] == "/workspace/file.txt"
        # Verify traceparent
        extracted = propagator.extract(injected)
        assert extracted == ("00", TRACE_ID, SPAN_ID, "01")


class TestGracefulFallback:
    def test_non_dict_params_no_crash(self, propagator):
        msg = {"params": [1, 2, 3]}
        result = propagator.inject(TRACE_ID, SPAN_ID, message=msg)
        # params is not a dict, so injection is a no-op
        assert result["params"] == [1, 2, 3]

    def test_extract_non_dict_params_returns_none(self, propagator):
        assert propagator.extract({"params": [1, 2]}) is None
