#!/usr/bin/env python3
"""
Manual test runner for SwarmGraph security features.
Bypasses pytest import issues by running tests directly.
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Now we can import normally
from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter, SWARMGRAPH_ENV_ALLOWLIST

def test_filtered_env_blocks_api_keys():
    """Test that API keys are filtered out from subprocess environment."""
    print("TEST: test_filtered_env_blocks_api_keys")
    original_env = os.environ.copy()
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test123456789"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test123"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "aws-secret-123"
        os.environ["GITHUB_TOKEN"] = "ghp_test123456"
        
        adapter = SwarmGraphAdapter()
        filtered = adapter._filtered_env()
        
        # Verify secrets are NOT in filtered env
        assert "OPENAI_API_KEY" not in filtered, "OPENAI_API_KEY should be filtered"
        assert "ANTHROPIC_API_KEY" not in filtered, "ANTHROPIC_API_KEY should be filtered"
        assert "AWS_SECRET_ACCESS_KEY" not in filtered, "AWS_SECRET_ACCESS_KEY should be filtered"
        assert "GITHUB_TOKEN" not in filtered, "GITHUB_TOKEN should be filtered"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False
    finally:
        os.environ.clear()
        os.environ.update(original_env)

def test_filtered_env_allows_arc_swarmgraph_vars():
    """Test that ARC_SWARMGRAPH_* prefixed vars pass through."""
    print("TEST: test_filtered_env_allows_arc_swarmgraph_vars")
    original_env = os.environ.copy()
    try:
        os.environ["ARC_SWARMGRAPH_RUN_BACKEND"] = "local"
        os.environ["ARC_SWARMGRAPH_ALLOW_COSTS"] = "true"
        os.environ["ARC_SWARMGRAPH_CLI"] = "/usr/bin/swarmgraph"
        
        adapter = SwarmGraphAdapter()
        filtered = adapter._filtered_env()
        
        assert filtered["ARC_SWARMGRAPH_RUN_BACKEND"] == "local", "ARC_SWARMGRAPH_RUN_BACKEND should pass"
        assert filtered["ARC_SWARMGRAPH_ALLOW_COSTS"] == "true", "ARC_SWARMGRAPH_ALLOW_COSTS should pass"
        assert filtered["ARC_SWARMGRAPH_CLI"] == "/usr/bin/swarmgraph", "ARC_SWARMGRAPH_CLI should pass"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False
    finally:
        os.environ.clear()
        os.environ.update(original_env)

def test_filtered_env_allows_system_vars():
    """Test that allowlisted system vars pass through."""
    print("TEST: test_filtered_env_allows_system_vars")
    try:
        adapter = SwarmGraphAdapter()
        filtered = adapter._filtered_env()
        
        for key in SWARMGRAPH_ENV_ALLOWLIST:
            if key in os.environ:
                assert filtered[key] == os.environ[key], f"{key} should pass through"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False

def test_filtered_env_includes_pythonwarnings():
    """Test that PYTHONWARNINGS is always set to 'ignore'."""
    print("TEST: test_filtered_env_includes_pythonwarnings")
    try:
        adapter = SwarmGraphAdapter()
        filtered = adapter._filtered_env()
        
        assert filtered["PYTHONWARNINGS"] == "ignore", "PYTHONWARNINGS should be 'ignore'"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False

def test_output_redaction_api_keys():
    """Test that API keys in output are redacted."""
    print("TEST: test_output_redaction_api_keys")
    try:
        adapter = SwarmGraphAdapter()
        
        test_cases = [
            ("Error: OPENAI_API_KEY=sk-test123456789012345678901234567890", "sk-test123456789012345678901234567890"),
            ("Using key: sk-ant-api03-test123456", "sk-ant-api03-test123456"),
            ("Token: ghp_1234567890abcdef1234567890abcdef", "ghp_1234567890abcdef1234567890abcdef"),
        ]
        
        for output_with_secret, secret in test_cases:
            redacted = adapter._redactor.redact_string(output_with_secret)
            assert secret not in redacted, f"Secret '{secret}' should be redacted"
            assert "[REDACTED" in redacted or "***" in redacted, "Redaction marker should be present"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False

def test_filtered_env_blocks_other_arc_vars():
    """Test that non-SWARMGRAPH ARC_* vars are filtered out."""
    print("TEST: test_filtered_env_blocks_other_arc_vars")
    original_env = os.environ.copy()
    try:
        os.environ["ARC_WORKSPACE_PATH"] = "/workspace"
        os.environ["ARC_CONTEXT7_API_KEY"] = "ctx7-secret"
        os.environ["ARC_SEARCH_API_KEY"] = "search-secret"
        
        adapter = SwarmGraphAdapter()
        filtered = adapter._filtered_env()
        
        assert "ARC_WORKSPACE_PATH" not in filtered, "ARC_WORKSPACE_PATH should be filtered"
        assert "ARC_CONTEXT7_API_KEY" not in filtered, "ARC_CONTEXT7_API_KEY should be filtered"
        assert "ARC_SEARCH_API_KEY" not in filtered, "ARC_SEARCH_API_KEY should be filtered"
        
        print("  ✓ PASSED")
        return True
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        return False
    finally:
        os.environ.clear()
        os.environ.update(original_env)

def main():
    print("=" * 70)
    print("SwarmGraph Security Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        test_filtered_env_blocks_api_keys,
        test_filtered_env_allows_arc_swarmgraph_vars,
        test_filtered_env_allows_system_vars,
        test_filtered_env_includes_pythonwarnings,
        test_output_redaction_api_keys,
        test_filtered_env_blocks_other_arc_vars,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"✗ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
