"""Tests for the Copilot Arena integration (P0).

Covers:
1. ArenaClient parses /create_pair response correctly
2. ArenaClient parses /create_edit_pair response correctly
3. ArenaClient.add_completion_outcome sends correct payload
4. ArenaProvider.complete() maps prompt→prefix, returns winner, stashes loser+pairId
5. ArenaProvider degrades gracefully when server returns no items
6. ArenaProvider raises NetworkError when client not configured
7. arena_request() routes to ArenaClient when ARC_ARENA_SERVER_URL is set
8. arena_request() falls back to stub when server URL not set
9. arena_request() falls back to stub when gates not met
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime_cockpit.arena.client import (
    ArenaClient,
    ArenaEditResponse,
    ArenaPairResponse,
)
from agent_runtime_cockpit.arena.models import ArenaMode, ArenaRequest, PrivacyLevel
from agent_runtime_cockpit.arena.service import arena_request
from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.providers.arena_provider import ArenaProvider
from agent_runtime_cockpit.providers.base import ProviderMessage, ProviderRequest


# ---------------------------------------------------------------------------
# 1. ArenaClient parses /create_pair response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_client_parses_create_pair_response():
    """ArenaClient.create_pair() parses completionItems correctly."""
    mock_response = {
        "pairId": "test-pair-123",
        "completionItems": [
            {
                "completionId": "comp-1",
                "model": "gpt-4o-mini",
                "completion": "def hello():\n    return 'world'",
                "pairIndex": 0,
                "pairCompletionId": "comp-2",
                "latency": 1.5,
            },
            {
                "completionId": "comp-2",
                "model": "claude-sonnet-4",
                "completion": "def hello():\n    print('world')",
                "pairIndex": 1,
                "pairCompletionId": "comp-1",
                "latency": 2.1,
            },
        ],
    }

    client = ArenaClient(base_url="http://localhost:8000")

    with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.create_pair(prefix="def hello():", suffix="")

    assert isinstance(result, ArenaPairResponse)
    assert result.pair_id == "test-pair-123"
    assert len(result.items) == 2
    assert result.items[0].model == "gpt-4o-mini"
    assert result.items[0].completion == "def hello():\n    return 'world'"
    assert result.items[0].pair_index == 0
    assert result.items[1].model == "claude-sonnet-4"
    assert result.items[1].latency == 2.1


# ---------------------------------------------------------------------------
# 2. ArenaClient parses /create_edit_pair response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_client_parses_create_edit_pair_response():
    """ArenaClient.create_edit_pair() parses responseItems correctly."""
    mock_response = {
        "pairId": "edit-pair-456",
        "responseItems": [
            {
                "responseId": "resp-1",
                "model": "gpt-4o",
                "response": "refactored code here",
                "pairIndex": 0,
                "pairResponseId": "resp-2",
                "latency": 3.0,
            },
            {
                "responseId": "resp-2",
                "model": "codestral-2405",
                "response": "alternative refactor",
                "pairIndex": 1,
                "pairResponseId": "resp-1",
                "latency": 2.5,
            },
        ],
    }

    client = ArenaClient(base_url="http://localhost:8000")

    with patch.object(client, "_post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.create_edit_pair(
            prefix="def old():",
            code_to_edit="pass",
            user_input="refactor this",
            language="python",
        )

    assert isinstance(result, ArenaEditResponse)
    assert result.pair_id == "edit-pair-456"
    assert len(result.items) == 2
    assert result.items[0].model == "gpt-4o"
    assert result.items[1].model == "codestral-2405"


# ---------------------------------------------------------------------------
# 3. ArenaClient.add_completion_outcome sends correct payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_client_add_completion_outcome_sends_correct_payload():
    """ArenaClient.add_completion_outcome() sends the vote payload."""
    client = ArenaClient(base_url="http://localhost:8000", user_id="test-user")

    completion_items = [
        {"completionId": "comp-1", "model": "gpt-4o-mini", "completion": "code1"},
        {"completionId": "comp-2", "model": "claude-sonnet-4", "completion": "code2"},
    ]

    with patch.object(client, "_put", new_callable=AsyncMock) as mock_put:
        await client.add_completion_outcome(
            pair_id="pair-123",
            accepted_index=0,
            completion_items=completion_items,
        )

    mock_put.assert_called_once()
    call_args = mock_put.call_args
    assert call_args[0][0] == "/add_completion_outcome"
    payload = call_args[0][1]
    assert payload["pairId"] == "pair-123"
    assert payload["userId"] == "test-user"
    assert payload["acceptedIndex"] == 0
    assert len(payload["completionItems"]) == 2


# ---------------------------------------------------------------------------
# 4. ArenaProvider.complete() maps prompt→prefix, returns winner, stashes loser
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_provider_complete_returns_winner_and_stashes_loser():
    """ArenaProvider.complete() returns winner content and stashes loser in metadata."""
    from agent_runtime_cockpit.arena.client import ArenaCompletionItem

    mock_pair = ArenaPairResponse(
        pair_id="pair-789",
        items=[
            ArenaCompletionItem(
                completion_id="comp-w",
                model="gpt-4o-mini",
                completion="winner code",
                pair_index=0,
                pair_completion_id="comp-l",
                latency=1.0,
            ),
            ArenaCompletionItem(
                completion_id="comp-l",
                model="claude-sonnet-4",
                completion="loser code",
                pair_index=1,
                pair_completion_id="comp-w",
                latency=2.0,
            ),
        ],
    )

    mock_client = MagicMock()
    mock_client.create_pair = AsyncMock(return_value=mock_pair)

    provider = ArenaProvider(client=mock_client)
    request = ProviderRequest(
        model="arena-battle",
        messages=[ProviderMessage(role="user", content="write hello world")],
        max_tokens=512,
        temperature=0.5,
    )

    response = await provider.complete(request, cancellation_token=CancellationToken())

    assert response.content == "winner code"
    assert response.model == "gpt-4o-mini"
    assert response.finish_reason == "stop"
    assert response.metadata["arena_pair_id"] == "pair-789"
    assert response.metadata["arena_winner_model"] == "gpt-4o-mini"
    assert response.metadata["arena_loser_model"] == "claude-sonnet-4"
    assert response.metadata["arena_loser_content"] == "loser code"


# ---------------------------------------------------------------------------
# 5. ArenaProvider degrades gracefully when server returns no items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_provider_degrades_when_no_items():
    """ArenaProvider.complete() returns degraded response when server returns empty."""
    mock_pair = ArenaPairResponse(pair_id="pair-empty", items=[])

    mock_client = MagicMock()
    mock_client.create_pair = AsyncMock(return_value=mock_pair)

    provider = ArenaProvider(client=mock_client)
    request = ProviderRequest(
        model="arena-battle",
        messages=[ProviderMessage(role="user", content="test")],
        max_tokens=256,
    )

    response = await provider.complete(request, cancellation_token=CancellationToken())

    assert response.content == ""
    assert response.finish_reason == "error"
    assert response.degraded is True
    assert "no completions" in response.degraded_reason


# ---------------------------------------------------------------------------
# 6. ArenaProvider raises NetworkError when client not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arena_provider_raises_when_not_configured():
    """ArenaProvider.complete() raises NetworkError when no client."""
    provider = ArenaProvider(client=None)
    request = ProviderRequest(
        model="arena-battle",
        messages=[ProviderMessage(role="user", content="test")],
        max_tokens=256,
    )

    from agent_runtime_cockpit.providers.base import NetworkError

    with pytest.raises(NetworkError, match="not configured"):
        await provider.complete(request, cancellation_token=CancellationToken())


# ---------------------------------------------------------------------------
# 7. arena_request() routes to ArenaClient when ARC_ARENA_SERVER_URL is set
# ---------------------------------------------------------------------------


def test_arena_request_routes_to_server_when_url_set(tmp_path: Path, monkeypatch):
    """arena_request() calls _arena_server_response when ARC_ARENA_SERVER_URL is set."""
    monkeypatch.setenv("ARC_ARENA_SERVER_URL", "http://localhost:8000")
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    monkeypatch.setenv("ARC_LMARENA_ALLOW_COSTS", "true")

    req = ArenaRequest(
        mode=ArenaMode.BATTLE,
        prompt="test prompt",
        workspace=str(tmp_path),
        privacy=PrivacyLevel.PRIVATE,
    )

    with patch("agent_runtime_cockpit.arena.service._arena_server_response") as mock_server:
        from agent_runtime_cockpit.arena.models import ArenaResponse

        mock_server.return_value = ArenaResponse(
            run_id="server-run",
            mode=ArenaMode.BATTLE,
            candidates=[],
        )
        result = arena_request(tmp_path, req)

    mock_server.assert_called_once()
    assert result.run_id == "server-run"


# ---------------------------------------------------------------------------
# 8. arena_request() falls back to stub when server URL not set
# ---------------------------------------------------------------------------


def test_arena_request_falls_back_to_stub_when_no_server_url(tmp_path: Path, monkeypatch):
    """arena_request() uses stub when ARC_ARENA_SERVER_URL is not set."""
    monkeypatch.delenv("ARC_ARENA_SERVER_URL", raising=False)
    monkeypatch.delenv("ARC_ALLOW_LIVE_ARENA", raising=False)

    req = ArenaRequest(
        mode=ArenaMode.BATTLE,
        prompt="test prompt",
        workspace=str(tmp_path),
        privacy=PrivacyLevel.PRIVATE,
    )

    result = arena_request(tmp_path, req)

    assert result.mode == ArenaMode.BATTLE
    assert len(result.candidates) == 2
    assert "Stub mode" in result.warnings[0]


# ---------------------------------------------------------------------------
# 9. arena_request() falls back to stub when gates not met
# ---------------------------------------------------------------------------


def test_arena_request_falls_back_when_gates_not_met(tmp_path: Path, monkeypatch):
    """arena_request() uses stub when ARC_ALLOW_LIVE_ARENA is not true."""
    monkeypatch.setenv("ARC_ARENA_SERVER_URL", "http://localhost:8000")
    monkeypatch.delenv("ARC_ALLOW_LIVE_ARENA", raising=False)

    req = ArenaRequest(
        mode=ArenaMode.BATTLE,
        prompt="test prompt",
        workspace=str(tmp_path),
        privacy=PrivacyLevel.PRIVATE,
    )

    result = arena_request(tmp_path, req)

    assert result.mode == ArenaMode.BATTLE
    assert len(result.candidates) == 2
    assert "Stub mode" in result.warnings[0]
