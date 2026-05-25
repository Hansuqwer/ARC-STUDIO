"""LM Arena CLI commands — list models, chat, vote, rankings."""

from __future__ import annotations

from typing import Optional

import typer

from ..arena.models import ArenaMode, ArenaRequest, ArenaVote, PrivacyLevel
from ..arena.service import (
    arena_request,
    get_vote_rankings,
    list_models,
    list_tags,
    store_arena_run,
)
from ..gating import GatingError
from ..protocol.event_envelope import err, ok
from ..security.profiles import enforce_profile, resolve_profile
from ..storage.jsonl import JsonlTraceStore
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import arena_app


@arena_app.command("list")
def arena_list(
    tags: Optional[str] = typer.Option(
        None, "--tags", help="Comma-separated tags to filter models (e.g., 'fast,code')"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available Arena models."""
    _setup_logging(debug)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    models = list_models(tag_list)
    _out(ok([m.model_dump() for m in models]), json_output)


@arena_app.command("tags")
def arena_tags_cmd(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available model tags with descriptions."""
    _setup_logging(debug)
    _out(ok(list_tags()), json_output)


@arena_app.command("chat")
def arena_chat_cmd(
    prompt: str = typer.Argument(..., help="The prompt to send to Arena"),
    mode: ArenaMode = typer.Option(
        ArenaMode.DIRECT, "--mode", "-m", help="Arena mode (battle/direct/code/agent-arena-preview)"
    ),
    model: str = typer.Option(
        "gpt-4o-mini-2024-07-18", "--model", help="Model ID for direct/code modes"
    ),
    tags: Optional[str] = typer.Option(
        None, "--tags", help="Comma-separated tags for battle mode model selection"
    ),
    privacy: PrivacyLevel = typer.Option(
        PrivacyLevel.PRIVATE, "--privacy", help="Privacy level (Private/Debug/Research)"
    ),
    allow_paid: bool = typer.Option(
        False, "--allow-paid", help="Allow paid API calls (requires ARC_ALLOW_LIVE_ARENA=true)"
    ),
    profile_id: str = typer.Option("local-safe", "--profile", help="Run profile ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Send a prompt to LM Arena and receive model responses."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        profile = resolve_profile(profile_id)
        if allow_paid and not profile.allow_paid_calls:
            raise GatingError(f"Profile '{profile.id}' does not allow paid calls.")
        enforce_profile(profile, "lmarena")
    except GatingError as exc:
        _out(err("profile_enforcement_failed", str(exc)), json_output)
        raise typer.Exit(1)

    req = ArenaRequest(
        mode=mode,
        prompt=prompt,
        workspace=str(ws),
        model=model,
        model_tags=tag_list,
        privacy=privacy,
        allow_paid_calls=allow_paid,
        profile_id=profile_id,
    )

    response = arena_request(ws, req)
    store_arena_run(JsonlTraceStore(ws / ".arc" / "traces"), response, req)
    _out(ok(response.model_dump()), json_output)


@arena_app.command("vote")
def arena_vote_cmd(
    run_id: str = typer.Argument(..., help="Run ID to vote on"),
    winner: str = typer.Argument(..., help="Winner candidate ID"),
    loser: Optional[str] = typer.Argument(None, help="Loser candidate ID (optional)"),
    voter: str = typer.Option("", "--voter", help="Voter identifier"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Record a vote for a battle candidate."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")

    vote = ArenaVote(
        run_id=run_id,
        winner_candidate_id=winner,
        loser_candidate_id=loser or "",
        voter=voter,
    )

    run = store.load(run_id)
    if run is None:
        _out(err("run_not_found", f"Run {run_id} not found"), json_output)
        raise typer.Exit(1)

    from datetime import datetime, timezone

    from ..protocol.schemas import RunEvent

    events = list(run.events)
    events.append(
        RunEvent(
            type="LMARENA_VOTE_RECORDED",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            run_id=run_id,
            sequence=len(events),
            data={
                "winner_candidate_id": vote.winner_candidate_id,
                "loser_candidate_id": vote.loser_candidate_id,
                "voter": vote.voter,
            },
        )
    )
    run.events = events
    run.metadata["vote"] = vote.winner_candidate_id
    store.save(run)

    _out(ok({"recorded": True, "run_id": run_id}), json_output)


@arena_app.command("rankings")
def arena_rankings_cmd(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Retrieve vote history and model rankings."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rankings = get_vote_rankings(store)
    _out(ok(rankings), json_output)
