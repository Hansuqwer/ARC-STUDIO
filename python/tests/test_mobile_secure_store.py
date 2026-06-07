"""Tests for T4 (Phase 8): SecureLocalStore — real encryption-at-rest + classification."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.mobile import (
    InMemoryKeyProvider,
    MobileDataSensitivity,
    SecureLocalStore,
    SecureStoreError,
)


def test_round_trip_various_types() -> None:
    s = SecureLocalStore()
    s.put("str", "hello")
    s.put("obj", {"a": 1, "b": [1, 2, 3]}, MobileDataSensitivity.MEDIUM)
    assert s.get("str") == "hello"
    assert s.get("obj") == {"a": 1, "b": [1, 2, 3]}
    assert set(s.keys()) == {"str", "obj"}


def test_no_plaintext_at_rest(tmp_path) -> None:
    path = tmp_path / "store.json"
    s = SecureLocalStore(path=path)
    secret = "SUPER-SECRET-VALUE-7f3a"
    s.put("token", secret, MobileDataSensitivity.CRITICAL)
    raw = path.read_text(encoding="utf-8")
    assert secret not in raw, "plaintext leaked into the at-rest file"
    assert "ciphertext" in raw
    # reload from disk with the same key → decrypts correctly
    reloaded = SecureLocalStore(key_provider=InMemoryKeyProvider(s._keys.get_key()), path=path)
    assert reloaded.get("token") == secret


def test_classification_tracked() -> None:
    s = SecureLocalStore()
    s.put("loc", {"lat": 1}, "high")
    assert s.classification_of("loc") == MobileDataSensitivity.HIGH


def test_export_metadata_only_by_default() -> None:
    s = SecureLocalStore()
    s.put("a", "low-value", MobileDataSensitivity.LOW)
    s.put("b", "secret", MobileDataSensitivity.CRITICAL)
    bundle = s.export()
    assert bundle["encrypted_at_rest"] is True
    for item in bundle["entries"]:
        assert "value" not in item  # metadata only
        assert {"key", "classification", "created_at", "updated_at"} <= set(item)


def test_export_with_values_redacts_restricted() -> None:
    s = SecureLocalStore()
    s.put("low", "ok-to-export", MobileDataSensitivity.LOW)
    s.put("high", "do-not-export", MobileDataSensitivity.CRITICAL)
    by_key = {i["key"]: i for i in s.export(include_values=True)["entries"]}
    assert by_key["low"]["value"] == "ok-to-export"
    assert by_key["high"].get("value_redacted") is True
    assert "do-not-export" not in str(by_key["high"])


def test_delete_and_wipe() -> None:
    s = SecureLocalStore()
    s.put("a", 1)
    s.put("b", 2)
    assert s.delete("a") is True
    assert s.delete("missing") is False
    assert s.keys() == ["b"]
    assert s.wipe() == 1
    assert s.keys() == []


def test_tamper_fails_closed() -> None:
    s = SecureLocalStore()
    s.put("k", "v")
    # corrupt the stored ciphertext
    s._entries["k"].ciphertext = s._entries["k"].ciphertext[:-4] + b"AAAA"
    with pytest.raises(SecureStoreError):
        s.get("k")


def test_wrong_key_cannot_decrypt(tmp_path) -> None:
    path = tmp_path / "s.json"
    s = SecureLocalStore(path=path)
    s.put("k", "v", MobileDataSensitivity.HIGH)
    other = SecureLocalStore(key_provider=InMemoryKeyProvider(), path=path)  # different key
    with pytest.raises(SecureStoreError):
        other.get("k")
