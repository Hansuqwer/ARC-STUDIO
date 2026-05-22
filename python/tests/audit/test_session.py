"""Tests for audit session (ADR-021 integration layer)."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.schema import RuntimeMode, TrustLevel


class FakeKeyManager:
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


def _store(audit_dir, key_available=True):
    from agent_runtime_cockpit.audit.storage import AuditChainStore

    return AuditChainStore(
        audit_dir=audit_dir,
        key_manager=FakeKeyManager(available=key_available),
    )


class TestAuditSession:
    def test_session_run_lifecycle(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started(runtime="swarmgraph", mode=RuntimeMode.gated_local)
        session.log_run_completed(runtime="swarmgraph")
        ok, msg = session.verify()
        assert ok is True

    def test_session_llm_and_tool_events(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started()
        session.log_llm_request(provider="anthropic", model="claude-3-5-sonnet")
        session.log_llm_response(provider="anthropic", model="claude-3-5-sonnet", response_id="msg_123")
        session.log_tool_call(tool_name="read_file", trust_level=TrustLevel.untrusted)
        session.log_tool_result(tool_name="read_file", result={"content": "data"}, trust_level=TrustLevel.untrusted)
        session.log_run_completed()
        ok, msg = session.verify()
        assert ok is True

    def test_session_budget_decision(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started()
        session.log_budget_decision(
            decision="blocked", reason="budget exhausted", budget_state={"remaining": "0.00"}
        )
        session.log_run_failed(reason="budget exhausted")
        ok, msg = session.verify()
        assert ok is True

    def test_session_cancelled(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started()
        session.log_run_cancelled(reason="user cancelled")
        ok, msg = session.verify()
        assert ok is True

    def test_session_verify_after_tamper(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started(runtime="swarmgraph")
        session.log_run_completed(runtime="swarmgraph")
        path = audit_dir / "run_abc.audit.jsonl"
        content = path.read_text()
        tampered = content.replace("swarmgraph", "tampered")
        path.write_text(tampered)
        ok, msg = session.verify()
        assert ok is False

    def test_session_no_key_does_not_crash(self, audit_dir):
        store = _store(audit_dir, key_available=False)
        session = _make_session("run_abc", store)
        session.log_run_started()
        session.log_run_completed()
        ok, msg = session.verify()
        assert ok is False
        assert "No audit key" in msg

    def test_session_multiple_events_timestamps(self, audit_dir):
        store = _store(audit_dir)
        session = _make_session("run_abc", store)
        session.log_run_started()
        session.log_llm_request(provider="openai", model="gpt-4")
        session.log_tool_call(tool_name="list_directory")
        session.log_run_completed()
        path = audit_dir / "run_abc.audit.jsonl"
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 4


def _make_session(run_id, store):
    from agent_runtime_cockpit.audit.session import AuditSession
    s = AuditSession(run_id=run_id, store=store)
    s.store.ensure_run(run_id)
    return s


@pytest.mark.asyncio
class TestAuditSessionAsync:
    async def test_async_session_lifecycle(self, audit_dir):
        store = _store(audit_dir)
        from agent_runtime_cockpit.audit.session import audit_session

        async with audit_session("run_abc", store=store) as session:
            session.log_run_started(runtime="swarmgraph")
            session.log_llm_request(provider="anthropic", model="claude")
            session.log_run_completed()
        ok, msg = session.verify()
        assert ok is True

    async def test_async_session_failure_records_failed(self, audit_dir):
        store = _store(audit_dir)
        from agent_runtime_cockpit.audit.session import audit_session

        with pytest.raises(RuntimeError):
            async with audit_session("run_fail", store=store) as session:
                session.log_run_started()
                raise RuntimeError("something broke")
        ok, msg = session.verify()
        assert ok is True  # chain is valid even for failed runs
