"""Tests for SwarmGraph arena battle fan-out.

Covers:
1. Queen spawns N=4 workers with ArenaProvider → 4 battles (8 candidates)
2. Each worker stores arena metadata in artifacts
3. Consensus emits ArenaVoteEvents for each battle
4. Runner emits votes to arena server after run completes
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from swarmgraph.config import ExecutionMode, SwarmGraphConfig
from swarmgraph.events import ArenaVoteEvent, SwarmGraphEventKind
from swarmgraph.runner import SwarmGraphRunner


class MockArenaResponse:
    """Duck-typed provider response with arena metadata."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.model = "gpt-4o-mini"
        self.content = "winner code"
        self.finish_reason = "stop"
        self.degraded = False
        self.degraded_reason = None
        self.tool_calls = []
        self.usage = MagicMock(
            input_tokens=10,
            output_tokens=20,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        self.metadata = {
            "arena_pair_id": f"pair-{call_id[:8]}",
            "arena_winner_model": "gpt-4o-mini",
            "arena_winner_index": 0,
            "arena_loser_model": "claude-sonnet-4",
            "arena_loser_index": 1,
            "arena_loser_content": "loser code",
        }


class MockArenaProvider:
    """Mock ArenaProvider that returns deterministic winner/loser."""

    def capabilities(self):
        cap = MagicMock()
        cap.provider_id = "arena"
        cap.default_model = "arena-battle"
        return cap

    async def complete(self, request, *, cancellation_token):
        return MockArenaResponse(call_id=request.call_id)


def test_arena_battle_fanout_4_workers_4_battles():
    """Queen spawns 4 workers → 4 battles → 4 ArenaVoteEvents."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        arena_battle_mode=True,
        num_workers=4,
        max_rounds=1,
        fan_out_threshold=0.0,  # Force 4 workers regardless of prompt
        allow_paid_calls=True,  # Required for provider_backed mode
    )
    provider = MockArenaProvider()
    runner = SwarmGraphRunner(config=config, provider=provider)

    result = runner.run("test prompt")

    # Check that 4 tasks were created
    assert result["total_tasks"] == 4
    assert result["completed_tasks"] == 4

    # Check that 4 ArenaVoteEvents were emitted
    arena_vote_events = [evt for evt in result["events"] if evt["kind"] == "arena_vote"]
    assert len(arena_vote_events) == 4

    # Check that each event has the correct structure
    for evt in arena_vote_events:
        assert "pair_id" in evt["data"]
        assert "accepted_index" in evt["data"]
        assert evt["data"]["accepted_index"] == 0  # Winner is always index 0
        assert "winner_model" in evt["data"]
        assert "loser_model" in evt["data"]


def test_arena_battle_worker_stores_metadata():
    """Each worker stores arena metadata in artifacts."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        arena_battle_mode=True,
        num_workers=2,
        max_rounds=1,
        fan_out_threshold=0.0,
    )
    provider = MockArenaProvider()
    runner = SwarmGraphRunner(config=config, provider=provider)

    runner.run("test prompt")

    # Check that tasks have arena metadata in their results
    # (This is stored in the state, not directly in the result dict)
    assert runner.state is not None
    for task in runner.state.tasks.values():
        if task.result:
            assert "arena_pair_id" in task.result.artifacts
            assert "arena_winner_model" in task.result.artifacts
            assert "arena_loser_model" in task.result.artifacts


def test_arena_battle_no_votes_when_disabled():
    """No ArenaVoteEvents when arena_battle_mode is False."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        arena_battle_mode=False,  # Disabled
        num_workers=2,
        max_rounds=1,
    )
    provider = MockArenaProvider()
    runner = SwarmGraphRunner(config=config, provider=provider)

    result = runner.run("test prompt")

    # Check that no ArenaVoteEvents were emitted
    arena_vote_events = [evt for evt in result["events"] if evt["kind"] == "arena_vote"]
    assert len(arena_vote_events) == 0


def test_arena_battle_no_votes_when_no_provider():
    """No ArenaVoteEvents when provider is None (fake_offline)."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.fake_offline,
        arena_battle_mode=True,
        num_workers=2,
        max_rounds=1,
        fan_out_threshold=0.0,
    )
    runner = SwarmGraphRunner(config=config, provider=None)

    result = runner.run("test prompt")

    # Check that no ArenaVoteEvents were emitted
    arena_vote_events = [evt for evt in result["events"] if evt["kind"] == "arena_vote"]
    assert len(arena_vote_events) == 0


def test_arena_battle_emits_votes_to_server():
    """Runner emits votes to arena server after run completes."""
    config = SwarmGraphConfig(
        execution_mode=ExecutionMode.provider_backed,
        arena_battle_mode=True,
        num_workers=2,
        max_rounds=1,
        fan_out_threshold=0.0,
    )
    provider = MockArenaProvider()
    runner = SwarmGraphRunner(config=config, provider=provider)

    # Mock ArenaClient
    with patch("agent_runtime_cockpit.arena.client.ArenaClient.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_client.add_completion_outcome = AsyncMock()
        mock_from_env.return_value = mock_client

        runner.run("test prompt")

        # Check that add_completion_outcome was called for each battle
        assert mock_client.add_completion_outcome.call_count == 2


def test_arena_battle_vote_event_structure():
    """ArenaVoteEvent has the correct structure."""
    from swarmgraph.events import emit_arena_vote_event
    from swarmgraph.state import SwarmState

    state = SwarmState(config=SwarmGraphConfig())
    event = emit_arena_vote_event(
        state=state,
        task_id="task-1",
        pair_id="pair-123",
        accepted_index=0,
        winner_model="gpt-4o-mini",
        loser_model="claude-sonnet-4",
    )

    assert isinstance(event, ArenaVoteEvent)
    assert event.kind == SwarmGraphEventKind.arena_vote
    assert event.data["task_id"] == "task-1"
    assert event.data["pair_id"] == "pair-123"
    assert event.data["accepted_index"] == 0
    assert event.data["winner_model"] == "gpt-4o-mini"
    assert event.data["loser_model"] == "claude-sonnet-4"
