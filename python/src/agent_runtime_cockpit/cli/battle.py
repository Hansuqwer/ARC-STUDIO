"""Battle CLI commands (Phase 34/R26A).

ARC-native, offline-first SwarmGraph battle mode for CLI.
No provider-backed/live claims. Offline/fake mode only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ..battle import (
    BattleRun,
    BattleRunner,
    BattleStore,
    BattleTopology,
    ConsensusProtocol,
)
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, _out
from ._subapps import battle_app


def _emit_error(
    message: str, json_output: bool, code: ArcErrorCode = ArcErrorCode.INVALID_INPUT
) -> None:
    _out(err(code, message), json_output)
    raise typer.Exit(1)


def _battle_payload(battle: BattleRun) -> dict[str, object]:
    return {
        "id": battle.id,
        "prompt": battle.prompt,
        "workers": battle.workers,
        "topology": battle.topology.value,
        "consensus_protocol": battle.consensus_protocol.value,
        "runtime_mode": battle.runtime_mode,
        "status": battle.status.value,
        "created_at": battle.created_at.isoformat(),
        "started_at": battle.started_at.isoformat() if battle.started_at else None,
        "completed_at": battle.completed_at.isoformat() if battle.completed_at else None,
        "consensus_escrow": battle.consensus_escrow,
        "require_hitl": battle.require_hitl,
    }


@battle_app.command("run")
def battle_run(
    prompt: str = typer.Argument(..., help="Battle prompt for workers to solve"),
    workers: int = typer.Option(2, "--workers", "-w", help="Number of workers (2 or 4)"),
    topology: str = typer.Option("flat", "--topology", "-t", help="Battle topology (flat only)"),
    consensus: str = typer.Option(
        "majority", "--consensus", "-c", help="Consensus protocol (majority or quorum)"
    ),
    runtime_mode: str = typer.Option(
        "fake/offline", "--runtime-mode", "-r", help="Runtime mode (fake/offline only)"
    ),
    consensus_escrow: bool = typer.Option(
        False, "--consensus-escrow", help="Enable commit-reveal voting"
    ),
    require_hitl: bool = typer.Option(False, "--require-hitl", help="Require human judge"),
    models: Optional[str] = typer.Option(
        None, "--models", "-m", help="Comma-separated model IDs for workers"
    ),
    json_output: bool = JSON_FLAG,
) -> None:
    """Run a SwarmGraph battle with multiple workers.

    Each worker independently solves the prompt, then consensus voting
    determines the winner. Results are stored in the battle database.

    Example:
        arc battle run "Write a function to check if a number is prime" --workers 2
    """
    # Validate inputs
    if workers not in (2, 4):
        _emit_error("Only 2 or 4 workers are supported", json_output)

    if topology != "flat":
        _emit_error("Only flat topology is supported", json_output)

    if runtime_mode != "fake/offline":
        _emit_error("Only fake/offline runtime mode is supported", json_output)

    if consensus not in ("majority", "quorum"):
        _emit_error("Consensus must be 'majority' or 'quorum'", json_output)

    # Parse worker models
    worker_models = None
    if models:
        worker_models = [m.strip() for m in models.split(",")]
        if len(worker_models) != workers:
            _emit_error(f"Expected {workers} models, got {len(worker_models)}", json_output)

    # Create battle run
    battle = BattleRun(
        prompt=prompt,
        workers=workers,
        topology=BattleTopology.flat,
        consensus_protocol=ConsensusProtocol[consensus],
        runtime_mode=runtime_mode,
        consensus_escrow=consensus_escrow,
        require_hitl=require_hitl,
    )

    # Run battle
    store = BattleStore()
    runner = BattleRunner(store=store)

    if not json_output:
        typer.echo(f"Starting battle {battle.id}...")
        typer.echo(f"  Prompt: {prompt}")
        typer.echo(f"  Workers: {workers}")
        typer.echo(f"  Consensus: {consensus}")

    result = runner.run_battle(battle, worker_models=worker_models)

    if result["status"] == "completed":
        if json_output:
            _out(ok(result), json_output)
        else:
            typer.echo(f"\nBattle completed: {battle.id}")
            typer.echo(f"  Candidates: {len(result['candidates'])}")
            typer.echo(f"  Votes: {len(result['votes'])}")
            outcome = result["outcome"]
            if outcome["consensus_reached"]:
                typer.echo(f"  Winner: {outcome['winner_candidate_id']}")
            else:
                typer.echo("  No consensus reached")
    else:
        _emit_error(str(result.get("error", "Unknown error")), json_output, ArcErrorCode.RUN_FAILED)


@battle_app.command("show")
def battle_show(
    battle_id: str = typer.Argument(..., help="Battle ID to show"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Show details of a battle run.

    Example:
        arc battle show battle-abc123
    """
    store = BattleStore()
    battle = store.get_battle_run(battle_id)

    if not battle:
        _emit_error(f"Battle {battle_id} not found", json_output, ArcErrorCode.RUN_NOT_FOUND)

    candidates = store.get_candidates(battle_id)
    votes = store.get_votes(battle_id)
    outcome = store.get_outcome(battle_id)

    if json_output:
        data = {
            "battle": {
                **_battle_payload(battle),
            },
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
            }
            if outcome
            else None,
        }
        _out(ok(data), json_output)
    else:
        typer.echo(f"Battle: {battle.id}")
        typer.echo(f"  Status: {battle.status.value}")
        typer.echo(f"  Prompt: {battle.prompt}")
        typer.echo(f"  Workers: {battle.workers}")
        typer.echo(f"  Consensus: {battle.consensus_protocol.value}")
        typer.echo(f"  Created: {battle.created_at.isoformat()}")

        typer.echo(f"\nCandidates ({len(candidates)}):")
        for c in candidates:
            typer.echo(f"  {c.id} ({c.worker_id}, {c.model_id})")
            typer.echo(f"    Output: {c.output[:100]}...")

        typer.echo(f"\nVotes ({len(votes)}):")
        for v in votes:
            status = "approved" if v.approved else "rejected"
            typer.echo(f"  {status}: {v.voter} -> {v.candidate_id}")

        if outcome:
            typer.echo("\nOutcome:")
            if outcome.consensus_reached:
                typer.echo(f"  Winner: {outcome.winner_candidate_id}")
            else:
                typer.echo("  No consensus reached")


@battle_app.command("vote")
def battle_vote(
    battle_id: str = typer.Argument(..., help="Battle ID"),
    candidate_id: str = typer.Option(..., "--candidate", "-c", help="Candidate ID to vote for"),
    approved: bool = typer.Option(..., "--approve/--reject", help="Approve or reject"),
    reason: str = typer.Option("", "--reason", "-r", help="Vote reasoning"),
    voter: str = typer.Option("human-judge", "--voter", "-v", help="Voter identifier"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Vote on a battle candidate (HITL judge).

    Example:
        arc battle vote battle-abc123 --candidate candidate-xyz --approve --reason "Best solution"
    """
    from ..battle import BattleVote, VoterType

    store = BattleStore()
    battle = store.get_battle_run(battle_id)

    if not battle:
        _emit_error(f"Battle {battle_id} not found", json_output, ArcErrorCode.RUN_NOT_FOUND)

    if not any(candidate.id == candidate_id for candidate in store.get_candidates(battle_id)):
        _emit_error(
            f"Candidate {candidate_id} not found for battle {battle_id}",
            json_output,
            ArcErrorCode.RUN_NOT_FOUND,
        )

    # Create vote
    vote = BattleVote(
        battle_id=battle_id,
        candidate_id=candidate_id,
        voter=voter,
        voter_type=VoterType.human,
        approved=approved,
        reasoning=reason,
    )

    # Store vote
    store.insert_vote(vote)

    if json_output:
        _out(
            ok(
                {
                    "vote_id": vote.id,
                    "battle_id": battle_id,
                    "candidate_id": candidate_id,
                    "approved": approved,
                }
            ),
            json_output,
        )
    else:
        status = "Approved" if approved else "Rejected"
        typer.echo(f"{status} candidate {candidate_id}")
        typer.echo(f"Vote ID: {vote.id}")


@battle_app.command("leaderboard")
def battle_leaderboard(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of models to show"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Show ELO leaderboard for battle models.

    Example:
        arc battle leaderboard --limit 10
    """
    store = BattleStore()
    ratings = store.list_elo_ratings(limit=limit)

    if json_output:
        data = [
            {
                "model_id": r.model_id,
                "rating": r.rating,
                "games_played": r.games_played,
                "wins": r.wins,
                "losses": r.losses,
                "draws": r.draws,
            }
            for r in ratings
        ]
        _out(ok(data), json_output)
    else:
        typer.echo("ELO Leaderboard:")
        typer.echo(f"{'Rank':<6} {'Model':<30} {'Rating':<10} {'Games':<8} {'W-L-D':<12}")
        typer.echo("-" * 70)
        for i, r in enumerate(ratings, 1):
            wld = f"{r.wins}-{r.losses}-{r.draws}"
            typer.echo(f"{i:<6} {r.model_id:<30} {r.rating:<10.1f} {r.games_played:<8} {wld:<12}")


@battle_app.command("list")
def battle_list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of battles to show"),
    json_output: bool = JSON_FLAG,
) -> None:
    """List battle runs.

    Example:
        arc battle list --status completed --limit 10
    """
    store = BattleStore()
    battles = store.list_battle_runs(status=status, limit=limit)

    if json_output:
        data = [
            {
                "id": b.id,
                "prompt": b.prompt,
                "workers": b.workers,
                "status": b.status.value,
                "created_at": b.created_at.isoformat(),
            }
            for b in battles
        ]
        _out(ok(data), json_output)
    else:
        typer.echo(f"Battles ({len(battles)}):")
        for b in battles:
            typer.echo(f"  {b.id} [{b.status.value}]")
            typer.echo(f"    Prompt: {b.prompt[:60]}...")
            typer.echo(f"    Workers: {b.workers}, Created: {b.created_at.isoformat()}")


@battle_app.command("export")
def battle_export(
    battle_id: str = typer.Argument(..., help="Battle ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json only)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Export battle results.

    Example:
        arc battle export battle-abc123 --output battle.json
    """
    if format != "json":
        _emit_error("Only JSON format is supported", json_output)

    store = BattleStore()
    battle = store.get_battle_run(battle_id)

    if not battle:
        _emit_error(f"Battle {battle_id} not found", json_output, ArcErrorCode.RUN_NOT_FOUND)

    candidates = store.get_candidates(battle_id)
    votes = store.get_votes(battle_id)
    outcome = store.get_outcome(battle_id)

    data = {
        "battle": {
            **_battle_payload(battle),
        },
        "candidates": [
            {
                "id": c.id,
                "worker_id": c.worker_id,
                "model_id": c.model_id,
                "output": c.output,
                "created_at": c.created_at.isoformat(),
            }
            for c in candidates
        ],
        "votes": [
            {
                "id": v.id,
                "candidate_id": v.candidate_id,
                "voter": v.voter,
                "voter_type": v.voter_type.value,
                "approved": v.approved,
                "reasoning": v.reasoning,
                "created_at": v.created_at.isoformat(),
            }
            for v in votes
        ],
        "outcome": {
            "id": outcome.id,
            "consensus_reached": outcome.consensus_reached,
            "winner_candidate_id": outcome.winner_candidate_id,
            "consensus_result": outcome.consensus_result,
            "completed_at": outcome.completed_at.isoformat(),
        }
        if outcome
        else None,
    }

    json_str = json.dumps(data, indent=2)

    if output:
        Path(output).write_text(json_str)
        if json_output:
            _out(ok({"battle_id": battle_id, "output": output, "format": format}), json_output)
        else:
            typer.echo(f"Exported battle to {output}")
    else:
        if json_output:
            _out(ok(data), json_output)
        else:
            typer.echo(json_str)


config_app = typer.Typer(name="config", help="Battle configuration commands")
battle_app.add_typer(config_app)


@config_app.command("validate")
def battle_config_validate(
    path: Path = typer.Argument(..., help="Battle config file to validate"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Validate a battle config file without executing it."""
    if not path.exists():
        _emit_error(f"Battle config not found: {path}", json_output, ArcErrorCode.RUN_NOT_FOUND)
    if not path.is_file():
        _emit_error(f"Battle config is not a file: {path}", json_output)

    try:
        text = path.read_text()
        parsed = json.loads(text) if path.suffix.lower() == ".json" else {"raw": text}
    except Exception as exc:
        _emit_error(f"Invalid battle config: {exc}", json_output)

    payload = {
        "path": str(path),
        "valid": True,
        "format": "json" if path.suffix.lower() == ".json" else "text",
        "keys": sorted(parsed.keys()) if isinstance(parsed, dict) else [],
    }
    _out(ok(payload), json_output)
