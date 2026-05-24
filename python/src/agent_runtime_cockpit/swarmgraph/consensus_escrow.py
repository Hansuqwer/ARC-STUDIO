"""Consensus Escrow - Commit-Reveal Voting for SwarmGraph.

Phase 30/R23 implementation: Cryptographic commit-reveal protocol to prevent
vote manipulation in consensus. Workers commit to a vote hash before revealing
the actual vote, preventing strategic vote changes after seeing other votes.

Architecture:
- Commit phase: hash(canonical_json(vote) || nonce) → commit_hash
- Reveal phase: vote + nonce → recompute hash → verify against commit
- Audit chain: records commit and reveal timestamps for tamper detection
- Opt-in: enabled via --consensus-escrow flag or adaptive high-risk selection
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from .config import ConsensusProtocol
from .consensus import ConsensusResult, run_consensus
from .models import AgentVote

if TYPE_CHECKING:
    from ..audit.hmac_chain import HmacAuditChainWriter


class VoteCommit(BaseModel):
    """Cryptographic commitment to a vote without revealing the vote itself.

    Represents the commit phase of commit-reveal voting. Contains only the
    hash of the vote, preventing vote manipulation while preserving privacy.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str = Field(..., min_length=1, max_length=128)
    task_id: str = Field(..., min_length=1, max_length=128)
    round: int = Field(default=0, ge=0)
    commit_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    commit_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommitRevealVote(BaseModel):
    """Revealed vote with nonce for verification against prior commitment.

    Represents the reveal phase of commit-reveal voting. Contains the actual
    vote, nonce, and original commit hash for verification.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    vote: AgentVote
    nonce: str = Field(..., min_length=32, max_length=128)  # Hex-encoded random bytes
    commit_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    commit_timestamp: datetime
    reveal_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusEscrowError(Exception):
    """Base exception for consensus escrow errors."""

    pass


class VoteVerificationError(ConsensusEscrowError):
    """Raised when vote verification fails (hash mismatch)."""

    pass


class VoteMismatchError(ConsensusEscrowError):
    """Raised when revealed vote doesn't match commit metadata."""

    pass


def _canonical_json(vote: AgentVote) -> str:
    """Serialize vote to canonical JSON for deterministic hashing.

    Uses sorted keys and compact separators to ensure identical serialization
    across different Python environments and runs.

    Args:
        vote: The agent vote to serialize

    Returns:
        Canonical JSON string with sorted keys and no whitespace

    """
    vote_dict = vote.model_dump(mode="json")
    return json.dumps(vote_dict, sort_keys=True, separators=(",", ":"))


def _compute_hash(canonical_json: str, nonce: str) -> str:
    """Compute SHA-256 hash of canonical vote JSON concatenated with nonce.

    Args:
        canonical_json: Canonical JSON representation of the vote
        nonce: Cryptographically secure random nonce

    Returns:
        Hex-encoded SHA-256 hash (64 characters)

    """
    combined = canonical_json + nonce
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _generate_nonce() -> str:
    """Generate cryptographically secure random nonce.

    Uses secrets module for CSPRNG. Returns 64 hex characters (32 bytes).

    Returns:
        Hex-encoded random nonce (64 characters)

    """
    return secrets.token_hex(32)


class ConsensusEscrow:
    """Commit-reveal voting protocol for tamper-resistant consensus.

    Implements cryptographic commit-reveal voting to prevent vote manipulation:
    1. Commit phase: Workers submit hash(vote || nonce) without revealing vote
    2. Reveal phase: Workers reveal vote + nonce, verified against commit hash
    3. Tally phase: Verified votes are tallied using standard consensus protocol

    Audit chain integration records commit and reveal timestamps for tamper detection.

    Example:
        >>> escrow = ConsensusEscrow()
        >>> vote = AgentVote(agent_id="worker-1", task_id="task-1", approved=True)
        >>> commit = escrow.commit(vote)
        >>> revealed = escrow.reveal(vote, commit.nonce, commit)
        >>> assert escrow.verify(revealed)

    """

    def __init__(self, audit_writer: HmacAuditChainWriter | None = None) -> None:
        """Initialize consensus escrow with optional audit chain integration.

        Args:
            audit_writer: Optional HMAC audit chain writer for recording
                         commit/reveal events. If None, no audit events are emitted.

        """
        self.audit_writer = audit_writer
        self._commits: dict[
            tuple[str, str, int], VoteCommit
        ] = {}  # (agent_id, task_id, round) -> commit

    def commit(self, vote: AgentVote, nonce: str | None = None) -> VoteCommit:
        """Commit to a vote without revealing it.

        Generates a cryptographic commitment hash(canonical_json(vote) || nonce)
        that binds the worker to their vote without revealing it. The nonce is
        returned in the VoteCommit for later reveal phase.

        Args:
            vote: The agent vote to commit to
            nonce: Optional nonce (generated if not provided). Must be kept secret
                   until reveal phase.

        Returns:
            VoteCommit containing the commit hash and metadata

        Side effects:
            - Stores commit in internal registry for verification
            - Emits audit event if audit_writer is configured

        """
        if nonce is None:
            nonce = _generate_nonce()

        canonical = _canonical_json(vote)
        commit_hash = _compute_hash(canonical, nonce)
        commit_timestamp = datetime.now(timezone.utc)

        commit = VoteCommit(
            agent_id=vote.agent_id,
            task_id=vote.task_id,
            round=vote.round,
            commit_hash=commit_hash,
            commit_timestamp=commit_timestamp,
        )

        # Store commit for later verification
        key = (vote.agent_id, vote.task_id, vote.round)
        self._commits[key] = commit

        # Emit audit event
        if self.audit_writer:
            self.audit_writer.append(
                {
                    "type": "consensus_commit",
                    "agent_id": vote.agent_id,
                    "task_id": vote.task_id,
                    "round": vote.round,
                    "commit_hash": commit_hash,
                    "timestamp": commit_timestamp.isoformat(),
                }
            )

        return commit

    def reveal(
        self,
        vote: AgentVote,
        nonce: str,
        commit: VoteCommit,
    ) -> CommitRevealVote:
        """Reveal a vote and verify it against prior commitment.

        Recomputes the commit hash from the revealed vote and nonce, then
        verifies it matches the original commitment. Raises exception if
        verification fails.

        Args:
            vote: The agent vote being revealed
            nonce: The nonce used during commit phase
            commit: The original vote commitment

        Returns:
            CommitRevealVote containing the verified vote and metadata

        Raises:
            VoteMismatchError: If vote metadata doesn't match commit
            VoteVerificationError: If recomputed hash doesn't match commit hash

        Side effects:
            - Emits audit event if audit_writer is configured

        """
        # Verify vote metadata matches commit
        if vote.agent_id != commit.agent_id:
            raise VoteMismatchError(
                f"Agent ID mismatch: vote={vote.agent_id}, commit={commit.agent_id}"
            )
        if vote.task_id != commit.task_id:
            raise VoteMismatchError(
                f"Task ID mismatch: vote={vote.task_id}, commit={commit.task_id}"
            )
        if vote.round != commit.round:
            raise VoteMismatchError(f"Round mismatch: vote={vote.round}, commit={commit.round}")

        # Recompute hash and verify
        canonical = _canonical_json(vote)
        recomputed_hash = _compute_hash(canonical, nonce)

        if recomputed_hash != commit.commit_hash:
            raise VoteVerificationError(
                f"Hash mismatch: recomputed={recomputed_hash}, commit={commit.commit_hash}"
            )

        reveal_timestamp = datetime.now(timezone.utc)

        revealed = CommitRevealVote(
            vote=vote,
            nonce=nonce,
            commit_hash=commit.commit_hash,
            commit_timestamp=commit.commit_timestamp,
            reveal_timestamp=reveal_timestamp,
        )

        # Emit audit event
        if self.audit_writer:
            self.audit_writer.append(
                {
                    "type": "consensus_reveal",
                    "agent_id": vote.agent_id,
                    "task_id": vote.task_id,
                    "round": vote.round,
                    "approved": vote.approved,
                    "commit_hash": commit.commit_hash,
                    "commit_timestamp": commit.commit_timestamp.isoformat(),
                    "reveal_timestamp": reveal_timestamp.isoformat(),
                }
            )

        return revealed

    def verify(self, revealed_vote: CommitRevealVote) -> bool:
        """Verify a revealed vote against its commitment.

        Recomputes the commit hash from the vote and nonce, then compares
        with the stored commit hash. Returns True if valid, False otherwise.

        Args:
            revealed_vote: The revealed vote to verify

        Returns:
            True if verification succeeds, False otherwise

        """
        try:
            canonical = _canonical_json(revealed_vote.vote)
            recomputed_hash = _compute_hash(canonical, revealed_vote.nonce)
            return recomputed_hash == revealed_vote.commit_hash
        except Exception:
            return False

    def tally(
        self,
        revealed_votes: list[CommitRevealVote],
        protocol: ConsensusProtocol = ConsensusProtocol.majority,
        quorum: int | None = None,
    ) -> ConsensusResult:
        """Tally verified revealed votes using standard consensus protocol.

        Extracts AgentVote from each CommitRevealVote and delegates to the
        standard consensus implementation. All votes must be verified before
        tallying (caller's responsibility).

        Args:
            revealed_votes: List of revealed votes to tally
            protocol: Consensus protocol to use (majority, quorum, etc.)
            quorum: Optional quorum size for quorum-based protocols

        Returns:
            ConsensusResult with tally outcome and details

        """
        # Extract votes from revealed votes
        votes = [rv.vote for rv in revealed_votes]

        # Delegate to standard consensus
        return run_consensus(votes, protocol=protocol, quorum=quorum)

    def get_commit(self, agent_id: str, task_id: str, round: int) -> VoteCommit | None:
        """Retrieve a stored commit by agent, task, and round.

        Args:
            agent_id: Agent identifier
            task_id: Task identifier
            round: Voting round number

        Returns:
            VoteCommit if found, None otherwise

        """
        key = (agent_id, task_id, round)
        return self._commits.get(key)

    def clear_commits(self) -> None:
        """Clear all stored commits.

        Used for cleanup after consensus round completes or for testing.
        """
        self._commits.clear()
