"""Replay commands: replay capability analysis (Phase 28)."""

from __future__ import annotations

from pathlib import Path

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import replay_app


@replay_app.command()
def replay_analyze(
    run_id: str = typer.Argument(..., help="Run ID to analyze for replay capability"),
    graph_id: str = typer.Option(None, "--graph-id", "-g", help="Graph ID (optional)"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Analyze replay capability for a LangGraph run.

    Reports whether the run can be replayed, resumed from checkpoint,
    and what level of determinism is available.
    """
    _setup_logging(debug)

    from ..adapters.langgraph.replay_detector import analyze_run_replay_capability

    workspace = Path.cwd()

    try:
        # Analyze replay capability
        capability = analyze_run_replay_capability(run_id, workspace, graph_id)

        # Prepare payload
        payload = {
            "run_id": capability.run_id,
            "runtime": capability.runtime,
            "can_replay_trace": capability.can_replay_trace,
            "can_resume_checkpoint": capability.can_resume_checkpoint,
            "requires_thread_id": capability.requires_thread_id,
            "side_effects_wrapped": capability.side_effects_wrapped,
            "determinism_level": capability.determinism_level,
            "has_checkpointer": capability.has_checkpointer,
            "checkpointer_type": capability.checkpointer_type,
            "thread_id_detected": capability.thread_id_detected,
            "thread_id": capability.thread_id,
            "warnings": capability.warnings,
            "summary": capability.get_capability_summary(),
        }

        _out(ok(payload), json_output)

        if not json_output:
            from ._app import console

            # Print the full report
            console.print(capability.report)

            # Print summary with color
            summary = capability.get_capability_summary()
            if capability.is_resumable():
                if capability.is_safe_to_replay():
                    console.print(f"\n[green]✓ {summary}[/green]")
                else:
                    console.print(f"\n[yellow]⚠ {summary}[/yellow]")
            else:
                console.print(f"\n[blue]ℹ {summary}[/blue]")

    except Exception as e:
        _out(
            err(ArcErrorCode.RUNTIME_ERROR, f"Failed to analyze replay capability: {e}"),
            json_output,
        )
        raise typer.Exit(1)
