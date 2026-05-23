"""Offline battle runner for ARC Battle Mode (Phase 34/R26A).

Orchestrates battles between multiple workers in fake/offline mode.
No provider-backed/live claims. Offline/fake mode only.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..protocol.events import create_event
from ..protocol.schemas import RunRecord, RunStatus
from ..storage.indexed_store import IndexedTraceStore
from ..swarmgraph.config import ExecutionMode
from ..swarmgraph.consensus import majority_consensus, quorum_consensus
from ..swarmgraph.models import AgentVote
from ..swarmgraph.nodes.worker import worker_execute
from .models import (
    BattleCandidate,
    BattleOutcome,
    BattleRun,
    BattleStatus,
    BattleVote,
    EloRating,
    VoterType,
)
from .store import BattleStore

log = logging.getLogger(__name__)


class BattleRunner:
    """Offline battle runner for SwarmGraph battles.

    Orchestrates battles between multiple workers in fake/offline mode.
    Each worker produces a candidate solution, then consensus voting
    determines the winner.
    """

    def __init__(
        self,
        store: BattleStore | None = None,
        workspace: Path | None = None,
    ):
        self.store = store or BattleStore()
        self.workspace = workspace or Path.cwd()
        self.events: list[dict[str, Any]] = []

    def run_battle(
        self,
        battle: BattleRun,
        *,
        worker_models: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a battle with the given configuration.

        Args:
            battle: Battle run configuration
            worker_models: Optional list of model IDs for workers (for ELO tracking)

        Returns:
            Result dict with status, candidates, votes, outcome
        """
        self.events = []

        # Validate battle configuration
        if battle.runtime_mode != "fake/offline":
            return self._error_result(battle, "Only fake/offline runtime mode is supported")

        if battle.workers not in (2, 4):
            return self._error_result(battle, "Only 2 or 4 workers are supported for baseline")

        if battle.topology.value != "flat":
            return self._error_result(battle, "Only flat topology is supported for baseline")

        # Default worker models if not provided
        if not worker_models:
            worker_models = [f"fake-worker-{i}" for i in range(battle.workers)]

        if len(worker_models) != battle.workers:
            return self._error_result(
                battle, f"Expected {battle.workers} worker models, got {len(worker_models)}"
            )

        try:
            # Update battle status to running
            battle.status = BattleStatus.running
            battle.started_at = datetime.now(timezone.utc)
            self.store.insert_battle_run(battle)
            self._emit_event(
                "BATTLE_STARTED",
                {
                    "battle_id": battle.id,
                    "prompt": battle.prompt,
                    "workers": battle.workers,
                    "topology": battle.topology.value,
                    "consensus_protocol": battle.consensus_protocol.value,
                    "runtime_mode": battle.runtime_mode,
                    "consensus_escrow": battle.consensus_escrow,
                    "require_hitl": battle.require_hitl,
                },
            )

            # Execute workers and collect candidates
            candidates = self._execute_workers(battle, worker_models)

            # Store candidates
            for candidate in candidates:
                self.store.insert_candidate(candidate)
                self._emit_event(
                    "BATTLE_CANDIDATE_READY",
                    {
                        "battle_id": battle.id,
                        "candidate_id": candidate.id,
                        "worker_id": candidate.worker_id,
                        "model_id": candidate.model_id,
                    },
                )

            # Run consensus voting (automatic for fake/offline mode)
            votes = self._run_consensus_voting(battle, candidates)

            # Store votes
            for vote in votes:
                self.store.insert_vote(vote)
                if battle.consensus_escrow and vote.commit_hash:
                    self._emit_event(
                        "BATTLE_VOTE_COMMITTED",
                        {
                            "battle_id": battle.id,
                            "vote_id": vote.id,
                            "commit_hash": vote.commit_hash,
                        },
                    )
                if battle.consensus_escrow and vote.reveal_nonce:
                    self._emit_event(
                        "BATTLE_VOTE_REVEALED",
                        {
                            "battle_id": battle.id,
                            "vote_id": vote.id,
                            "candidate_id": vote.candidate_id,
                            "approved": vote.approved,
                        },
                    )

            # Determine outcome
            outcome = self._determine_outcome(battle, candidates, votes)

            # Store outcome
            self.store.insert_outcome(outcome)
            self._emit_event(
                "BATTLE_CONSENSUS_REACHED",
                {
                    "battle_id": battle.id,
                    "consensus_reached": outcome.consensus_reached,
                    "winner_candidate_id": outcome.winner_candidate_id,
                    "consensus_result": outcome.consensus_result,
                },
            )

            # Update ELO ratings if consensus reached
            if outcome.consensus_reached and outcome.winner_candidate_id:
                self._update_elo_ratings(candidates, outcome.winner_candidate_id)

            # Update battle status to completed
            battle.status = BattleStatus.completed
            battle.completed_at = datetime.now(timezone.utc)
            self.store.update_battle_status(
                battle.id,
                BattleStatus.completed.value,
                started_at=battle.started_at.isoformat(),
                completed_at=battle.completed_at.isoformat(),
            )
            self._emit_event(
                "BATTLE_COMPLETED",
                {
                    "battle_id": battle.id,
                    "status": battle.status.value,
                    "winner_candidate_id": outcome.winner_candidate_id,
                },
            )

            # Persist battle run as ARC run record (Phase 34.1)
            run_id, trace_path = self.persist_battle_run_trace(
                battle, outcome, workspace=self.workspace
            )

            return {
                "status": "completed",
                "battle_id": battle.id,
                "run_id": run_id,
                "trace_path": str(trace_path),
                "candidates": [
                    {
                        "id": c.id,
                        "worker_id": c.worker_id,
                        "model_id": c.model_id,
                        "output": c.output,
                    }
                    for c in candidates
                ],
                "votes": [
                    {
                        "id": v.id,
                        "candidate_id": v.candidate_id,
                        "voter": v.voter,
                        "approved": v.approved,
                    }
                    for v in votes
                ],
                "outcome": {
                    "consensus_reached": outcome.consensus_reached,
                    "winner_candidate_id": outcome.winner_candidate_id,
                    "consensus_result": outcome.consensus_result,
                },
                "events": self.events,
            }

        except Exception as e:
            log.error("Battle execution failed: %s", e, exc_info=True)
            battle.status = BattleStatus.failed
            battle.error_detail = str(e)
            battle.completed_at = datetime.now(timezone.utc)
            self.store.update_battle_status(
                battle.id,
                BattleStatus.failed.value,
                completed_at=battle.completed_at.isoformat(),
                error_detail=battle.error_detail,
            )
            return self._error_result(battle, str(e))

    def _execute_workers(
        self, battle: BattleRun, worker_models: list[str]
    ) -> list[BattleCandidate]:
        """Execute workers and collect candidate outputs.

        Each worker independently processes the prompt and produces a candidate.
        """
        candidates: list[BattleCandidate] = []

        for i, model_id in enumerate(worker_models):
            worker_id = f"worker-{i}"

            # Create a simple task for the worker
            from ..swarmgraph.models import SwarmTask, TaskStatus

            task = SwarmTask(
                id=f"task-{battle.id}-{worker_id}",
                prompt=battle.prompt,
                status=TaskStatus.assigned,
                assigned_agent_id=worker_id,
            )

            # Execute worker in fake/offline mode
            result = worker_execute(
                task,
                mode=ExecutionMode.fake_offline,
                timeout=30.0,
            )

            # Create candidate from worker output
            output = result.output if result.output else f"Fake output from {worker_id}"
            candidate = BattleCandidate(
                battle_id=battle.id,
                worker_id=worker_id,
                model_id=model_id,
                output=output,
                metadata={
                    "task_id": task.id,
                    "cost_usd": result.cost_usd,
                    "error": result.error,
                },
            )
            candidates.append(candidate)

        return candidates

    def _run_consensus_voting(
        self, battle: BattleRun, candidates: list[BattleCandidate]
    ) -> list[BattleVote]:
        """Run consensus voting on candidates.

        In fake/offline mode, we simulate voting with a deterministic pattern
        to ensure consistent test results. The first candidate always wins.
        """
        votes: list[BattleVote] = []

        # Each worker votes on all candidates (including their own)
        for i, voter_candidate in enumerate(candidates):
            for j, target_candidate in enumerate(candidates):
                # Deterministic voting: approve the first candidate, reject others
                # This ensures consistent test results
                approved = j == 0

                vote = BattleVote(
                    battle_id=battle.id,
                    candidate_id=target_candidate.id,
                    voter=voter_candidate.worker_id,
                    voter_type=VoterType.model,
                    approved=approved,
                    reasoning=f"Deterministic vote from {voter_candidate.worker_id}",
                )

                # If consensus escrow is enabled, add commit-reveal fields
                if battle.consensus_escrow:
                    import hashlib
                    import secrets

                    nonce = secrets.token_hex(16)
                    vote_data = f"{vote.candidate_id}:{vote.approved}:{nonce}"
                    commit_hash = hashlib.sha256(vote_data.encode()).hexdigest()

                    # Create new vote with commit-reveal fields
                    vote = BattleVote(
                        battle_id=vote.battle_id,
                        candidate_id=vote.candidate_id,
                        voter=vote.voter,
                        voter_type=vote.voter_type,
                        approved=vote.approved,
                        reasoning=vote.reasoning,
                        commit_hash=commit_hash,
                        reveal_nonce=nonce,
                    )

                votes.append(vote)

        return votes

    def _determine_outcome(
        self,
        battle: BattleRun,
        candidates: list[BattleCandidate],
        votes: list[BattleVote],
    ) -> BattleOutcome:
        """Determine battle outcome based on consensus voting.

        Uses the configured consensus protocol (majority or quorum).
        """
        # Count votes for each candidate
        candidate_votes: dict[str, list[BattleVote]] = {c.id: [] for c in candidates}
        for vote in votes:
            if vote.candidate_id in candidate_votes:
                candidate_votes[vote.candidate_id].append(vote)

        # Convert to AgentVote format for consensus functions
        candidate_consensus: dict[str, Any] = {}
        for candidate_id, cand_votes in candidate_votes.items():
            agent_votes = [
                AgentVote(
                    agent_id=v.voter,
                    task_id=candidate_id,
                    approved=v.approved,
                    reasoning=v.reasoning,
                )
                for v in cand_votes
            ]

            # Run consensus protocol
            if battle.consensus_protocol.value == "majority":
                result = majority_consensus(agent_votes)
            elif battle.consensus_protocol.value == "quorum":
                quorum = battle.workers // 2 + 1
                result = quorum_consensus(agent_votes, quorum=quorum)
            else:
                # Default to majority
                result = majority_consensus(agent_votes)

            candidate_consensus[candidate_id] = {
                "reached": result.reached,
                "approved": result.approved,
                "total_votes": result.total_votes,
                "approval_count": result.approval_count,
                "rejection_count": result.rejection_count,
            }

        # Find winner (candidate with most approvals)
        winner_id = None
        max_approvals = -1
        consensus_reached = False

        for candidate_id, consensus in candidate_consensus.items():
            if consensus["reached"] and consensus["approved"]:
                consensus_reached = True
                if consensus["approval_count"] > max_approvals:
                    max_approvals = consensus["approval_count"]
                    winner_id = candidate_id

        return BattleOutcome(
            battle_id=battle.id,
            winner_candidate_id=winner_id,
            consensus_reached=consensus_reached,
            consensus_result={
                "protocol": battle.consensus_protocol.value,
                "candidates": candidate_consensus,
                "winner_approvals": max_approvals if winner_id else 0,
            },
        )

    def _update_elo_ratings(self, candidates: list[BattleCandidate], winner_id: str) -> None:
        """Update ELO ratings for all participating models.

        Treats the battle as a single game where the winner beats all losers.
        The winner gets +1 game and +1 win total.
        Each loser gets +1 game and +1 loss.
        """
        # Get current ratings for all models
        model_ratings: dict[str, EloRating] = {}
        for candidate in candidates:
            rating = self.store.get_elo_rating(candidate.model_id)
            if not rating:
                rating = EloRating(model_id=candidate.model_id)
            model_ratings[candidate.model_id] = rating

        # Find winner and losers
        winner_model = None
        loser_models = []
        for candidate in candidates:
            if candidate.id == winner_id:
                winner_model = candidate.model_id
            else:
                loser_models.append(candidate.model_id)

        if not winner_model:
            return

        # Get winner's current rating
        winner_rating = model_ratings[winner_model]

        # Calculate average rating of losers for ELO calculation
        loser_ratings = [model_ratings[m].rating for m in loser_models]
        avg_loser_rating = (
            sum(loser_ratings) / len(loser_ratings) if loser_ratings else winner_rating.rating
        )

        # Calculate new winner rating based on average loser rating
        from .models import calculate_elo_change

        new_winner_rating, _ = calculate_elo_change(winner_rating.rating, avg_loser_rating)

        # Update winner (only once for the entire battle)
        updated_winner = EloRating(
            model_id=winner_rating.model_id,
            rating=new_winner_rating,
            games_played=winner_rating.games_played + 1,
            wins=winner_rating.wins + 1,
            losses=winner_rating.losses,
            draws=winner_rating.draws,
            last_updated=datetime.now(timezone.utc),
        )
        self.store.upsert_elo_rating(updated_winner)

        # Update each loser
        for loser_model in loser_models:
            loser_rating = model_ratings[loser_model]

            # Calculate new loser rating against winner
            _, new_loser_rating = calculate_elo_change(winner_rating.rating, loser_rating.rating)

            updated_loser = EloRating(
                model_id=loser_rating.model_id,
                rating=new_loser_rating,
                games_played=loser_rating.games_played + 1,
                wins=loser_rating.wins,
                losses=loser_rating.losses + 1,
                draws=loser_rating.draws,
                last_updated=datetime.now(timezone.utc),
            )
            self.store.upsert_elo_rating(updated_loser)

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit a battle event."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self.events.append(event)
        log.debug("Battle event: %s", event)

    def _error_result(self, battle: BattleRun, error: str) -> dict[str, Any]:
        """Return an error result."""
        return {
            "status": "failed",
            "battle_id": battle.id,
            "error": error,
            "events": self.events,
        }

    def get_events(self) -> list[dict[str, Any]]:
        """Get all emitted events."""
        return self.events

    def persist_battle_run_trace(
        self,
        battle: BattleRun,
        outcome: BattleOutcome | None = None,
        *,
        workspace: Path = Path.cwd(),
    ) -> tuple[str, Path]:
        """Persist battle run as ARC run record with JSONL trace.

        Creates a RunRecord from battle events and stores it using IndexedTraceStore
        (dual-writes JSONL + SQLite index). This makes battle runs compatible with
        existing ARC run/trace surfaces (arc runs get, arc runs trace, etc.).

        Args:
            battle: Battle run to persist
            outcome: Battle outcome (if available)
            workspace: Workspace root path

        Returns:
            Tuple of (run_id, trace_path)
        """
        # Generate new run_id (separate from battle_id)
        run_id = f"run-{uuid.uuid4().hex[:8]}"

        # Convert battle events to RunEvent objects
        run_events = []
        for seq, event in enumerate(self.events):
            # Add RUN_STARTED as first event
            if seq == 0:
                run_events.append(
                    create_event(
                        run_id,
                        0,
                        "RUN_STARTED",
                        {
                            "workflow_id": f"battle:{battle.id}",
                            "runtime": "swarmgraph-battle",
                        },
                    )
                )

            # Convert battle event to RunEvent
            run_events.append(
                create_event(
                    run_id,
                    len(run_events),
                    event["type"],
                    event["data"],
                )
            )

        # Add RUN_COMPLETED as final event
        if battle.status == BattleStatus.completed:
            duration_ms = None
            if battle.started_at and battle.completed_at:
                duration_ms = int((battle.completed_at - battle.started_at).total_seconds() * 1000)
            run_events.append(
                create_event(
                    run_id,
                    len(run_events),
                    "RUN_COMPLETED",
                    {"duration_ms": duration_ms or 0},
                )
            )
        elif battle.status == BattleStatus.failed:
            run_events.append(
                create_event(
                    run_id,
                    len(run_events),
                    "RUN_FAILED",
                    {"error": battle.error_detail or "Battle failed"},
                )
            )

        # Map battle status to RunStatus
        status_map = {
            BattleStatus.pending: RunStatus.PENDING,
            BattleStatus.running: RunStatus.RUNNING,
            BattleStatus.completed: RunStatus.COMPLETED,
            BattleStatus.failed: RunStatus.FAILED,
        }
        run_status = status_map.get(battle.status, RunStatus.PENDING)

        # Create RunRecord with battle metadata
        run_record = RunRecord(
            id=run_id,
            workflow_id=f"battle:{battle.id}",
            runtime="swarmgraph-battle",
            status=run_status,
            started_at=battle.started_at.isoformat()
            if battle.started_at
            else datetime.now(timezone.utc).isoformat(),
            ended_at=battle.completed_at.isoformat() if battle.completed_at else None,
            events=run_events,
            metadata={
                "kind": "battle",
                "battle_id": battle.id,
                "workers": battle.workers,
                "topology": battle.topology.value,
                "consensus_protocol": battle.consensus_protocol.value,
                "runtime_mode": battle.runtime_mode,
                "battle_db_path": str(self.store.db_path),
                "outcome_id": outcome.id if outcome else None,
                "winner_candidate_id": outcome.winner_candidate_id if outcome else None,
                "consensus_reached": outcome.consensus_reached if outcome else False,
            },
        )

        # Use IndexedTraceStore to save (dual-writes JSONL + SQLite)
        trace_dir = workspace / ".arc" / "traces"
        db_path = workspace / ".arc" / "arc.db"
        store = IndexedTraceStore(trace_dir=trace_dir, db_path=db_path)
        store.init()
        store.save(run_record)

        trace_path = store.trace_path(run_id)
        log.info("Persisted battle run as ARC run: %s -> %s", run_id, trace_path)

        return run_id, trace_path
