"""Integration tests for the /run slash command."""

from __future__ import annotations

import os
import signal
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken
from agent_runtime_cockpit.cli_repl.slash_commands import _build_registry


@dataclass
class _StubRunResult:
    text: str

    def render(self) -> str:
        return self.text

    def summary(self) -> dict[str, Any]:
        return {"chars": len(self.text)}


class _StubRunner:
    def __init__(
        self,
        runtime: Any,
        *,
        cancellation_token: Optional[CancellationToken] = None,
        mode: str = "instant",
    ) -> None:
        self.runtime = runtime
        self.token = cancellation_token
        self.mode = mode

    def run(
        self, prompt: str, on_progress: Optional[Callable[[dict[str, Any]], None]] = None
    ) -> _StubRunResult:
        if self.mode == "instant":
            return _StubRunResult(text=f"ok: {prompt}")
        if self.mode == "progress":
            for stage in ("plan", "execute", "aggregate"):
                if on_progress is not None:
                    on_progress({"stage": stage})
            return _StubRunResult(text=f"ok: {prompt}")
        if self.mode == "cancellable":
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if self.token is not None:
                    self.token.raise_if_cancelled()
                if on_progress is not None:
                    on_progress({"stage": "execute"})
                time.sleep(0.01)
            raise AssertionError("Cancellable runner ran to completion")
        raise AssertionError(f"Unknown stub runner mode: {self.mode}")


@pytest.fixture
def registry():
    return _build_registry()


@pytest.fixture
def run_entry(registry):
    entry = registry.get("/run")
    if entry is None:
        pytest.skip("/run not registered in this Phase 2 subset (per ADR-016)")
    return entry


@pytest.fixture
def ctx(make_repl_context):
    return make_repl_context()


def test_run_blocked_when_gate_closed(run_entry, ctx, monkeypatch):
    monkeypatch.delenv("ARC_ALLOW_RUN", raising=False)
    ctx.session.allow_run = False
    result = run_entry.handler(["hello"], ctx)
    assert result.state == "blocked"
    assert result.reason == "gate_closed"
    assert "ARC_ALLOW_RUN" in result.remediation
    assert not any(e.name.startswith("run.") for e in ctx.events)


def test_run_unblocked_by_env_var(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")
    ctx.session.allow_run = False
    with patch(
        "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
        lambda runtime, **kw: _StubRunner(runtime, mode="instant", **kw),
    ):
        result = run_entry.handler(["hello"], ctx)
    assert result.state == "present"
    assert "ok: hello" in result.output


def test_run_unblocked_by_session_flag(run_entry, ctx, monkeypatch):
    monkeypatch.delenv("ARC_ALLOW_RUN", raising=False)
    ctx.session.allow_run = True
    with patch(
        "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
        lambda runtime, **kw: _StubRunner(runtime, mode="instant", **kw),
    ):
        result = run_entry.handler(["hi"], ctx)
    assert result.state == "present"


def test_successful_run_emits_started_then_completed(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")
    with patch(
        "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
        lambda runtime, **kw: _StubRunner(runtime, mode="instant", **kw),
    ):
        result = run_entry.handler(["hello", "world"], ctx)
    assert result.state == "present"
    run_events = [e.name for e in ctx.events if e.name.startswith("run.")]
    assert run_events[0] == "run.started"
    assert run_events[-1] == "run.completed"
    assert "run.cancelled" not in run_events


def test_progress_events_are_emitted_with_stage(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")
    with patch(
        "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
        lambda runtime, **kw: _StubRunner(runtime, mode="progress", **kw),
    ):
        result = run_entry.handler(["go"], ctx)
    assert result.state == "present"
    progress_stages = [
        e.payload.get("stage") for e in ctx.events if e.name.startswith("run.progress.")
    ]
    assert progress_stages == ["plan", "execute", "aggregate"]


@pytest.mark.skipif(
    os.name == "nt", reason="SIGINT delivery from a thread is unreliable on Windows"
)
@pytest.mark.xfail(
    strict=False,
    reason="SIGINT timing: signal delivery from a background thread to the main thread "
    "is not guaranteed to preempt the cancellation-token check loop within the "
    "50ms window on heavily loaded CI runners.",
)
def test_sigint_during_run_yields_degraded_and_cancelled_event(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")

    def _send_sigint_soon():
        time.sleep(0.05)
        os.kill(os.getpid(), signal.SIGINT)

    sender = threading.Thread(target=_send_sigint_soon)
    sender.start()
    try:
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
            lambda runtime, **kw: _StubRunner(runtime, mode="cancellable", **kw),
        ):
            result = run_entry.handler(["loop"], ctx)
    finally:
        sender.join(timeout=2.0)
    assert result.state == "degraded"
    run_events = [e for e in ctx.events if e.name.startswith("run.")]
    names = [e.name for e in run_events]
    assert "run.started" in names
    assert "run.cancelled" in names
    assert "run.completed" not in names
    cancelled = next(e for e in run_events if e.name == "run.cancelled")
    assert cancelled.payload["reason"] == "user"
    assert cancelled.payload.get("elapsed_ms") is not None


def test_programmatic_cancellation_yields_degraded(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")
    captured_tokens: list[CancellationToken] = []

    class _CapturingRunner(_StubRunner):
        def __init__(self, runtime, **kw):
            super().__init__(runtime, mode="cancellable", **kw)
            if self.token is not None:
                captured_tokens.append(self.token)

    def _cancel_after_short_delay():
        time.sleep(0.05)
        if captured_tokens:
            captured_tokens[0].cancel(CancellationReason.BUDGET, "$5 cap hit")

    canceller = threading.Thread(target=_cancel_after_short_delay)
    canceller.start()
    try:
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", _CapturingRunner
        ):
            result = run_entry.handler(["loop"], ctx)
    finally:
        canceller.join(timeout=2.0)
    assert result.state == "degraded"
    cancelled = next(e for e in ctx.events if e.name == "run.cancelled")
    assert cancelled.payload["reason"] == "budget"
    assert "$5 cap hit" in cancelled.payload["detail"]


def test_sigint_handler_restored_after_successful_run(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")

    def _sentinel(signum, frame):
        pass

    previous = signal.signal(signal.SIGINT, _sentinel)
    try:
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
            lambda runtime, **kw: _StubRunner(runtime, mode="instant", **kw),
        ):
            run_entry.handler(["x"], ctx)
        assert signal.getsignal(signal.SIGINT) is _sentinel
    finally:
        signal.signal(signal.SIGINT, previous)


@pytest.mark.skipif(os.name == "nt", reason="SIGINT delivery unreliable on Windows")
def test_sigint_handler_restored_after_cancelled_run(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")

    def _sentinel(signum, frame):
        pass

    previous = signal.signal(signal.SIGINT, _sentinel)
    try:

        def _send_sigint_soon():
            time.sleep(0.05)
            os.kill(os.getpid(), signal.SIGINT)

        sender = threading.Thread(target=_send_sigint_soon)
        sender.start()
        try:
            with patch(
                "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner",
                lambda runtime, **kw: _StubRunner(runtime, mode="cancellable", **kw),
            ):
                run_entry.handler(["loop"], ctx)
        finally:
            sender.join(timeout=2.0)
        assert signal.getsignal(signal.SIGINT) is _sentinel
    finally:
        signal.signal(signal.SIGINT, previous)


def test_sigint_handler_restored_after_exception(run_entry, ctx, monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_RUN", "1")

    def _sentinel(signum, frame):
        pass

    class _ExplodingRunner:
        def __init__(self, runtime, **kw):
            pass

        def run(self, prompt, on_progress=None):
            raise RuntimeError("boom")

    previous = signal.signal(signal.SIGINT, _sentinel)
    try:
        with patch(
            "agent_runtime_cockpit.cli_repl.slash_commands.SwarmGraphRunner", _ExplodingRunner
        ):
            with pytest.raises(RuntimeError, match="boom"):
                run_entry.handler(["x"], ctx)
        assert signal.getsignal(signal.SIGINT) is _sentinel
    finally:
        signal.signal(signal.SIGINT, previous)
