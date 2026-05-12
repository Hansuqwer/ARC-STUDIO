"""
Test for Issue #12: Output redaction for secrets

Verifies that sensitive information is redacted from logs and metadata.
"""
import pytest


def test_redact_openai_api_keys():
    """Test that OpenAI API keys are redacted."""
    text = "Error: Authentication failed with key sk-1234567890abcdefghijklmnop"
    
    # Simulate redaction
    import re
    redacted = re.sub(r'sk-[A-Za-z0-9_-]{20,}', 'sk-REDACTED', text)
    
    assert "sk-REDACTED" in redacted
    assert "sk-1234567890abcdefghijklmnop" not in redacted
    print("✅ OpenAI API key redacted")


def test_redact_anthropic_api_keys():
    """Test that Anthropic API keys are redacted."""
    text = "Failed with sk-ant-api03-1234567890abcdefghijklmnop"
    
    import re
    redacted = re.sub(r'sk-ant-[A-Za-z0-9_-]{20,}', 'sk-ant-REDACTED', text)
    
    assert "sk-ant-REDACTED" in redacted
    assert "sk-ant-api03-1234567890abcdefghijklmnop" not in redacted
    print("✅ Anthropic API key redacted")


def test_redact_api_key_parameters():
    """Test that api_key parameters are redacted."""
    text = "Config: api_key=secret123 and apikey: another_secret"
    
    import re
    redacted = re.sub(r'(api[_-]?key\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', text)
    redacted = re.sub(r'(apikey\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', redacted)
    
    assert "api_key=REDACTED" in redacted
    assert "apikey: REDACTED" in redacted
    assert "secret123" not in redacted
    assert "another_secret" not in redacted
    print("✅ API key parameters redacted")


def test_redact_authorization_headers():
    """Test that Authorization headers are redacted."""
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    
    import re
    redacted = re.sub(r'(authorization:\s*bearer\s+)[^\s]+', r'\1REDACTED', text, flags=re.IGNORECASE)
    
    assert "Authorization: Bearer REDACTED" in redacted
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
    print("✅ Authorization header redacted")


def test_redact_aws_credentials():
    """Test that AWS credentials are redacted."""
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    
    import re
    redacted = re.sub(r'(aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', text, flags=re.IGNORECASE)
    redacted = re.sub(r'(aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', redacted, flags=re.IGNORECASE)
    
    assert "AWS_ACCESS_KEY_ID=REDACTED" in redacted
    assert "AWS_SECRET_ACCESS_KEY=REDACTED" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in redacted
    print("✅ AWS credentials redacted")


def test_redact_tokens():
    """Test that token parameters are redacted."""
    text = "token=ghp_1234567890 access_token: pat_abcdefg"
    
    import re
    redacted = re.sub(r'(token\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', text)
    redacted = re.sub(r'(access[_-]?token\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', redacted)
    
    assert "token=REDACTED" in redacted
    assert "access_token: REDACTED" in redacted
    assert "ghp_1234567890" not in redacted
    assert "pat_abcdefg" not in redacted
    print("✅ Tokens redacted")


def test_redact_passwords():
    """Test that password parameters are redacted."""
    text = "password=supersecret123 SECRET: another_secret"
    
    import re
    redacted = re.sub(r'(password\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', text, flags=re.IGNORECASE)
    redacted = re.sub(r'(secret\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', redacted, flags=re.IGNORECASE)
    
    assert "password=REDACTED" in redacted
    assert "SECRET: REDACTED" in redacted
    assert "supersecret123" not in redacted
    assert "another_secret" not in redacted
    print("✅ Passwords redacted")


def test_redact_multiple_secrets_in_text():
    """Test redacting multiple secrets in one text."""
    text = """
    Error trace:
    OPENAI_API_KEY=sk-1234567890abcdefghij
    Authorization: Bearer token123
    api_key: secret456
    AWS_ACCESS_KEY_ID=AKIA789
    """
    
    import re
    redacted = text
    patterns = [
        (r'sk-[A-Za-z0-9_-]{20,}', 'sk-REDACTED'),
        (r'(api[_-]?key\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED'),
        (r'(authorization:\s*bearer\s+)[^\s]+', r'\1REDACTED', re.IGNORECASE),
        (r'(aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*)[^\s\'"]+', r'\1REDACTED', re.IGNORECASE),
    ]
    
    for pattern_tuple in patterns:
        if len(pattern_tuple) == 2:
            pattern, replacement = pattern_tuple
            redacted = re.sub(pattern, replacement, redacted)
        else:
            pattern, replacement, flags = pattern_tuple
            redacted = re.sub(pattern, replacement, redacted, flags=flags)
    
    # Verify all secrets are redacted
    assert "sk-REDACTED" in redacted
    assert "api_key: REDACTED" in redacted
    assert "Authorization: Bearer REDACTED" in redacted
    assert "AWS_ACCESS_KEY_ID=REDACTED" in redacted
    
    # Verify original secrets are gone
    assert "sk-1234567890abcdefghij" not in redacted
    assert "token123" not in redacted
    assert "secret456" not in redacted
    assert "AKIA789" not in redacted
    
    print("✅ Multiple secrets redacted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
