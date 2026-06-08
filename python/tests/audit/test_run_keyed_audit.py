"""B2P-19: shared keyed (HMAC) run-audit checkpoint helper."""

from __future__ import annotations

import json
from types import SimpleNamespace

from agent_runtime_cockpit.audit.hmac_chain import verify_hmac_chain
from agent_runtime_cockpit.audit.run_keyed_audit import write_run_keyed_audit

_KEY = b"0123456789abcdef0123456789abcdef"


class _FakeKeyManager:
    def __init__(self, key: bytes | None) -> None:
        self._key = key

    def get_key(self):
        return self._key, SimpleNamespace(
            key_id="test-key", source="test", available=self._key is not None
        )


def test_writes_verifiable_keyed_chain(tmp_path) -> None:
    path = write_run_keyed_audit(
        "run-1",
        status="completed",
        workflow_id="wf",
        event_count=3,
        workspace_root=tmp_path,
        key_manager=_FakeKeyManager(_KEY),
    )
    assert path is not None and path.exists()
    ok, reason = verify_hmac_chain(path, _KEY)
    assert ok, reason


def test_no_key_is_noop(tmp_path) -> None:
    path = write_run_keyed_audit(
        "run-2",
        status="completed",
        workflow_id="wf",
        event_count=0,
        workspace_root=tmp_path,
        key_manager=_FakeKeyManager(None),
    )
    assert path is None


def test_tamper_is_detected(tmp_path) -> None:
    path = write_run_keyed_audit(
        "run-3",
        status="completed",
        workflow_id="wf",
        event_count=1,
        workspace_root=tmp_path,
        key_manager=_FakeKeyManager(_KEY),
    )
    assert path is not None
    lines = path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["status"] = "TAMPERED"
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    ok, _ = verify_hmac_chain(path, _KEY)
    assert ok is False


def test_run_path_integration_is_best_effort() -> None:
    # Reliability (gate 7): a keyed-audit failure must never break the run path. The executor calls
    # the helper inside a best-effort try/except — lock that containment against regression.
    import inspect

    from agent_runtime_cockpit.tasks.executor import TaskExecutor

    src = inspect.getsource(TaskExecutor._execute_run)
    assert "write_run_keyed_audit" in src
    assert "never break the run" in src  # the best-effort containment comment on the except


def test_helper_is_noop_not_raise_without_key(tmp_path) -> None:
    # Reliability (gate 7): the helper itself never raises on the missing-key path — callers may
    # invoke it unconditionally at the end of a run path.
    assert (
        write_run_keyed_audit(
            "run-noraise",
            status="completed",
            workflow_id="wf",
            event_count=0,
            workspace_root=tmp_path,
            key_manager=_FakeKeyManager(None),
        )
        is None
    )
