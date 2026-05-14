"""Tests for Arena data models."""
from agent_runtime_cockpit.arena.models import (
    ArenaMode,
    ArenaRequest,
    ArenaResponse,
    ArenaCandidate,
    ArenaVote,
    ArenaAdoptRequest,
    ArenaAdoptResult,
    PrivacyLevel,
)


def test_arena_modes():
    assert ArenaMode.BATTLE.value == "battle"
    assert ArenaMode.DIRECT.value == "direct"
    assert ArenaMode.CODE.value == "code"
    assert ArenaMode.AGENT_ARENA_PREVIEW.value == "agent-arena-preview"


def test_arena_request_defaults():
    req = ArenaRequest(prompt="test prompt")
    assert req.mode == ArenaMode.BATTLE
    assert req.privacy == PrivacyLevel.PRIVATE
    assert req.allow_paid_calls is False
    assert req.profile_id == "local-safe"


def test_arena_response_with_candidates():
    resp = ArenaResponse(
        run_id="test-run-001",
        mode=ArenaMode.BATTLE,
        candidates=[
            ArenaCandidate(id="c1", model="gpt-4o", text="response A"),
            ArenaCandidate(id="c2", model="claude-sonnet", text="response B"),
        ],
    )
    assert len(resp.candidates) == 2
    assert resp.mode == ArenaMode.BATTLE
    assert resp.generated_at != ""


def test_arena_vote():
    vote = ArenaVote(run_id="test-run", winner_candidate_id="c1", loser_candidate_id="c2")
    assert vote.run_id == "test-run"
    assert vote.winner_candidate_id == "c1"
    assert vote.timestamp != ""


def test_arena_adopt_result():
    result = ArenaAdoptResult(applied=True, file_changed="src/main.py", patch_lines=10)
    assert result.applied is True
    assert result.patch_lines == 10
