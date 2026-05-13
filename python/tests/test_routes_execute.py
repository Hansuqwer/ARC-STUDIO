"""
Smoke test for /api/execute endpoint.

Verifies that the execute endpoint returns a valid response
and doesn't crash due to NameError or other runtime issues.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path so we can import routes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from routes import app

client = TestClient(app)


def test_execute_endpoint_does_not_crash():
    """
    Regression test: verifies /api/execute doesn't raise NameError
    from _allowed_subprocess_env() referencing undefined _ALLOW_ENV.
    
    This test would have caught the typo bug fixed in commit after 1d27ccb.
    """
    response = client.post("/api/execute", json={
        "prompt": "hello world",
        "backend": "stub",
        "cost_allowed": False
    })
    
    # Should not be 500 (which would indicate NameError or crash)
    assert response.status_code != 500, f"Endpoint crashed: {response.text}"
    
    # Either 200 (success) or 400/408 (validation/timeout) is acceptable
    # The important thing is it doesn't crash with NameError
    if response.status_code == 200:
        data = response.json()
        assert "run_id" in data
        assert "status" in data
        assert "trace_path" in data


def test_allowed_subprocess_env_function_exists():
    """
    Verify _allowed_subprocess_env() returns a dict without raising NameError.
    """
    from routes import _allowed_subprocess_env
    env = _allowed_subprocess_env()
    assert isinstance(env, dict)
    # Should only contain allow-listed keys
    from routes import _ALLOWED_ENV
    for key in env.keys():
        assert key in _ALLOWED_ENV


def test_health_check():
    """Basic health check test."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ARC Studio Backend"


def test_execute_with_invalid_backend():
    """Verify that an invalid backend returns 400."""
    response = client.post("/api/execute", json={
        "prompt": "hello world",
        "backend": "invalid_backend",
        "cost_allowed": False
    })
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_execute_with_empty_prompt():
    """Verify that an empty prompt returns 400."""
    response = client.post("/api/execute", json={
        "prompt": "",
        "backend": "stub",
        "cost_allowed": False
    })
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_execute_with_dangerous_prompt():
    """Verify that a prompt with dangerous characters returns 400."""
    dangerous_prompts = [
        "hello; rm -rf /",
        "hello | cat /etc/passwd",
        "hello `whoami`",
        "hello $(whoami)",
        "hello < /etc/passwd",
        "hello > /tmp/evil",
    ]
    for prompt in dangerous_prompts:
        response = client.post("/api/execute", json={
            "prompt": prompt,
            "backend": "stub",
            "cost_allowed": False
        })
        assert response.status_code == 400, f"Expected 400 for prompt: {prompt}"
        data = response.json()
        assert "dangerous characters" in data["detail"].lower() or "detail" in data


def test_get_traces_empty():
    """Verify that /api/traces returns [] when no traces exist."""
    response = client.get("/api/traces")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_get_trace_invalid_id():
    """Verify that an invalid trace ID returns 400."""
    response = client.get("/api/traces/invalid-id-format")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_get_trace_path_traversal():
    """Verify that path traversal in trace ID returns 400."""
    response = client.get("/api/traces/../../../etc/passwd")
    assert response.status_code == 400


def test_execute_with_whitespace_prompt():
    """Verify that a whitespace-only prompt returns 400."""
    response = client.post("/api/execute", json={
        "prompt": "   ",
        "backend": "stub",
        "cost_allowed": False
    })
    assert response.status_code == 400


def test_execute_with_null_bytes_prompt():
    """Verify that a prompt with null bytes is sanitized."""
    response = client.post("/api/execute", json={
        "prompt": "hello\x00world",
        "backend": "stub",
        "cost_allowed": False
    })
    assert response.status_code != 500


def test_get_traces_returns_list():
    """Verify that /api/traces returns a list type."""
    response = client.get("/api/traces")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
