# Prompt — R-OPEN-HARDEN: Provider Error Hardening Research + Plan

> **Status:** Research complete 2026-06-06. Execute this prompt to implement.

## Verified findings (from live codebase inspection)

1. **Retry infrastructure exists but is unwired.** `providers/base.py` has:
   - `RateLimitError`, `NetworkError`, `ProviderError.is_retryable()`
   - `calculate_next_retry_delay(retry_count)` — exponential backoff
   - `Task.should_retry()` — checks `max_retries` and status
   - Tests in `tests/test_harden_retry.py` verify all of the above.
   
2. **`run_turn` does not retry.** `runtime/turn_manager.py` has zero references to
   `RateLimitError`, `is_retryable`, or `retry`. Provider errors propagate raw to
   the caller. The retry infrastructure is tested in isolation but never called.

3. **Budget survives gracefully** (SQLite WAL, documented last-writer-wins).

## Scope (Phase 123)

One bounded slice: **wire the existing retry logic into `run_turn`** so that
`RateLimitError` and `NetworkError` trigger the documented backoff before
propagating.

### Acceptance criteria
- `run_turn` catches `RateLimitError`/`NetworkError` from the provider call,
  sleeps the documented backoff, and retries up to `max_retries` (configurable,
  default 2).
- Non-retryable errors (`AuthError`, `ValidationError`, etc.) propagate immediately.
- New tests: failure-injection via monkeypatch, verify retry count, verify
  `AuthError` not retried.
- No fabricated benchmark numbers. No claims about "production-grade retry."

## Method

- Read `runtime/turn_manager.py` to find the provider call site.
- Read `providers/base.py` retry helpers.
- Add a narrow `_with_retry` helper in `turn_manager.py` that wraps the provider call.
- Wire `asyncio.sleep` (real delay) gated by `ARC_DISABLE_RETRY_SLEEP=1` in tests.
- Tests: monkeypatch the provider to raise on first N calls, succeed on N+1.

## Constraints

- `asyncio.sleep` in tests must be skipped (mock or `ARC_DISABLE_RETRY_SLEEP=1`).
- Default `max_retries=2`, configurable via provider config or env.
- Do not add retries to the streaming path (out of scope for this slice).
- Banned-claims clean: no "production-grade retry", "zero downtime", etc.
