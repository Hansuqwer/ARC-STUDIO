"""Tests for secure credential storage (Phase 36.2)."""

import os
import time

from agent_runtime_cockpit.auth.manager import (
    StoredCredential,
    encrypt_credential,
    decrypt_credential,
    save_credential,
    get_credential,
    get_decrypted_api_key,
    remove_credential,
    list_credentials,
)


def test_encrypt_decrypt_roundtrip():
    """Encrypting then decrypting returns the original API key."""
    cred = encrypt_credential("openai", "sk-test-secret-key-12345")
    decrypted = decrypt_credential(cred)
    assert decrypted == "sk-test-secret-key-12345"


def test_encrypt_produces_different_ciphertext():
    """Each encryption produces unique ciphertext (Fernet nonce)."""
    cred1 = encrypt_credential("openai", "sk-test-key")
    cred2 = encrypt_credential("openai", "sk-test-key")
    assert cred1.credential_data != cred2.credential_data


def _make_cred(provider_id: str, api_key: str) -> StoredCredential:
    cred = encrypt_credential(provider_id, api_key)
    cred.label = "default"
    return cred


def test_save_and_get_credential(tmp_path):
    """Saved credential is retrievable."""
    auth_path = tmp_path / "auth.json"
    cred = _make_cred("anthropic", "sk-ant-test-key")
    save_credential(cred, auth_path)
    retrieved = get_credential("anthropic", auth_path)
    assert retrieved is not None
    assert retrieved.provider_id == "anthropic"


def test_get_decrypted_api_key(tmp_path):
    """get_decrypted_api_key returns the original key."""
    auth_path = tmp_path / "auth.json"
    key = "sk-real-deal-99999"
    cred = _make_cred("openai", key)
    save_credential(cred, auth_path)
    result = get_decrypted_api_key("openai", auth_path)
    assert result == key


def test_remove_credential(tmp_path):
    """Removed credential is no longer retrievable."""
    auth_path = tmp_path / "auth.json"
    cred = _make_cred("openai", "sk-test-key")
    save_credential(cred, auth_path)
    assert remove_credential("openai", auth_path) is True
    assert get_credential("openai", auth_path) is None


def test_list_credentials_no_secrets(tmp_path):
    """list_credentials does not expose raw secrets."""
    auth_path = tmp_path / "auth.json"
    cred = _make_cred("openai", "sk-super-secret")
    save_credential(cred, auth_path)
    entries = list_credentials(auth_path)
    assert len(entries) == 1
    assert entries[0]["provider_id"] == "openai"
    assert entries[0]["has_credential"] is True
    # Verify the raw secret is not in the list output
    raw = auth_path.read_text(encoding="utf-8")
    assert "sk-super-secret" not in raw


def test_credential_not_found(tmp_path):
    """Non-existent provider returns None."""
    auth_path = tmp_path / "auth.json"
    assert get_credential("nonexistent", auth_path) is None


def test_expired_credential_returns_none(tmp_path):
    """Expired credentials are not returned."""
    auth_path = tmp_path / "auth.json"
    cred = _make_cred("openai", "sk-test")
    cred.expires_at = time.time() - 1  # expired
    save_credential(cred, auth_path)
    assert get_credential("openai", auth_path) is None


def test_multiple_providers(tmp_path):
    """Multiple providers can be stored and retrieved independently."""
    auth_path = tmp_path / "auth.json"
    save_credential(_make_cred("openai", "sk-1"), auth_path)
    save_credential(_make_cred("anthropic", "sk-ant-2"), auth_path)
    assert get_decrypted_api_key("openai", auth_path) == "sk-1"
    assert get_decrypted_api_key("anthropic", auth_path) == "sk-ant-2"


def test_file_permissions(tmp_path):
    """Saved auth file has restricted permissions."""
    auth_path = tmp_path / "auth.json"
    cred = _make_cred("openai", "sk-test")
    save_credential(cred, auth_path)
    mode = os.stat(auth_path).st_mode & 0o777
    assert mode == 0o600
