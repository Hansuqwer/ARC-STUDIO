"""Tests for HMAC-authenticated audit chain."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.audit.key_manager import (
    AuditKeyManager,
    sign_audit_record,
    verify_audit_signature,
    AuditKeyStatus,
)
from agent_runtime_cockpit.audit.hmac_chain import (
    HmacAuditChainWriter,
    verify_hmac_chain,
    GENESIS,
)


def test_sign_and_verify():
    key = b"test-hmac-key-32-bytes-long!!"
    data = {"run_id": "run-001", "action": "consensus", "result": "approved"}
    record_hash, signature = sign_audit_record(data, key)
    assert len(record_hash) == 64
    assert len(signature) == 64
    assert verify_audit_signature(data, signature, key) is True
    assert verify_audit_signature(data, signature, b"wrong-key") is False


def test_tampered_data_fails_verification():
    key = b"test-hmac-key-32-bytes-long!!"
    data = {"run_id": "run-001", "action": "consensus"}
    record_hash, signature = sign_audit_record(data, key)
    tampered = {**data, "action": "rejected"}
    assert verify_audit_signature(tampered, signature, key) is False


def test_chain_continuity():
    key = b"test-hmac-key-32-bytes-long!!"
    prev = GENESIS
    hashes = []
    for i in range(5):
        data = {"seq": i, "value": f"item-{i}"}
        rh, sig = sign_audit_record(data, key, prev)
        hashes.append(rh)
        prev = rh
    for i, data in enumerate([{"seq": j, "value": f"item-{j}"} for j in range(5)]):
        rh, sig = sign_audit_record(data, key, GENESIS if i == 0 else hashes[i - 1])
        assert rh == hashes[i]


def test_key_manager_env_fallback():
    with patch.dict(os.environ, {"ARC_AUDIT_HMAC_KEY": "env-test-key"}):
        with patch.object(AuditKeyManager, "_try_keychain", return_value=None):
            mgr = AuditKeyManager()
            key, status = mgr.get_key()
            assert key == b"env-test-key"
            assert status.source == "env"
            assert status.degraded is True


def test_key_manager_no_key():
    with patch.dict(os.environ, {}, clear=True):
        with patch.object(AuditKeyManager, "_try_keychain", return_value=None):
            mgr = AuditKeyManager()
            key, status = mgr.get_key()
            assert key is None
            assert status.available is False


def test_hmac_chain_writer_and_verify(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "audit.jsonl"
    with patch.object(AuditKeyManager, "_try_keychain", return_value=key):
        mgr = AuditKeyManager()
        writer = HmacAuditChainWriter(chain_path, mgr)
        writer.append({"action": "init", "run_id": "r1"})
        writer.append({"action": "step", "run_id": "r1", "step": 1})
        writer.append({"action": "complete", "run_id": "r1"})
    ok, reason = verify_hmac_chain(chain_path, key)
    assert ok is True
    assert "verified 3 records" in reason


def test_hmac_chain_tamper_detected(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "audit.jsonl"
    with patch.object(AuditKeyManager, "_try_keychain", return_value=key):
        mgr = AuditKeyManager()
        writer = HmacAuditChainWriter(chain_path, mgr)
        writer.append({"action": "init"})
        writer.append({"action": "step"})
    lines = chain_path.read_text().splitlines()
    tampered_record = json.loads(lines[1])
    tampered_record["event"]["action"] = "tampered"
    lines[1] = json.dumps(tampered_record, sort_keys=True, separators=(",", ":"))
    chain_path.write_text("\n".join(lines) + "\n")
    ok, reason = verify_hmac_chain(chain_path, key)
    assert ok is False
    assert "signature invalid" in reason


def test_hmac_chain_empty(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    chain_path = tmp_path / "empty.jsonl"
    chain_path.write_text("")
    ok, reason = verify_hmac_chain(chain_path, key)
    assert ok is True
    assert "empty chain" in reason


def test_hmac_chain_not_found(tmp_path: Path):
    key = b"test-hmac-key-32-bytes-long!!"
    ok, reason = verify_hmac_chain(tmp_path / "nonexistent.jsonl", key)
    assert ok is False
    assert "not found" in reason


def test_key_manager_generate_key():
    mgr = AuditKeyManager()
    key = mgr.generate_key()
    assert len(key) == 64  # 32 bytes hex-encoded
    assert all(c in "0123456789abcdef" for c in key)
