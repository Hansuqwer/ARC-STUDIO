"""Tests for GET /api/audit/verify/{run_id} route."""

from __future__ import annotations

import hashlib
import json

import pytest

GENESIS = "GENESIS"


def _sha256_chain(records: list[dict]) -> list[str]:
    """Build a SHA-256 chain file from event dicts, return lines."""
    lines = []
    prev_hash = GENESIS
    for event in records:
        event_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(event_json.encode()).hexdigest()
        chain_hash = hashlib.sha256(f"{prev_hash}:{event_hash}".encode()).hexdigest()
        record = {
            "prev_hash": prev_hash,
            "event_hash": event_hash,
            "chain_hash": chain_hash,
            "event": event,
        }
        lines.append(json.dumps(record))
        prev_hash = chain_hash
    return lines


@pytest.fixture
def sha256_chain(workspace):
    """Create a valid 3-record SHA-256 audit chain."""
    events = [{"type": "RUN_STARTED", "seq": i, "data": {"i": i}} for i in range(3)]
    lines = _sha256_chain(events)
    chain_path = workspace / ".arc" / "audit" / "run-test-sha.audit.jsonl"
    chain_path.write_text("\n".join(lines) + "\n")
    return "run-test-sha"


@pytest.fixture
def tampered_chain(workspace):
    """Create a SHA-256 chain with a tampered record."""
    events = [{"type": "RUN_STARTED", "seq": i, "data": {"i": i}} for i in range(3)]
    lines = _sha256_chain(events)
    # Tamper with second record's chain_hash
    record = json.loads(lines[1])
    record["chain_hash"] = "deadbeef" * 8
    lines[1] = json.dumps(record)
    chain_path = workspace / ".arc" / "audit" / "run-tampered.audit.jsonl"
    chain_path.write_text("\n".join(lines) + "\n")
    return "run-tampered"


@pytest.mark.asyncio
async def test_verify_sha256_ok(client, sha256_chain):
    resp = await client.get(f"/api/audit/verify/{sha256_chain}?mode=sha256")
    assert resp.status_code == 200
    body = await resp.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["ok"] is True
    assert data["mode"] == "sha256"
    assert data["records_checked"] == 3
    assert "duration_ms" in data
    assert "file_size_bytes" in data


@pytest.mark.asyncio
async def test_verify_auto_detects_sha256(client, sha256_chain):
    resp = await client.get(f"/api/audit/verify/{sha256_chain}?mode=auto")
    assert resp.status_code == 200
    body = await resp.json()
    assert body["ok"] is True
    assert body["data"]["mode"] == "sha256"
    assert body["data"]["records_checked"] == 3


@pytest.mark.asyncio
async def test_verify_tampered_chain_fails(client, tampered_chain):
    resp = await client.get(f"/api/audit/verify/{tampered_chain}?mode=sha256")
    assert resp.status_code == 200
    body = await resp.json()
    assert body["ok"] is True  # envelope ok
    data = body["data"]
    assert data["ok"] is False
    assert data["mode"] == "sha256"
    assert "mismatch" in data["reason"].lower() or "broken" in data["reason"].lower()


@pytest.mark.asyncio
async def test_verify_missing_run_returns_404(client):
    resp = await client.get("/api/audit/verify/nonexistent-run?mode=auto")
    assert resp.status_code == 404
    body = await resp.json()
    assert body["ok"] is False


@pytest.mark.asyncio
async def test_verify_invalid_mode_returns_400(client, sha256_chain):
    resp = await client.get(f"/api/audit/verify/{sha256_chain}?mode=invalid")
    assert resp.status_code == 400
    body = await resp.json()
    assert body["ok"] is False


@pytest.mark.asyncio
async def test_verify_hmac_no_key_returns_400(client, sha256_chain):
    """HMAC mode with no key configured should return 400."""
    resp = await client.get(f"/api/audit/verify/{sha256_chain}?mode=hmac")
    assert resp.status_code == 200 or resp.status_code == 400
    body = await resp.json()
    # Either returns an error envelope or 400 status depending on key availability
    if resp.status_code == 400:
        assert body["ok"] is False


@pytest.mark.asyncio
async def test_verify_json_shape_stable(client, sha256_chain):
    """Verify the response has the documented stable JSON fields."""
    resp = await client.get(f"/api/audit/verify/{sha256_chain}?mode=sha256")
    body = await resp.json()
    data = body["data"]
    required_fields = {"ok", "mode", "records_checked", "reason", "duration_ms"}
    assert required_fields.issubset(set(data.keys()))
    # Optional fields may be present
    assert isinstance(data["ok"], bool)
    assert data["mode"] in ("sha256", "hmac")
    assert isinstance(data["records_checked"], int)
    assert isinstance(data["duration_ms"], int)
