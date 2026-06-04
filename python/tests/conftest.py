"""Shared pytest cleanup hooks."""

from __future__ import annotations

import gc
import socket
from dataclasses import dataclass, field
from typing import Any

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken


@dataclass
class _CapturedEvent:
    name: str
    payload: dict[str, Any]


@dataclass
class _StubSession:
    allow_run: bool = False


@dataclass
class _StubReplContext:
    events: list[_CapturedEvent] = field(default_factory=list)
    session: _StubSession = field(default_factory=_StubSession)
    runtime: Any = None
    _session_token: CancellationToken = field(default_factory=CancellationToken)

    def emit_event(self, name: str, payload: dict[str, Any]) -> None:
        self.events.append(_CapturedEvent(name=name, payload=dict(payload)))

    def run_token_factory(self) -> CancellationToken:
        return self._session_token.child()


@pytest.fixture
def make_repl_context():
    def _factory(**overrides):
        ctx = _StubReplContext()
        for k, v in overrides.items():
            setattr(ctx, k, v)
        return ctx

    return _factory


@pytest.fixture(autouse=True)
def _allow_unauthenticated_daemon_in_tests(monkeypatch: pytest.MonkeyPatch):
    """Most daemon route tests target route behavior, not auth bootstrap."""
    monkeypatch.setenv("ARC_DAEMON_ALLOW_UNAUTHENTICATED", "1")
    monkeypatch.setenv("ARC_AUDIT_HMAC_KEY", "test-audit-hmac-key-32-bytes-long")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Close unreachable Docker SDK Unix sockets before pytest's final GC pass."""
    for obj in gc.get_objects():
        if isinstance(obj, socket.socket) and obj.family == socket.AF_UNIX and obj.fileno() != -1:
            obj.close()
