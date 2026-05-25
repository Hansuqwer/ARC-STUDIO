"""Web integration tests for Arena endpoints."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_arena_models_returns_ok(client):
    """GET /api/arena/models returns a list of models."""
    r = await client.get("/api/arena/models")
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) > 0
    # Check model structure
    model = data[0]
    assert "id" in model
    assert "name" in model
    assert "provider" in model


async def test_arena_models_filter_by_tags(client):
    """GET /api/arena/models?tags=fast returns filtered models."""
    r = await client.get("/api/arena/models?tags=fast")
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", [])
    assert isinstance(data, list)
    # All returned models should have 'fast' in their tags
    for model in data:
        assert "fast" in model.get("tags", [])


async def test_arena_tags_returns_ok(client):
    """GET /api/arena/tags returns tag descriptions."""
    r = await client.get("/api/arena/tags")
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert isinstance(data, dict)
    assert "fast" in data
    assert "best" in data


async def test_arena_chat_direct_mode(client):
    """POST /api/arena/chat in direct mode returns a response."""
    r = await client.post(
        "/api/arena/chat",
        json={
            "mode": "direct",
            "prompt": "Hello, Arena!",
            "model": "gpt-4o-mini-2024-07-18",
            "privacy": "Private",
            "allow_paid_calls": False,
            "profile_id": "local-safe",
        },
    )
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert "run_id" in data
    assert data.get("mode") == "direct"
    assert "candidates" in data
    assert len(data["candidates"]) >= 1


async def test_arena_chat_battle_mode(client):
    """POST /api/arena/chat in battle mode returns multiple candidates."""
    r = await client.post(
        "/api/arena/chat",
        json={
            "mode": "battle",
            "prompt": "Compare models",
            "model_tags": ["fast"],
            "privacy": "Private",
            "allow_paid_calls": False,
            "profile_id": "local-safe",
        },
    )
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert data.get("mode") == "battle"
    assert len(data.get("candidates", [])) >= 2


async def test_arena_chat_invalid_mode(client):
    """POST /api/arena/chat with invalid mode returns a stable error envelope."""
    r = await client.post(
        "/api/arena/chat",
        json={
            "mode": "invalid-mode",
            "prompt": "test",
            "privacy": "Private",
            "allow_paid_calls": False,
            "profile_id": "local-safe",
        },
    )
    assert r.status_code == 400
    body = await r.json()
    assert body.get("ok") is False


async def test_arena_vote_records(client):
    """POST /api/arena/vote records a vote for a run."""
    # First create a battle run
    chat_r = await client.post(
        "/api/arena/chat",
        json={
            "mode": "battle",
            "prompt": "Vote test",
            "model_tags": ["fast"],
            "privacy": "Private",
            "allow_paid_calls": False,
            "profile_id": "local-safe",
        },
    )
    chat_body = await chat_r.json()
    run_id = chat_body.get("data", {}).get("run_id")
    candidates = chat_body.get("data", {}).get("candidates", [])

    if not run_id or len(candidates) < 2:
        pytest.skip("Could not create battle run for vote test")

    # Vote for the first candidate
    vote_r = await client.post(
        "/api/arena/vote",
        json={
            "run_id": run_id,
            "winner_candidate_id": candidates[0]["id"],
            "loser_candidate_id": candidates[1]["id"],
            "voter": "test-user",
        },
    )
    assert vote_r.status_code == 200
    vote_body = await vote_r.json()
    assert vote_body.get("ok") is True
    assert vote_body.get("data", {}).get("recorded") is True


async def test_arena_vote_nonexistent_run(client):
    """POST /api/arena/vote for non-existent run returns 404."""
    r = await client.post(
        "/api/arena/vote",
        json={
            "run_id": "nonexistent-run-id",
            "winner_candidate_id": "c1",
            "loser_candidate_id": "c2",
        },
    )
    assert r.status_code == 404


async def test_arena_adopt_stub_mode(client):
    """POST /api/arena/adopt returns stub mode message."""
    r = await client.post(
        "/api/arena/adopt",
        json={
            "run_id": "test-run",
            "candidate_id": "c1",
            "target_file": "src/test.py",
        },
    )
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    # Stub mode returns applied=False
    assert data.get("applied") is False
    assert "stub" in data.get("message", "").lower()


async def test_arena_rankings_empty(client):
    """GET /api/arena/rankings returns empty rankings when no votes exist."""
    r = await client.get("/api/arena/rankings")
    assert r.status_code == 200
    body = await r.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert "total_votes" in data
    assert "votes" in data
    assert "rankings" in data
    assert isinstance(data["votes"], list)
    assert isinstance(data["rankings"], list)


async def test_arena_rankings_after_vote(client):
    """GET /api/arena/rankings returns rankings after votes are recorded."""
    # Create a battle run
    chat_r = await client.post(
        "/api/arena/chat",
        json={
            "mode": "battle",
            "prompt": "Rankings test",
            "model_tags": ["fast"],
            "privacy": "Private",
            "allow_paid_calls": False,
            "profile_id": "local-safe",
        },
    )
    chat_body = await chat_r.json()
    run_id = chat_body.get("data", {}).get("run_id")
    candidates = chat_body.get("data", {}).get("candidates", [])

    if not run_id or len(candidates) < 2:
        pytest.skip("Could not create battle run for rankings test")

    # Record a vote
    await client.post(
        "/api/arena/vote",
        json={
            "run_id": run_id,
            "winner_candidate_id": candidates[0]["id"],
            "loser_candidate_id": candidates[1]["id"],
            "voter": "test-user",
        },
    )

    # Check rankings
    r = await client.get("/api/arena/rankings")
    assert r.status_code == 200
    body = await r.json()
    data = body.get("data", {})
    assert data.get("total_votes") >= 1
    assert len(data.get("votes", [])) >= 1
    assert len(data.get("rankings", [])) >= 1
