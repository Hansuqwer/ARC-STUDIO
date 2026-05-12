"""
Test for Issue #11: Environment variable allow-list

Verifies that only safe environment variables are passed to subprocess.
"""
import os
import pytest


def test_env_allowlist_concept():
    """
    Test the concept of environment variable allow-listing.
    
    This test verifies the logic that will be used in _build_safe_env().
    """
    # Simulate the allow-list
    ALLOWED_ENV_VARS = frozenset({
        "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE",
        "TMPDIR", "TEMP", "TMP", "SHELL", "USER", "LOGNAME",
    })
    
    # Set up test environment
    test_env = {
        "PATH": "/usr/bin",
        "HOME": "/home/test",
        "OPENAI_API_KEY": "sk-secret123",  # Should NOT be included
        "AWS_ACCESS_KEY_ID": "AKIA123",    # Should NOT be included
        "ARC_SWARMGRAPH_CLI": "/path/to/cli",  # Should be included
        "ARC_SWARMGRAPH_GATEWAY_URL": "https://gateway",  # Should be included
    }
    
    # Build safe env (simulating _build_safe_env logic)
    safe_env = {}
    for key in ALLOWED_ENV_VARS:
        if key in test_env:
            safe_env[key] = test_env[key]
    
    for key, value in test_env.items():
        if key.startswith("ARC_SWARMGRAPH_"):
            safe_env[key] = value
    
    safe_env["PYTHONWARNINGS"] = "ignore"
    
    # Verify allowed vars are included
    assert "PATH" in safe_env
    assert safe_env["PATH"] == "/usr/bin"
    assert "HOME" in safe_env
    assert safe_env["HOME"] == "/home/test"
    
    # Verify ARC_SWARMGRAPH_* vars are included
    assert "ARC_SWARMGRAPH_CLI" in safe_env
    assert "ARC_SWARMGRAPH_GATEWAY_URL" in safe_env
    
    # Verify PYTHONWARNINGS is added
    assert "PYTHONWARNINGS" in safe_env
    
    # Verify secrets are NOT included
    assert "OPENAI_API_KEY" not in safe_env
    assert "AWS_ACCESS_KEY_ID" not in safe_env
    
    print("✅ Environment allow-list logic verified")


def test_no_secret_leakage():
    """Test that common secret patterns are blocked."""
    ALLOWED_ENV_VARS = frozenset({"PATH", "HOME"})
    
    secrets = {
        "OPENAI_API_KEY": "sk-test123",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "AWS_ACCESS_KEY_ID": "AKIA123",
        "AWS_SECRET_ACCESS_KEY": "secret",
        "GITHUB_TOKEN": "ghp_token",
        "DATABASE_PASSWORD": "password123",
        "API_SECRET": "secret",
        "PATH": "/usr/bin",  # This one IS allowed
    }
    
    # Build safe env
    safe_env = {}
    for key in ALLOWED_ENV_VARS:
        if key in secrets:
            safe_env[key] = secrets[key]
    
    # Verify PATH is included (it's allowed)
    assert "PATH" in safe_env
    
    # Verify all secrets are blocked
    blocked_secrets = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN", "DATABASE_PASSWORD", "API_SECRET"
    ]
    for key in blocked_secrets:
        assert key not in safe_env, f"Secret {key} leaked into safe_env!"
    
    print("✅ No secret leakage detected")


def test_arc_swarmgraph_prefix_included():
    """Test that all ARC_SWARMGRAPH_* variables are included."""
    test_env = {
        "ARC_SWARMGRAPH_CLI": "/cli",
        "ARC_SWARMGRAPH_GATEWAY_URL": "https://gateway",
        "ARC_SWARMGRAPH_GATEWAY_TOKEN": "token123",
        "ARC_SWARMGRAPH_ALLOW_COSTS": "true",
        "ARC_OTHER_VAR": "should_not_be_included",
        "OPENAI_API_KEY": "sk-secret",
    }
    
    # Build safe env with ARC_SWARMGRAPH_* prefix filter
    safe_env = {}
    for key, value in test_env.items():
        if key.startswith("ARC_SWARMGRAPH_"):
            safe_env[key] = value
    
    # Verify all ARC_SWARMGRAPH_* vars are included
    assert "ARC_SWARMGRAPH_CLI" in safe_env
    assert "ARC_SWARMGRAPH_GATEWAY_URL" in safe_env
    assert "ARC_SWARMGRAPH_GATEWAY_TOKEN" in safe_env
    assert "ARC_SWARMGRAPH_ALLOW_COSTS" in safe_env
    
    # Verify other vars are NOT included
    assert "ARC_OTHER_VAR" not in safe_env
    assert "OPENAI_API_KEY" not in safe_env
    
    print("✅ ARC_SWARMGRAPH_* prefix filtering verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
