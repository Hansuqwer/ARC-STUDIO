"""Unit tests for the cooperative cancellation primitive."""

from __future__ import annotations

import threading
import time

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import (
    CancellationReason,
    CancellationToken,
    Cancelled,
    never_cancelled,
)


def test_fresh_token_is_not_cancelled() -> None:
    token = CancellationToken()
    assert token.is_cancelled is False
    assert token.reason is None
    assert token.detail == ""
    assert token.cancelled_at is None


def test_raise_if_cancelled_is_noop_when_not_cancelled() -> None:
    token = CancellationToken()
    token.raise_if_cancelled()
    assert token.is_cancelled is False


def test_cancel_sets_state_and_reason() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "Ctrl+C")
    assert token.is_cancelled is True
    assert token.reason is CancellationReason.USER
    assert token.detail == "Ctrl+C"
    assert token.cancelled_at is not None


def test_cancel_records_monotonic_timestamp() -> None:
    token = CancellationToken()
    before = time.monotonic()
    token.cancel(CancellationReason.TIMEOUT, "deadline")
    after = time.monotonic()
    assert token.cancelled_at is not None
    assert before <= token.cancelled_at <= after


def test_cancel_is_idempotent_preserves_first_reason() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.BUDGET, "cost cap hit")
    first_ts = token.cancelled_at
    time.sleep(0.005)
    token.cancel(CancellationReason.USER, "Ctrl+C")
    assert token.reason is CancellationReason.BUDGET
    assert token.detail == "cost cap hit"
    assert token.cancelled_at == first_ts


def test_raise_if_cancelled_raises_with_reason() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.GATE_REVOKED, "ARC_ALLOW_RUN unset mid-run")
    with pytest.raises(Cancelled) as excinfo:
        token.raise_if_cancelled()
    assert excinfo.value.reason is CancellationReason.GATE_REVOKED
    assert excinfo.value.detail == "ARC_ALLOW_RUN unset mid-run"


def test_cancelled_exception_str_contains_reason_and_detail() -> None:
    rendered = str(Cancelled(CancellationReason.TIMEOUT, "deadline 30s exceeded"))
    assert "timeout" in rendered
    assert "deadline 30s exceeded" in rendered


def test_cancelled_exception_str_without_detail() -> None:
    rendered = str(Cancelled(CancellationReason.USER))
    assert "user" in rendered
    assert not rendered.endswith(": ")
    assert not rendered.endswith(":")


def test_raise_if_cancelled_is_repeatable() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "")
    with pytest.raises(Cancelled):
        token.raise_if_cancelled()
    with pytest.raises(Cancelled):
        token.raise_if_cancelled()


def test_wait_returns_false_on_timeout_when_not_cancelled() -> None:
    token = CancellationToken()
    start = time.monotonic()
    result = token.wait(timeout=0.05)
    elapsed = time.monotonic() - start
    assert result is False
    assert elapsed >= 0.045


def test_wait_returns_true_immediately_if_already_cancelled() -> None:
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "")
    start = time.monotonic()
    result = token.wait(timeout=5.0)
    elapsed = time.monotonic() - start
    assert result is True
    assert elapsed < 0.1


def test_wait_returns_true_when_cancelled_mid_wait() -> None:
    token = CancellationToken()

    def _cancel_after_short_delay() -> None:
        time.sleep(0.02)
        token.cancel(CancellationReason.USER, "external")

    canceller = threading.Thread(target=_cancel_after_short_delay)
    canceller.start()
    try:
        start = time.monotonic()
        result = token.wait(timeout=2.0)
        elapsed = time.monotonic() - start
        assert result is True
        assert elapsed < 1.0
    finally:
        canceller.join(timeout=1.0)


def test_child_starts_uncancelled_when_parent_uncancelled() -> None:
    parent = CancellationToken()
    child = parent.child()
    assert child.is_cancelled is False
    assert parent.is_cancelled is False


def test_child_is_cancelled_immediately_if_parent_already_cancelled() -> None:
    parent = CancellationToken()
    parent.cancel(CancellationReason.USER, "Ctrl+C before fan-out")
    child = parent.child()
    assert child.is_cancelled is True
    assert child.reason is CancellationReason.PARENT
    assert "Ctrl+C" in child.detail


def test_child_cancels_when_parent_cancels_later() -> None:
    parent = CancellationToken()
    child = parent.child()
    grandchild = child.child()
    parent.cancel(CancellationReason.BUDGET, "cap hit")
    assert child.is_cancelled is True
    assert child.reason is CancellationReason.PARENT
    assert grandchild.is_cancelled is True
    assert grandchild.reason is CancellationReason.PARENT


def test_cancelling_child_does_not_cancel_parent() -> None:
    parent = CancellationToken()
    child_a = parent.child()
    child_b = parent.child()
    child_a.cancel(CancellationReason.TIMEOUT, "worker A slow")
    assert child_a.is_cancelled is True
    assert parent.is_cancelled is False
    assert child_b.is_cancelled is False


def test_grandchild_reason_traces_to_parent_cause() -> None:
    parent = CancellationToken()
    child = parent.child()
    grandchild = child.child()
    parent.cancel(CancellationReason.BUDGET, "$5 cap")
    assert grandchild.reason is CancellationReason.PARENT
    assert "budget" in grandchild.detail.lower() or "$5" in grandchild.detail


def test_cancellation_is_observable_across_threads() -> None:
    token = CancellationToken()
    observed: list[bool] = []
    done = threading.Event()

    def _worker() -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if token.is_cancelled:
                observed.append(True)
                done.set()
                return
            time.sleep(0.005)
        observed.append(False)
        done.set()

    worker = threading.Thread(target=_worker)
    worker.start()
    try:
        time.sleep(0.02)
        token.cancel(CancellationReason.USER, "from main thread")
        assert done.wait(timeout=1.5), "Worker did not observe cancellation"
        assert observed == [True]
    finally:
        worker.join(timeout=1.0)


def test_raise_if_cancelled_raises_in_worker_thread() -> None:
    token = CancellationToken()
    captured: list[Cancelled] = []
    done = threading.Event()

    def _worker() -> None:
        try:
            for _ in range(200):
                token.raise_if_cancelled()
                time.sleep(0.005)
        except Cancelled as exc:
            captured.append(exc)
        finally:
            done.set()

    worker = threading.Thread(target=_worker)
    worker.start()
    try:
        time.sleep(0.02)
        token.cancel(CancellationReason.TIMEOUT, "wall clock")
        assert done.wait(timeout=1.5)
        assert len(captured) == 1
        assert captured[0].reason is CancellationReason.TIMEOUT
        assert captured[0].detail == "wall clock"
    finally:
        worker.join(timeout=1.0)


def test_never_cancelled_is_never_cancelled() -> None:
    token = never_cancelled()
    assert token.is_cancelled is False
    token.raise_if_cancelled()


def test_never_cancelled_returns_same_instance() -> None:
    assert never_cancelled() is never_cancelled()


def test_never_cancelled_wait_respects_timeout() -> None:
    token = never_cancelled()
    start = time.monotonic()
    result = token.wait(timeout=0.05)
    elapsed = time.monotonic() - start
    assert result is False
    assert elapsed >= 0.045
