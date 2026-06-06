"""Tests for FallbackProviderClient — multi-provider failover (R-OPEN-HARDEN slice 4)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import never_cancelled
from agent_runtime_cockpit.providers import ProviderResponse, StreamChunk, UsageRecord
from agent_runtime_cockpit.providers.base import AuthError, NetworkError, RateLimitError
from agent_runtime_cockpit.providers.fallback import FallbackProviderClient


def _response(content: str = "ok") -> ProviderResponse:
    return ProviderResponse(
        call_id="c1",
        model="test",
        content=content,
        finish_reason="stop",
        usage=UsageRecord(input_tokens=1, output_tokens=1),
    )


class _StubClient:
    def __init__(self, *, response=None, raises=None, chunks=None, chunks_then_raise=None):
        self._response = response
        self._raises = raises
        self._chunks = chunks or []
        self._chunks_then_raise = chunks_then_raise
        self.complete_calls = 0
        self.stream_calls = 0
        self.cancelled = []

    def capabilities(self):
        return {"id": "stub"}

    async def complete(self, request, *, cancellation_token):
        self.complete_calls += 1
        if self._raises is not None:
            raise self._raises
        return self._response or _response()

    async def stream(self, request, *, cancellation_token):
        self.stream_calls += 1
        for c in self._chunks:
            yield c
        if self._chunks_then_raise is not None:
            raise self._chunks_then_raise
        if self._raises is not None:
            raise self._raises

    async def cancel(self, call_id):
        self.cancelled.append(call_id)


def test_empty_clients_rejected():
    with pytest.raises(ValueError):
        FallbackProviderClient([])


@pytest.mark.asyncio
async def test_primary_success_no_failover():
    primary = _StubClient(response=_response("primary"))
    secondary = _StubClient(response=_response("secondary"))
    fb = FallbackProviderClient([primary, secondary])
    result = await fb.complete(object(), cancellation_token=never_cancelled())
    assert result.content == "primary"
    assert primary.complete_calls == 1
    assert secondary.complete_calls == 0


@pytest.mark.asyncio
async def test_failover_on_retryable_error():
    primary = _StubClient(raises=RateLimitError("429"))
    secondary = _StubClient(response=_response("secondary"))
    fb = FallbackProviderClient([primary, secondary])
    result = await fb.complete(object(), cancellation_token=never_cancelled())
    assert result.content == "secondary"
    assert primary.complete_calls == 1
    assert secondary.complete_calls == 1


@pytest.mark.asyncio
async def test_failover_chain_of_three():
    p1 = _StubClient(raises=RateLimitError("429"))
    p2 = _StubClient(raises=NetworkError("timeout"))
    p3 = _StubClient(response=_response("third"))
    fb = FallbackProviderClient([p1, p2, p3])
    result = await fb.complete(object(), cancellation_token=never_cancelled())
    assert result.content == "third"
    assert (p1.complete_calls, p2.complete_calls, p3.complete_calls) == (1, 1, 1)


@pytest.mark.asyncio
async def test_non_retryable_does_not_failover():
    primary = _StubClient(raises=AuthError("bad key"))
    secondary = _StubClient(response=_response("secondary"))
    fb = FallbackProviderClient([primary, secondary])
    with pytest.raises(AuthError):
        await fb.complete(object(), cancellation_token=never_cancelled())
    assert primary.complete_calls == 1
    assert secondary.complete_calls == 0  # never reached


@pytest.mark.asyncio
async def test_all_providers_exhausted_raises_last():
    p1 = _StubClient(raises=RateLimitError("429"))
    p2 = _StubClient(raises=NetworkError("last error"))
    fb = FallbackProviderClient([p1, p2])
    with pytest.raises(NetworkError):
        await fb.complete(object(), cancellation_token=never_cancelled())


@pytest.mark.asyncio
async def test_stream_failover_before_first_chunk():
    primary = _StubClient(raises=RateLimitError("429"))
    chunk = StreamChunk(call_id="c1", chunk_type="delta", delta="hi", payload={})
    secondary = _StubClient(chunks=[chunk])
    fb = FallbackProviderClient([primary, secondary])
    out = [c async for c in fb.stream(object(), cancellation_token=never_cancelled())]
    assert [c.delta for c in out] == ["hi"]
    assert primary.stream_calls == 1
    assert secondary.stream_calls == 1


@pytest.mark.asyncio
async def test_stream_no_failover_after_first_chunk():
    chunk = StreamChunk(call_id="c1", chunk_type="delta", delta="partial", payload={})
    primary = _StubClient(chunks=[chunk], chunks_then_raise=RateLimitError("mid-stream"))
    secondary = _StubClient(
        chunks=[StreamChunk(call_id="c1", chunk_type="delta", delta="should-not", payload={})]
    )
    fb = FallbackProviderClient([primary, secondary])
    collected = []
    with pytest.raises(RateLimitError):
        async for c in fb.stream(object(), cancellation_token=never_cancelled()):
            collected.append(c.delta)
    assert collected == ["partial"]  # no duplicate from secondary
    assert secondary.stream_calls == 0


@pytest.mark.asyncio
async def test_cancel_best_effort_all():
    p1 = _StubClient(response=_response())
    p2 = _StubClient(response=_response())
    fb = FallbackProviderClient([p1, p2])
    await fb.cancel("call-1")
    assert p1.cancelled == ["call-1"]
    assert p2.cancelled == ["call-1"]
