"""CLI commands for ARC Time Travel — run replay & diff debugger (R101).

Commands:
  arc time-travel record    Start recording a time travel session.
  arc time-travel replay    Replay a time travel session forward/backward.
  arc time-travel branch    Create a branch from a specific step.
  arc time-travel compare   Compare two execution paths.
  arc time-travel show      Show time travel session details.

All commands accept --json for machine-readable envelope output.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import time_travel_app


@time_travel_app.command("record")
def time_travel_record(
    run_id: str = typer.Argument(..., help="Run ID to record"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output .arctt file path"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Start recording a time travel session for a run."""
    from ..time_travel import create_session

    ws = _workspace(workspace)
    session_id = str(uuid.uuid4())
    session = create_session(session_id=session_id, run_id=run_id)

    if output:
        output_path = Path(output)
        session.save(output_path)
    else:
        output_path = ws / ".arc" / "time_travel" / f"{session_id}.arctt"
        session.save(output_path)

    _out(
        ok(
            {
                "session_id": session_id,
                "run_id": run_id,
                "output": str(output_path),
                "steps": 0,
                "message": f"Time travel session created: {output_path}",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Time Travel Session Created[/bold]")
        console.print(f"  Session ID: {session_id}")
        console.print(f"  Run ID: {run_id}")
        console.print(f"  Output: {output_path}")


@time_travel_app.command("replay")
def time_travel_replay(
    session_file: str = typer.Argument(..., help="Path to .arctt file"),
    direction: str = typer.Option(
        "forward", "--direction", "-d", help="Replay direction: forward or backward"
    ),
    steps: int = typer.Option(1, "--steps", "-s", help="Number of steps to replay"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Replay a time travel session forward or backward."""
    from ..time_travel import load_session

    _workspace(workspace)
    session_path = Path(session_file)
    if not session_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Session file not found: {session_file}"), as_json)
        raise typer.Exit(1)

    session = load_session(session_path)
    start_index = session.current_step_index

    if direction == "forward":
        for _ in range(steps):
            session.step_forward()
    elif direction == "backward":
        for _ in range(steps):
            session.step_backward()
    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid direction: {direction}. Use: forward, backward",
            ),
            as_json,
        )
        raise typer.Exit(1)

    current = session.get_current_step()
    _out(
        ok(
            {
                "session_id": session.session_id,
                "direction": direction,
                "steps_moved": steps,
                "start_index": start_index,
                "current_index": session.current_step_index,
                "current_step": current.to_dict() if current else None,
                "total_steps": len(session.steps),
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Time Travel Replay[/bold]")
        console.print(f"  Session: {session.session_id}")
        console.print(f"  Direction: {direction}")
        console.print(f"  Steps moved: {steps}")
        console.print(f"  Current step: {session.current_step_index + 1} / {len(session.steps)}")
        if current:
            console.print(f"  Step type: {current.step_type.value}")
            console.print(f"  Timestamp: {current.timestamp}")


@time_travel_app.command("branch")
def time_travel_branch(
    session_file: str = typer.Argument(..., help="Path to .arctt file"),
    step_index: int = typer.Option(..., "--step", "-s", help="Step index to branch from"),
    branch_id: Optional[str] = typer.Option(
        None, "--branch-id", "-b", help="Branch ID (auto-generated if not provided)"
    ),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Create a branch from a specific step in a time travel session."""
    from ..time_travel import load_session, save_session

    _workspace(workspace)
    session_path = Path(session_file)
    if not session_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Session file not found: {session_file}"), as_json)
        raise typer.Exit(1)

    session = load_session(session_path)
    bid = branch_id or str(uuid.uuid4())
    branch = session.branch_from_step(step_index, bid)

    if branch is None:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid step index: {step_index}"), as_json)
        raise typer.Exit(1)

    save_session(session, session_path)

    _out(
        ok(
            {
                "session_id": session.session_id,
                "branch_id": bid,
                "parent_step_id": branch.parent_step_id,
                "branch_steps": len(branch.steps),
                "total_branches": len(session.branches),
                "message": f"Branch created: {bid}",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Branch Created[/bold]")
        console.print(f"  Branch ID: {bid}")
        console.print(f"  Parent step: {branch.parent_step_id}")
        console.print(f"  Branch steps: {len(branch.steps)}")


@time_travel_app.command("compare")
def time_travel_compare(
    session1_file: str = typer.Argument(..., help="Path to first .arctt file"),
    session2_file: str = typer.Argument(..., help="Path to second .arctt file"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Compare two execution paths."""
    from ..time_travel import compare_paths, load_session

    _workspace(workspace)
    path1 = Path(session1_file)
    path2 = Path(session2_file)

    if not path1.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Session file not found: {session1_file}"), as_json)
        raise typer.Exit(1)
    if not path2.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Session file not found: {session2_file}"), as_json)
        raise typer.Exit(1)

    session1 = load_session(path1)
    session2 = load_session(path2)
    report = compare_paths(session1, session2)

    _out(ok(report), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Path Comparison[/bold]")
        console.print(f"  Session 1: {report['session1_id']} ({report['session1_steps']} steps)")
        console.print(f"  Session 2: {report['session2_id']} ({report['session2_steps']} steps)")
        console.print(f"  Paths identical: {report['paths_identical']}")
        console.print(f"  Differences: {report['difference_count']}")
        if report["diverged_at"] is not None:
            console.print(f"  Diverged at step: {report['diverged_at']}")


@time_travel_app.command("show")
def time_travel_show(
    session_file: str = typer.Argument(..., help="Path to .arctt file"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Show time travel session details."""
    from ..time_travel import load_session

    _workspace(workspace)
    session_path = Path(session_file)
    if not session_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Session file not found: {session_file}"), as_json)
        raise typer.Exit(1)

    session = load_session(session_path)
    _out(ok(session.to_dict()), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Time Travel Session[/bold]")
        console.print(f"  Session ID: {session.session_id}")
        console.print(f"  Run ID: {session.run_id}")
        console.print(f"  Created: {session.created_at}")
        console.print(f"  Total steps: {len(session.steps)}")
        console.print(f"  Current step: {session.current_step_index + 1}")
        console.print(f"  Branches: {len(session.branches)}")
        for i, step in enumerate(session.steps[:10]):
            marker = " <--" if i == session.current_step_index else ""
            console.print(f"    [{i}] {step.step_type.value} @ {step.timestamp}{marker}")


__all__ = ["time_travel_app"]
