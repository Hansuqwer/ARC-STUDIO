"""R-OPEN-HARDEN: retry/backoff unit tests.

Tests:
1. Provider error flag contract: retryable vs non-retryable.
2. Task.calculate_next_retry: exponential backoff formula.
3. Task.should_retry: gate conditions (status, retry_count).
4. Retry ceiling: retry_count >= max_retries → should_retry False.
5. Backoff monotonically increases with retry count.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# ── Provider error retryable flag contract ────────────────────────────────────


def test_rate_limit_error_is_retryable():
    from agent_runtime_cockpit.providers.base import RateLimitError

    assert RateLimitError("hit limit").retryable is True


def test_network_error_is_retryable():
    from agent_runtime_cockpit.providers.base import NetworkError

    assert NetworkError("timeout").retryable is True


@pytest.mark.parametrize(
    "cls_name", ["AuthError", "ValidationError", "ModelError", "CancelledError"]
)
def test_non_retryable_errors(cls_name):
    import agent_runtime_cockpit.providers.base as base

    cls = getattr(base, cls_name)
    assert cls("msg").retryable is False


def test_provider_error_retryable_override():
    """retryable can be overridden at construction time."""
    from agent_runtime_cockpit.providers.base import ProviderError

    assert ProviderError("msg", retryable=True).retryable is True
    assert ProviderError("msg", retryable=False).retryable is False


def test_cost_extraction_error_is_not_retryable():
    from agent_runtime_cockpit.providers.base import CostExtractionError

    err = CostExtractionError("gpt-99", "openai", ["gpt-4o"])
    assert err.retryable is False
    assert "gpt-99" in str(err)
    assert "openai" in str(err)


# ── Task retry / backoff ──────────────────────────────────────────────────────


def _task(retry_count=0, max_retries=3, status="failed"):
    from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType

    t = Task(
        type=TaskType.RUN,
        operation="run",
        workflow_id="wf-1",
        max_retries=max_retries,
    )
    t.retry_count = retry_count
    t.status = TaskStatus(status)
    return t


def test_should_retry_when_failed_and_under_limit():
    assert _task(retry_count=0, max_retries=3, status="failed").should_retry() is True
    assert _task(retry_count=2, max_retries=3, status="failed").should_retry() is True


def test_should_not_retry_at_limit():
    assert _task(retry_count=3, max_retries=3, status="failed").should_retry() is False


def test_should_not_retry_non_failed_status():
    for status in ("pending", "running", "completed", "cancelled"):
        assert _task(status=status).should_retry() is False, f"Should not retry {status}"


def test_calculate_next_retry_exponential_backoff():
    """delay = 2^retry_count seconds."""
    before = datetime.now(timezone.utc)
    for retry_count in range(5):
        t = _task(retry_count=retry_count)
        next_retry = datetime.fromisoformat(t.calculate_next_retry())
        elapsed = (next_retry - before).total_seconds()
        expected_delay = 2**retry_count
        # Allow 2s tolerance for test execution time
        assert elapsed >= expected_delay - 0.5, (
            f"retry_count={retry_count}: delay {elapsed:.1f}s < expected {expected_delay}s"
        )
        assert elapsed < expected_delay + 2.5, (
            f"retry_count={retry_count}: delay {elapsed:.1f}s >> expected {expected_delay}s"
        )


def test_backoff_is_monotonically_increasing():
    """Later retries must schedule further in the future than earlier ones."""
    times = []
    for retry_count in range(6):
        t = _task(retry_count=retry_count)
        times.append(datetime.fromisoformat(t.calculate_next_retry()))
    for i in range(1, len(times)):
        assert times[i] > times[i - 1]


@given(st.integers(min_value=0, max_value=20))
@settings(max_examples=40)
def test_backoff_formula_property(retry_count):
    """calculate_next_retry uses 2^retry_count seconds, for any retry_count."""
    t = _task(retry_count=retry_count)
    before = datetime.now(timezone.utc)
    next_retry = datetime.fromisoformat(t.calculate_next_retry())
    elapsed = (next_retry - before).total_seconds()
    expected = 2**retry_count
    # 2^20 = ~12 days; test is still fast because it's pure arithmetic
    assert abs(elapsed - expected) < 3.0, (
        f"retry_count={retry_count}: elapsed={elapsed:.1f}s expected={expected}s"
    )


def test_max_retries_zero_never_retries():
    assert _task(retry_count=0, max_retries=0, status="failed").should_retry() is False
