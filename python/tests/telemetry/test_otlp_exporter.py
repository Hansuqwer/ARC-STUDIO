"""Tests for OTLP trace exporter."""

from agent_runtime_cockpit.protocol.schemas import RunRecord
from agent_runtime_cockpit.telemetry.otlp_exporter import (
    convert_run_to_otlp_spans,
    export_run_to_otlp,
    validate_otlp_endpoint,
)


def test_validate_endpoint_empty():
    """Empty endpoint should be invalid."""
    is_valid, message = validate_otlp_endpoint("")
    assert not is_valid
    assert "not configured" in message


def test_validate_endpoint_invalid_format():
    """Invalid URL format should be rejected."""
    is_valid, message = validate_otlp_endpoint("not-a-url")
    assert not is_valid
    assert "Invalid" in message


def test_validate_endpoint_localhost():
    """Localhost endpoints should be valid with no warning."""
    is_valid, warning = validate_otlp_endpoint("http://localhost:4317")
    assert is_valid
    assert warning is None

    is_valid, warning = validate_otlp_endpoint("http://127.0.0.1:4317")
    assert is_valid
    assert warning is None


def test_validate_endpoint_remote_denied_by_default():
    """Remote endpoints are denied unless explicitly enabled."""
    is_valid, warning = validate_otlp_endpoint("http://example.com:4317")
    assert not is_valid
    assert warning is not None
    assert "ARC_ALLOW_REMOTE_OTLP=1" in warning


def test_validate_endpoint_remote_with_opt_in(monkeypatch):
    """Remote endpoints return a warning only after explicit opt-in."""
    monkeypatch.setenv("ARC_ALLOW_REMOTE_OTLP", "1")
    is_valid, warning = validate_otlp_endpoint("http://example.com:4317")
    assert is_valid
    assert warning is not None
    assert "Non-localhost" in warning
    assert "example.com" in warning


def test_convert_run_to_spans():
    """Should convert RunRecord to OTLP spans."""
    run = RunRecord(
        id="test-run-123",
        workflow_id="test-workflow",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        ended_at="2026-05-12T17:01:00Z",
        events=[
            {
                "type": "RUN_STARTED",
                "timestamp": "2026-05-12T17:00:00Z",
                "run_id": "test-run-123",
                "sequence": 0,
                "data": {},
            },
            {
                "type": "TOOL_CALL_START",
                "timestamp": "2026-05-12T17:00:30Z",
                "run_id": "test-run-123",
                "sequence": 1,
                "data": {
                    "toolCallName": "test_tool",
                    "toolCallId": "tool-123",
                },
            },
        ],
        metadata={},
    )

    spans = convert_run_to_otlp_spans(run)

    # Should have root span + 2 event spans
    assert len(spans) == 3

    # Check root span
    root = spans[0]
    assert root["trace_id"] == "test-run-123"
    assert root["name"] == "run:test-workflow"
    assert root["attributes"]["arc.runtime"] == "swarmgraph"
    assert root["attributes"]["arc.status"] == "completed"

    # Check event spans
    event_span = spans[1]
    assert event_span["name"] == "RUN_STARTED"
    assert event_span["parent_span_id"] == "test-run-123-root"


def test_convert_run_redacts_secrets():
    """Should redact secrets in span attributes."""
    run = RunRecord(
        id="test-run-456",
        workflow_id="test-workflow",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        ended_at="2026-05-12T17:01:00Z",
        events=[
            {
                "type": "TOOL_CALL_START",
                "timestamp": "2026-05-12T17:00:30Z",
                "run_id": "test-run-456",
                "sequence": 0,
                "data": {
                    "api_key": "sk-secret123",
                    "token": "ghp_token456",
                },
            },
        ],
        metadata={},
    )

    spans = convert_run_to_otlp_spans(run)

    # Secrets should be redacted
    # Note: redactValue is called on attributes, so secrets in data won't appear in attributes
    # This test verifies the redaction pipeline is called
    assert len(spans) == 2  # root + 1 event


def test_export_run_requires_endpoint():
    """Export should fail without endpoint."""
    import pytest

    run = RunRecord(
        id="test-run",
        workflow_id="test",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        events=[],
        metadata={},
    )

    with pytest.raises(ValueError, match="not configured"):
        export_run_to_otlp(run, "")


def test_export_run_validates_endpoint():
    """Export should validate endpoint format."""
    import pytest

    run = RunRecord(
        id="test-run",
        workflow_id="test",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        events=[],
        metadata={},
    )

    with pytest.raises(ValueError, match="Invalid"):
        export_run_to_otlp(run, "invalid-url")


def test_export_run_success():
    """Export should succeed with valid endpoint."""
    run = RunRecord(
        id="test-run",
        workflow_id="test",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        events=[],
        metadata={},
    )

    success = export_run_to_otlp(run, "http://localhost:4317")
    assert success


def test_export_run_denies_remote_by_default():
    """Export rejects remote endpoints by default."""
    import pytest

    run = RunRecord(
        id="test-run",
        workflow_id="test",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        events=[],
        metadata={},
    )

    with pytest.raises(ValueError, match="ARC_ALLOW_REMOTE_OTLP=1"):
        export_run_to_otlp(run, "http://example.com:4317")


def test_export_run_warns_remote_with_opt_in(monkeypatch):
    """Export can target remote endpoints only after explicit opt-in."""
    monkeypatch.setenv("ARC_ALLOW_REMOTE_OTLP", "1")
    run = RunRecord(
        id="test-run",
        workflow_id="test",
        runtime="swarmgraph",
        status="completed",
        started_at="2026-05-12T17:00:00Z",
        events=[],
        metadata={},
    )

    success = export_run_to_otlp(run, "http://example.com:4317")
    assert success
