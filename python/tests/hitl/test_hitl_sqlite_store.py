"""Tests for HITL SQLite storage (Phase 29 / R22)."""

import tempfile
import time
from pathlib import Path

import pytest

from agent_runtime_cockpit.audit.hitl import HitlDecision, HitlPrompt
from agent_runtime_cockpit.audit.hitl_sqlite_store import HitlSqliteStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_hitl.db"
        yield db_path


@pytest.fixture
def store(temp_db):
    """Create a HitlSqliteStore instance with temporary database."""
    return HitlSqliteStore(temp_db)


@pytest.fixture
def sample_prompt():
    """Create a sample HITL prompt for testing."""
    return HitlPrompt(
        hitl_id="test_hitl_001",
        run_id="test_run_001",
        step_id="step_001",
        prompt_text="Approve this action?",
        context={"action": "delete_file", "file": "test.txt"},
        options=["approve", "reject"],
        timeout_seconds=300,
    )


def test_store_initialization(store, temp_db):
    """Test store initialization creates database."""
    store.init_db()
    assert temp_db.exists()


def test_save_prompt(store, sample_prompt):
    """Test saving a HITL prompt."""
    token = store.save_prompt(sample_prompt, expiry_seconds=3600)

    assert token is not None
    assert len(token) > 0

    # Verify prompt was saved
    retrieved = store.get_prompt(sample_prompt.hitl_id)
    assert retrieved is not None
    assert retrieved.hitl_id == sample_prompt.hitl_id
    assert retrieved.run_id == sample_prompt.run_id
    assert retrieved.prompt_text == sample_prompt.prompt_text


def test_list_prompts_empty(store):
    """Test listing prompts when none exist."""
    prompts = store.list_prompts()
    assert len(prompts) == 0


def test_list_prompts_with_data(store, sample_prompt):
    """Test listing prompts with data."""
    store.save_prompt(sample_prompt)

    prompts = store.list_prompts()
    assert len(prompts) == 1
    assert prompts[0].hitl_id == sample_prompt.hitl_id


def test_list_prompts_excludes_expired(store, sample_prompt):
    """Test that expired prompts are excluded by default."""
    # Save prompt with very short expiry
    store.save_prompt(sample_prompt, expiry_seconds=1)

    # Wait for expiry
    time.sleep(1.5)

    # Should not be listed
    prompts = store.list_prompts(include_expired=False)
    assert len(prompts) == 0

    # Should be listed when including expired
    prompts = store.list_prompts(include_expired=True)
    assert len(prompts) == 1


def test_get_prompt(store, sample_prompt):
    """Test getting a specific prompt."""
    store.save_prompt(sample_prompt)

    retrieved = store.get_prompt(sample_prompt.hitl_id)
    assert retrieved is not None
    assert retrieved.hitl_id == sample_prompt.hitl_id
    assert retrieved.run_id == sample_prompt.run_id
    assert retrieved.step_id == sample_prompt.step_id
    assert retrieved.prompt_text == sample_prompt.prompt_text
    assert retrieved.context == sample_prompt.context


def test_get_prompt_not_found(store):
    """Test getting a non-existent prompt."""
    retrieved = store.get_prompt("nonexistent")
    assert retrieved is None


def test_get_token(store, sample_prompt):
    """Test getting the token for a prompt."""
    token = store.save_prompt(sample_prompt)

    retrieved_token = store.get_token(sample_prompt.hitl_id)
    assert retrieved_token == token


def test_get_token_expired(store, sample_prompt):
    """Test that token is not returned for expired prompts."""
    store.save_prompt(sample_prompt, expiry_seconds=1)

    # Wait for expiry
    time.sleep(1.5)

    token = store.get_token(sample_prompt.hitl_id)
    assert token is None


def test_respond_to_prompt(store, sample_prompt):
    """Test responding to a HITL prompt."""
    token = store.save_prompt(sample_prompt)

    response = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token=token,
        operator_id="test_operator",
        notes="Looks good",
    )

    assert response is not None
    assert response.hitl_id == sample_prompt.hitl_id
    assert response.run_id == sample_prompt.run_id
    assert response.decision == HitlDecision.APPROVE
    assert response.operator_id == "test_operator"
    assert response.notes == "Looks good"


def test_respond_with_wrong_token(store, sample_prompt):
    """Test that responding with wrong token fails."""
    store.save_prompt(sample_prompt)

    response = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token="wrong_token",
        operator_id="test_operator",
    )

    assert response is None


def test_respond_to_expired_prompt(store, sample_prompt):
    """Test that responding to expired prompt fails."""
    token = store.save_prompt(sample_prompt, expiry_seconds=1)

    # Wait for expiry
    time.sleep(1.5)

    response = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token=token,
        operator_id="test_operator",
    )

    assert response is None


def test_respond_twice_fails(store, sample_prompt):
    """Test that responding twice to the same prompt fails."""
    token = store.save_prompt(sample_prompt)

    # First response succeeds
    response1 = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token=token,
        operator_id="test_operator",
    )
    assert response1 is not None

    # Second response fails
    response2 = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.REJECT,
        token=token,
        operator_id="test_operator",
    )
    assert response2 is None


def test_get_response(store, sample_prompt):
    """Test getting a response for a prompt."""
    token = store.save_prompt(sample_prompt)

    # Respond to prompt
    store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token=token,
        operator_id="test_operator",
        notes="Test notes",
    )

    # Get response
    response = store.get_response(sample_prompt.hitl_id)
    assert response is not None
    assert response.hitl_id == sample_prompt.hitl_id
    assert response.decision == HitlDecision.APPROVE
    assert response.operator_id == "test_operator"
    assert response.notes == "Test notes"


def test_get_response_not_found(store):
    """Test getting response for non-existent prompt."""
    response = store.get_response("nonexistent")
    assert response is None


def test_prune_expired(store):
    """Test pruning expired prompts."""
    # Create prompts with different expiry times
    prompt1 = HitlPrompt(
        hitl_id="prompt1",
        run_id="run1",
        step_id="step1",
        prompt_text="Prompt 1",
    )
    prompt2 = HitlPrompt(
        hitl_id="prompt2",
        run_id="run2",
        step_id="step2",
        prompt_text="Prompt 2",
    )
    prompt3 = HitlPrompt(
        hitl_id="prompt3",
        run_id="run3",
        step_id="step3",
        prompt_text="Prompt 3",
    )

    # Save with different expiry times
    store.save_prompt(prompt1, expiry_seconds=1)  # Will expire
    store.save_prompt(prompt2, expiry_seconds=1)  # Will expire
    store.save_prompt(prompt3, expiry_seconds=3600)  # Won't expire

    # Wait for expiry
    time.sleep(1.5)

    # Prune expired
    pruned = store.prune_expired()
    assert pruned == 2

    # Verify only prompt3 remains
    prompts = store.list_prompts(include_expired=True)
    assert len(prompts) == 1
    assert prompts[0].hitl_id == "prompt3"


def test_list_responses_for_run(store):
    """Test listing all responses for a specific run."""
    # Create multiple prompts for the same run
    prompt1 = HitlPrompt(
        hitl_id="prompt1",
        run_id="test_run",
        step_id="step1",
        prompt_text="Prompt 1",
    )
    prompt2 = HitlPrompt(
        hitl_id="prompt2",
        run_id="test_run",
        step_id="step2",
        prompt_text="Prompt 2",
    )
    prompt3 = HitlPrompt(
        hitl_id="prompt3",
        run_id="other_run",
        step_id="step3",
        prompt_text="Prompt 3",
    )

    token1 = store.save_prompt(prompt1)
    token2 = store.save_prompt(prompt2)
    token3 = store.save_prompt(prompt3)

    # Respond to all prompts
    store.respond(prompt1.hitl_id, HitlDecision.APPROVE, token1)
    store.respond(prompt2.hitl_id, HitlDecision.REJECT, token2)
    store.respond(prompt3.hitl_id, HitlDecision.APPROVE, token3)

    # List responses for test_run
    responses = store.list_responses_for_run("test_run")
    assert len(responses) == 2

    hitl_ids = {r.hitl_id for r in responses}
    assert "prompt1" in hitl_ids
    assert "prompt2" in hitl_ids
    assert "prompt3" not in hitl_ids


def test_respond_with_audit_hash(store, sample_prompt):
    """Test responding with audit hash for linking to audit chain."""
    token = store.save_prompt(sample_prompt)

    audit_hash = "abc123def456"
    response = store.respond(
        hitl_id=sample_prompt.hitl_id,
        decision=HitlDecision.APPROVE,
        token=token,
        operator_id="test_operator",
        notes="Approved",
        audit_hash=audit_hash,
    )

    assert response is not None
    # Note: audit_hash is stored but not returned in HitlResponse model
    # This is for audit chain linking purposes
