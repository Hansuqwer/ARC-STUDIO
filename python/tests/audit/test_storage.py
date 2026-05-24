"""Tests for audit chain storage layer (ADR-021)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.schema import LlmRequestEvent, RunCompletedEvent, RunStartedEvent


def _make_store(audit_dir, key_available=True):
    from agent_runtime_cockpit.audit.storage import AuditChainStore

    return AuditChainStore(
        audit_dir=audit_dir,
        key_manager=FakeKeyManager(available=key_available),
    )


class FakeKeyManager:
    """Returns a static test key."""

    def __init__(self, available: bool = True):
        self._available = available

    def get_key(self):
        if self._available:
            return b"test-key-32-bytes-long-0123456789abcdef", type(
                "Status",
                (),
                {
                    "available": True,
                    "source": "test",
                    "degraded": True,
                    "warning": "",
                    "key_id": "",
                },
            )()
        return None, type(
            "Status",
            (),
            {
                "available": False,
                "source": "none",
                "degraded": True,
                "warning": "No key",
                "key_id": "",
            },
        )()


@pytest.fixture
def audit_dir(tmp_path: Path) -> Path:
    d = tmp_path / "audit"
    d.mkdir()
    return d


class TestAuditChainStore:
    def _store(self, audit_dir, key_available=True):
        from agent_runtime_cockpit.audit.storage import AuditChainStore

        return AuditChainStore(
            audit_dir=audit_dir,
            key_manager=FakeKeyManager(available=key_available),
        )

    def test_ensure_run_creates_file(self, audit_dir):
        store = self._store(audit_dir)
        store.ensure_run("run_abc")
        path = audit_dir / "run_abc.audit.jsonl"
        assert path.exists()

    def test_ensure_run_idempotent(self, audit_dir):
        store = self._store(audit_dir)
        store.ensure_run("run_abc")
        store.ensure_run("run_abc")
        path = audit_dir / "run_abc.audit.jsonl"
        assert path.exists()

    def test_append_event_with_key(self, audit_dir):
        store = self._store(audit_dir)
        event = RunStartedEvent(run_id="run_abc", runtime="swarmgraph")
        result = store.append_event(event)
        assert result is not None
        assert result["seq"] == 0
        assert result["event"]["type"] == "run_started"

    def test_append_event_without_key(self, audit_dir):
        store = self._store(audit_dir, key_available=False)
        event = RunStartedEvent(run_id="run_abc", runtime="swarmgraph")
        result = store.append_event(event)
        assert result is None

    def test_append_multiple_events(self, audit_dir):
        store = self._store(audit_dir)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        store.append_event(LlmRequestEvent(run_id="run_abc", provider="anthropic", model="claude"))
        store.append_event(RunCompletedEvent(run_id="run_abc", runtime="swarmgraph"))
        path = audit_dir / "run_abc.audit.jsonl"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_verify_run_good(self, audit_dir):
        store = self._store(audit_dir)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        store.append_event(RunCompletedEvent(run_id="run_abc", runtime="swarmgraph"))
        ok, msg = store.verify_run("run_abc")
        assert ok is True
        assert "verified" in msg

    def test_verify_run_missing(self, audit_dir):
        store = self._store(audit_dir)
        ok, msg = store.verify_run("run_nonexistent")
        assert ok is False
        assert "not found" in msg

    def test_verify_run_no_key(self, audit_dir):
        store = self._store(audit_dir, key_available=False)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        ok, msg = store.verify_run("run_abc")
        assert ok is False
        assert "No audit key" in msg

    def test_export_run(self, audit_dir):
        store = self._store(audit_dir)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        store.append_event(RunCompletedEvent(run_id="run_abc", runtime="swarmgraph"))
        out_path = audit_dir / "bundle.json"
        result = store.export_run("run_abc", output_path=out_path)
        assert result is not None
        bundle = json.loads(out_path.read_text())
        assert bundle["run_id"] == "run_abc"
        assert bundle["verification"]["verified"] is True
        assert bundle["verification"]["event_count"] == 2

    def test_export_run_missing(self, audit_dir):
        store = self._store(audit_dir)
        result = store.export_run("run_nonexistent")
        assert result is None

    def test_delete_run(self, audit_dir):
        store = self._store(audit_dir)
        store.ensure_run("run_abc")
        assert store.delete_run("run_abc") is True
        assert not (audit_dir / "run_abc.audit.jsonl").exists()

    def test_delete_nonexistent_run(self, audit_dir):
        store = self._store(audit_dir)
        assert store.delete_run("run_nonexistent") is False

    def test_list_runs(self, audit_dir):
        store = self._store(audit_dir)
        store.ensure_run("run_abc")
        store.ensure_run("run_def")
        runs = store.list_runs()
        assert "run_abc" in runs
        assert "run_def" in runs

    def test_list_runs_empty(self, audit_dir):
        store = self._store(audit_dir)
        assert store.list_runs() == []


class TestChainTamperDetection:
    def test_tampered_event_detected(self, audit_dir):
        store = _make_store(audit_dir)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        store.append_event(RunCompletedEvent(run_id="run_abc", runtime="swarmgraph"))
        path = audit_dir / "run_abc.audit.jsonl"
        content = path.read_text()
        tampered = content.replace("swarmgraph", "tampered-runtime")
        path.write_text(tampered)
        ok, msg = store.verify_run("run_abc")
        assert ok is False
        assert "signature" in msg.lower() or "invalid" in msg.lower()

    def test_truncated_chain_is_short_valid_chain(self, audit_dir):
        """Truncation is a known limitation of simple HMAC chains.

        A shorter chain with valid signatures is still valid. Detecting
        truncation requires periodic integrity checkpoints (future work).
        This test documents the current behavior.
        """
        store = _make_store(audit_dir)
        store.append_event(RunStartedEvent(run_id="run_abc", runtime="swarmgraph"))
        store.append_event(RunCompletedEvent(run_id="run_abc", runtime="swarmgraph"))
        path = audit_dir / "run_abc.audit.jsonl"
        lines = path.read_text().splitlines()
        path.write_text("\n".join(lines[:1]))
        ok, msg = store.verify_run("run_abc")
        assert ok is True  # shorter chain with valid HMACs is still valid
        assert "1 records" in msg
