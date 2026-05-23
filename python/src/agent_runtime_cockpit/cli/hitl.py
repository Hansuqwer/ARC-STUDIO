"""HITL commands: pending prompts and responses (Phase 29)."""

from __future__ import annotations

from pathlib import Path

import typer

from ..audit.hitl import HitlDecision
from ..audit.hitl_sqlite_store import HitlSqliteStore
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import hitl_app


@hitl_app.command("pending")
def hitl_pending(
    include_expired: bool = typer.Option(
        False, "--include-expired", help="Include expired prompts"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List pending HITL prompts."""
    _setup_logging(debug)

    workspace = Path.cwd()
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")

    try:
        prompts = store.list_prompts(include_expired=include_expired)

        payload = {
            "count": len(prompts),
            "prompts": [
                {
                    "hitl_id": p.hitl_id,
                    "run_id": p.run_id,
                    "step_id": p.step_id,
                    "prompt_text": p.prompt_text,
                    "context": p.context,
                    "options": p.options,
                    "timeout_seconds": p.timeout_seconds,
                    "created_at": p.created_at,
                }
                for p in prompts
            ],
        }

        _out(ok(payload), json_output)

        if not json_output:
            from ._app import console

            if len(prompts) == 0:
                console.print("[yellow]No pending HITL prompts[/yellow]")
            else:
                console.print(f"Pending HITL prompts: {len(prompts)}")
                for p in prompts:
                    console.print(f"\n[bold]{p.hitl_id}[/bold]")
                    console.print(f"  Run: {p.run_id}")
                    console.print(f"  Step: {p.step_id}")
                    console.print(f"  Prompt: {p.prompt_text}")
                    console.print(f"  Options: {', '.join(p.options)}")
                    console.print(f"  Created: {p.created_at}")

    except Exception as e:
        _out(
            err(ArcErrorCode.RUNTIME_ERROR, f"Failed to list HITL prompts: {e}"),
            json_output,
        )
        raise typer.Exit(1)


@hitl_app.command("respond")
def hitl_respond(
    hitl_id: str = typer.Argument(..., help="HITL prompt ID to respond to"),
    decision: str = typer.Option(
        ..., "--decision", "-d", help="Decision: approve, reject, modify, skip"
    ),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for the decision"),
    operator_id: str = typer.Option("cli-user", "--operator", "-o", help="Operator ID"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Respond to a HITL prompt.

    Requires the prompt token which can be obtained from the prompt details.
    For security, the token should be provided via environment variable HITL_TOKEN.
    """
    _setup_logging(debug)

    import os

    workspace = Path.cwd()
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")

    # Validate decision
    try:
        decision_enum = HitlDecision(decision.lower())
    except ValueError:
        valid_decisions = [d.value for d in HitlDecision]
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid decision: {decision}. Must be one of: {', '.join(valid_decisions)}",
            ),
            json_output,
        )
        raise typer.Exit(1)

    # Get token from environment or prompt
    token = os.environ.get("HITL_TOKEN")
    if not token:
        # Get token from store for convenience (in production, this should be more secure)
        token = store.get_token(hitl_id)
        if not token:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"HITL prompt not found or expired: {hitl_id}. Set HITL_TOKEN environment variable.",
                ),
                json_output,
            )
            raise typer.Exit(1)

    try:
        # Respond to prompt
        response = store.respond(
            hitl_id=hitl_id,
            decision=decision_enum,
            token=token,
            operator_id=operator_id,
            notes=reason,
            audit_hash=None,  # TODO: Link to audit chain
        )

        if not response:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Failed to respond to HITL prompt: {hitl_id}. Prompt may be expired, already responded, or token invalid.",
                ),
                json_output,
            )
            raise typer.Exit(1)

        payload = {
            "hitl_id": response.hitl_id,
            "run_id": response.run_id,
            "decision": response.decision.value,
            "operator_id": response.operator_id,
            "notes": response.notes,
            "responded_at": response.responded_at,
        }

        _out(ok(payload), json_output)

        if not json_output:
            from ._app import console

            console.print(f"[green]✓ Response recorded for HITL prompt: {hitl_id}[/green]")
            console.print(f"  Decision: {response.decision.value}")
            console.print(f"  Operator: {response.operator_id}")
            if reason:
                console.print(f"  Reason: {reason}")

    except Exception as e:
        _out(
            err(ArcErrorCode.RUNTIME_ERROR, f"Failed to respond to HITL prompt: {e}"),
            json_output,
        )
        raise typer.Exit(1)


@hitl_app.command("show")
def hitl_show(
    hitl_id: str = typer.Argument(..., help="HITL prompt ID to show"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show details of a specific HITL prompt."""
    _setup_logging(debug)

    workspace = Path.cwd()
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")

    try:
        prompt = store.get_prompt(hitl_id)

        if not prompt:
            _out(
                err(ArcErrorCode.RUN_NOT_FOUND, f"HITL prompt not found: {hitl_id}"),
                json_output,
            )
            raise typer.Exit(1)

        # Check if there's a response
        response = store.get_response(hitl_id)

        payload = {
            "hitl_id": prompt.hitl_id,
            "run_id": prompt.run_id,
            "step_id": prompt.step_id,
            "prompt_text": prompt.prompt_text,
            "context": prompt.context,
            "options": prompt.options,
            "timeout_seconds": prompt.timeout_seconds,
            "created_at": prompt.created_at,
            "response": {
                "decision": response.decision.value,
                "operator_id": response.operator_id,
                "notes": response.notes,
                "responded_at": response.responded_at,
            }
            if response
            else None,
        }

        _out(ok(payload), json_output)

        if not json_output:
            from ._app import console

            console.print(f"[bold]HITL Prompt: {prompt.hitl_id}[/bold]")
            console.print(f"  Run: {prompt.run_id}")
            console.print(f"  Step: {prompt.step_id}")
            console.print(f"  Prompt: {prompt.prompt_text}")
            console.print(f"  Options: {', '.join(prompt.options)}")
            console.print(f"  Timeout: {prompt.timeout_seconds}s")
            console.print(f"  Created: {prompt.created_at}")

            if response:
                console.print("\n[bold]Response:[/bold]")
                console.print(f"  Decision: [green]{response.decision.value}[/green]")
                console.print(f"  Operator: {response.operator_id}")
                console.print(f"  Responded: {response.responded_at}")
                if response.notes:
                    console.print(f"  Notes: {response.notes}")
            else:
                console.print("\n[yellow]No response yet[/yellow]")

    except Exception as e:
        _out(
            err(ArcErrorCode.RUNTIME_ERROR, f"Failed to show HITL prompt: {e}"),
            json_output,
        )
        raise typer.Exit(1)


@hitl_app.command("prune")
def hitl_prune(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune expired HITL prompts."""
    _setup_logging(debug)

    workspace = Path.cwd()
    store = HitlSqliteStore(workspace / ".arc" / "hitl.db")

    try:
        pruned = store.prune_expired()

        payload = {"pruned_count": pruned}
        _out(ok(payload), json_output)

        if not json_output:
            from ._app import console

            if pruned > 0:
                console.print(f"[green]Pruned {pruned} expired HITL prompts[/green]")
            else:
                console.print("[yellow]No expired prompts to prune[/yellow]")

    except Exception as e:
        _out(
            err(ArcErrorCode.RUNTIME_ERROR, f"Failed to prune HITL prompts: {e}"),
            json_output,
        )
        raise typer.Exit(1)
